import os
import re
import shutil
import yt_dlp
import httpx
from typing import Optional


def _find_ffmpeg_path() -> Optional[str]:
    """查找 ffmpeg 可执行文件路径"""
    if shutil.which("ffmpeg"):
        return os.path.dirname(shutil.which("ffmpeg"))
    try:
        import static_ffmpeg
        paths = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        return os.path.dirname(paths[0])
    except Exception:
        return None


class VideoDownloader:
    """yt-dlp 封装层，提供视频解析、下载、直链获取能力"""

    DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")

    def __init__(self):
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
        self.ffmpeg_path = _find_ffmpeg_path()
        self.has_ffmpeg = self.ffmpeg_path is not None

    @staticmethod
    def _is_bilibili_url(url: str) -> bool:
        return "bilibili.com" in url or "b23.tv" in url

    @staticmethod
    def _base_ydl_opts(url: str = "") -> dict:
        user_agent = os.getenv(
            "YTDLP_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        )
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
            "http_headers": {
                "User-Agent": user_agent,
            },
        }

        if VideoDownloader._is_bilibili_url(url):
            opts["http_headers"]["Referer"] = url

        proxy = os.getenv("YTDLP_PROXY", "").strip()
        cookiefile = os.getenv("YTDLP_COOKIEFILE", "").strip()
        if proxy:
            opts["proxy"] = proxy
        if cookiefile:
            opts["cookiefile"] = cookiefile
        return opts

    @staticmethod
    def _normalize_ydlp_error(url: str, error: Exception) -> Exception:
        message = str(error)
        is_bilibili = VideoDownloader._is_bilibili_url(url)
        if is_bilibili and "412" in message and "Precondition Failed" in message:
            return ValueError(
                "B 站拦截了当前服务器请求（HTTP 412）。这通常不是前端问题，而是服务器 IP、"
                "代理出口或 cookie 被风控。请在 backend/.env 中配置 YTDLP_PROXY，"
                "必要时再补 YTDLP_COOKIEFILE，然后重启后端容器。"
            )
        return error

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    def _bilibili_headers(self, referer: str = "https://www.bilibili.com") -> dict:
        headers = {
            "User-Agent": os.getenv(
                "YTDLP_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            ),
            "Referer": referer,
        }
        cookie = os.getenv("BILIBILI_COOKIE", "").strip()
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def _httpx_proxy(self) -> Optional[str]:
        return os.getenv("YTDLP_PROXY", "").strip() or None

    def _resolve_bilibili_url(self, url: str) -> str:
        if "b23.tv" not in url:
            return url
        with httpx.Client(
            headers=self._bilibili_headers(url),
            follow_redirects=True,
            timeout=15,
            proxy=self._httpx_proxy(),
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return str(response.url)

    @staticmethod
    def _parse_bvid(url: str) -> Optional[str]:
        match = re.search(r"(BV[a-zA-Z0-9]+)", url)
        return match.group(1) if match else None

    def _parse_bilibili_fallback(self, url: str) -> dict:
        resolved_url = self._resolve_bilibili_url(url)
        bvid = self._parse_bvid(resolved_url)
        if not bvid:
            raise ValueError("B 站链接未找到 BV 号，无法使用公开 API 兜底解析")

        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        with httpx.Client(
            headers=self._bilibili_headers(f"https://www.bilibili.com/video/{bvid}"),
            timeout=15,
            proxy=self._httpx_proxy(),
        ) as client:
            response = client.get(api_url)
            response.raise_for_status()
            payload = response.json()

        if payload.get("code") != 0:
            raise ValueError(payload.get("message") or "B 站公开 API 兜底解析失败")

        data = payload.get("data") or {}
        cid = data.get("cid")
        formats = self._get_bilibili_fallback_formats(bvid, cid)
        owner = data.get("owner") or {}
        stat = data.get("stat") or {}

        return {
            "id": bvid,
            "title": data.get("title", "未知标题"),
            "thumbnail": data.get("pic", ""),
            "duration": data.get("duration"),
            "duration_string": self._format_duration(data.get("duration")),
            "uploader": owner.get("name", "未知"),
            "platform": "BiliBili",
            "view_count": stat.get("view"),
            "upload_date": "",
            "description": (data.get("desc") or "")[:200],
            "formats": formats,
            "subtitles": [],
            "automatic_captions": [],
            "fallback_notice": "B 站拦截了服务器的 yt-dlp 请求，已使用公开 API 兜底解析。下载清晰度可能受限。",
        }

    def _get_bilibili_fallback_formats(self, bvid: str, cid: Optional[int]) -> list[dict]:
        if not cid:
            return []

        api_url = "https://api.bilibili.com/x/player/playurl"
        params = {
            "bvid": bvid,
            "cid": str(cid),
            "qn": "64",
            "fnval": "0",
            "fourk": "1",
        }
        try:
            with httpx.Client(
                headers=self._bilibili_headers(f"https://www.bilibili.com/video/{bvid}"),
                timeout=15,
                proxy=self._httpx_proxy(),
            ) as client:
                response = client.get(api_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []

        if payload.get("code") != 0:
            return []

        data = payload.get("data") or {}
        durls = data.get("durl") or []
        if not durls:
            return []

        accept_quality = data.get("accept_quality") or []
        accept_description = data.get("accept_description") or []
        quality_label = dict(zip(accept_quality, accept_description))

        formats = []
        for item in durls[:1]:
            quality = data.get("quality") or 0
            size = item.get("size")
            formats.append({
                "format_id": f"bilibili_api:{bvid}:{cid}:{quality}",
                "ext": "mp4",
                "resolution": quality_label.get(quality, "B站公开直链"),
                "height": quality,
                "filesize": size,
                "filesize_approx": size,
                "vcodec": "unknown",
                "acodec": "unknown",
                "has_audio": True,
                "label": f"{quality_label.get(quality, 'B站公开直链')} MP4 ({self._format_filesize(size)})",
                "url": item.get("url"),
            })
        return formats

    def _get_bilibili_api_direct_url(self, bvid: str, cid: str, quality: str) -> tuple[str, Optional[int]]:
        api_url = "https://api.bilibili.com/x/player/playurl"
        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": quality,
            "fnval": "0",
            "fourk": "1",
        }
        with httpx.Client(
            headers=self._bilibili_headers(f"https://www.bilibili.com/video/{bvid}"),
            timeout=20,
            proxy=self._httpx_proxy(),
            follow_redirects=True,
        ) as client:
            response = client.get(api_url, params=params)
            response.raise_for_status()
            payload = response.json()

        if payload.get("code") != 0:
            raise ValueError(payload.get("message") or "B 站公开直链获取失败")

        durls = (payload.get("data") or {}).get("durl") or []
        if not durls:
            raise ValueError("B 站公开 API 没有返回可下载直链")
        return durls[0].get("url", ""), durls[0].get("size")

    def _download_bilibili_api(self, url: str, format_id: str) -> dict:
        try:
            _, bvid, cid, quality = format_id.split(":", 3)
        except ValueError:
            raise ValueError("B 站兜底下载格式无效")

        direct_url, _ = self._get_bilibili_api_direct_url(bvid, cid, quality)
        if not direct_url:
            raise ValueError("B 站公开 API 没有返回可下载直链")

        metadata = self._parse_bilibili_fallback(url)
        title = self._sanitize_filename(metadata.get("title", bvid))
        filename = f"{title}.mp4"
        filepath = os.path.join(self.DOWNLOAD_DIR, filename)

        with httpx.Client(
            headers=self._bilibili_headers(f"https://www.bilibili.com/video/{bvid}"),
            timeout=60,
            proxy=self._httpx_proxy(),
            follow_redirects=True,
        ) as client:
            with client.stream("GET", direct_url) as response:
                response.raise_for_status()
                with open(filepath, "wb") as output:
                    for chunk in response.iter_bytes():
                        if chunk:
                            output.write(chunk)

        return {
            "filepath": filepath,
            "filename": filename,
            "title": metadata.get("title", bvid),
            "ext": "mp4",
        }

    @staticmethod
    def _format_filesize(size: Optional[int]) -> str:
        if not size:
            return "未知大小"
        if size < 1024 * 1024:
            return f"{size / 1024:.0f}KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        return f"{size / (1024 * 1024 * 1024):.2f}GB"

    @staticmethod
    def _format_duration(seconds: Optional[int]) -> str:
        if not seconds:
            return "00:00"
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def parse_video(self, url: str) -> dict:
        """解析视频信息，不下载文件"""
        ydl_opts = self._base_ydl_opts(url)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            if self._is_bilibili_url(url) and "412" in str(e):
                try:
                    return self._parse_bilibili_fallback(url)
                except Exception as fallback_error:
                    raise ValueError(
                        "B 站拦截了当前服务器请求（HTTP 412），并且公开 API 兜底也失败了："
                        f"{fallback_error}。这通常是服务器出口 IP 被风控，请优先配置 YTDLP_PROXY；"
                        "如果仍失败，再按需配置 BILIBILI_COOKIE。"
                    )
            raise self._normalize_ydlp_error(url, e)

        if not info:
            raise ValueError("无法解析该链接")

        formats = self._extract_formats(info)
        platform = info.get("extractor", info.get("extractor_key", "Unknown"))

        return {
            "id": info.get("id", ""),
            "title": info.get("title", "未知标题"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration"),
            "duration_string": self._format_duration(info.get("duration")),
            "uploader": info.get("uploader", info.get("channel", "未知")),
            "platform": platform,
            "view_count": info.get("view_count"),
            "upload_date": info.get("upload_date", ""),
            "description": (info.get("description") or "")[:200],
            "formats": formats,
            "subtitles": list(info.get("subtitles", {}).keys()),
            "automatic_captions": list(info.get("automatic_captions", {}).keys())[:5],
        }

    def _extract_formats(self, info: dict) -> list:
        """从 yt-dlp info 中提取并整理可用格式"""
        raw_formats = info.get("formats", [])
        if not raw_formats:
            return []

        seen = set()
        results = []

        for f in raw_formats:
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height")
            ext = f.get("ext", "mp4")

            has_video = vcodec and vcodec != "none"
            has_audio = acodec and acodec != "none"

            if not has_video:
                continue

            resolution = f"{f.get('width', '?')}x{height}" if height else "未知"
            filesize = f.get("filesize") or f.get("filesize_approx")
            size_label = self._format_filesize(filesize)

            if has_audio:
                label = f"{height}p {ext.upper()} ({size_label})"
                key = (height, ext, "av")
            else:
                label = f"{height}p {ext.upper()} (仅视频, {size_label})"
                key = (height, ext, "v")

            if key in seen:
                continue
            seen.add(key)

            results.append({
                "format_id": f.get("format_id", ""),
                "ext": ext,
                "resolution": resolution,
                "height": height or 0,
                "filesize": filesize,
                "filesize_approx": filesize,
                "vcodec": vcodec,
                "acodec": acodec if has_audio else None,
                "has_audio": has_audio,
                "label": label,
            })

        results.sort(key=lambda x: x["height"], reverse=True)

        if not any(r["has_audio"] for r in results) and results:
            best_video = results[0]
            merged = {
                **best_video,
                "format_id": f"bestvideo+bestaudio/best",
                "label": f"{best_video['height']}p 最佳 (视频+音频合并)",
                "has_audio": True,
                "acodec": "merged",
            }
            results.insert(0, merged)

        return results[:15]

    def download_video(self, url: str, format_id: str) -> dict:
        """下载视频到服务器临时目录，返回文件路径和元数据"""
        if format_id.startswith("bilibili_api:"):
            return self._download_bilibili_api(url, format_id)

        if not self.has_ffmpeg and "+" in format_id:
            format_id = "best"

        ydl_opts = {
            **self._base_ydl_opts(url),
            "format": format_id,
            "outtmpl": os.path.join(self.DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        }

        if self.has_ffmpeg:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
            ydl_opts["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception as e:
            raise self._normalize_ydlp_error(url, e)

        if not info:
            raise ValueError("下载失败")

        title = self._sanitize_filename(info.get("title", "video"))
        ext = info.get("ext", "mp4")
        filename = f"{title}.{ext}"
        filepath = os.path.join(self.DOWNLOAD_DIR, filename)

        if not os.path.exists(filepath):
            prepared = ydl.prepare_filename(info)
            if os.path.exists(prepared):
                filepath = prepared
                filename = os.path.basename(prepared)
            else:
                for f in os.listdir(self.DOWNLOAD_DIR):
                    if title in f:
                        filepath = os.path.join(self.DOWNLOAD_DIR, f)
                        filename = f
                        break

        return {
            "filepath": filepath,
            "filename": filename,
            "title": info.get("title", "video"),
            "ext": ext,
        }

    def get_direct_url(self, url: str, format_id: str) -> dict:
        """获取视频直链"""
        if format_id.startswith("bilibili_api:"):
            try:
                _, bvid, cid, quality = format_id.split(":", 3)
            except ValueError:
                raise ValueError("B 站兜底直链格式无效")
            direct_url, size = self._get_bilibili_api_direct_url(bvid, cid, quality)
            return {
                "direct_url": direct_url,
                "ext": "mp4",
                "filesize": size,
                "title": bvid,
            }

        ydl_opts = {
            **self._base_ydl_opts(url),
            "format": format_id,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise self._normalize_ydlp_error(url, e)

        if not info:
            raise ValueError("无法获取直链")

        direct_url = info.get("url")
        if not direct_url:
            requested = info.get("requested_formats")
            if requested and len(requested) > 0:
                direct_url = requested[0].get("url")

        if not direct_url:
            raise ValueError("该视频不支持直链下载，请使用服务端下载模式")

        return {
            "direct_url": direct_url,
            "ext": info.get("ext", "mp4"),
            "filesize": info.get("filesize") or info.get("filesize_approx"),
            "title": info.get("title", "video"),
        }
