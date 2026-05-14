"""AI 视频总结模块：字幕提取 + 可切换的 LLM 总结"""

import math
import os
import re
import subprocess
import tempfile
from typing import Optional

import httpx
import yt_dlp
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)


def _is_bilibili_url(url: str) -> bool:
    return "bilibili.com" in url or "b23.tv" in url


def _get_first_env(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return default


def _build_ydl_opts(url: str = "", **extra) -> dict:
    user_agent = os.getenv(
        "YTDLP_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    )
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "http_headers": {
            "User-Agent": user_agent,
        },
    }
    if _is_bilibili_url(url):
        opts["http_headers"]["Referer"] = url

    proxy = os.getenv("YTDLP_PROXY", "").strip()
    cookiefile = os.getenv("YTDLP_COOKIEFILE", "").strip()
    if proxy:
        opts["proxy"] = proxy
    if cookiefile:
        opts["cookiefile"] = cookiefile
    opts.update(extra)
    return opts


def _normalize_subtitle_error(url: str, error: Exception) -> Exception:
    message = str(error)
    if _is_bilibili_url(url) and "412" in message and "Precondition Failed" in message:
        return ValueError(
            "B 站字幕接口拦截了当前服务器请求（HTTP 412）。请在 backend/.env 中配置 "
            "YTDLP_PROXY；如果还不够，再补 YTDLP_COOKIEFILE，然后重启后端容器。"
        )
    return error


def _get_bool_env(key: str, default: bool = False) -> bool:
    value = os.getenv(key, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _get_int_env(key: str, default: int) -> int:
    value = os.getenv(key, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _build_openai_audio_client_kwargs() -> dict:
    api_key = _get_first_env("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("未找到 OpenAI API Key，无法启用语音转写兜底")

    kwargs = {"api_key": api_key}
    base_url = _get_first_env("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    kwargs["timeout"] = _get_int_env("OPENAI_TIMEOUT_SECONDS", 120)
    return kwargs


def _friendly_openai_error(error: Exception, action: str = "AI 服务") -> Exception:
    endpoint = _get_first_env("OPENAI_BASE_URL", "LLM_BASE_URL", default="https://api.openai.com")
    if isinstance(error, (APIConnectionError, APITimeoutError)):
        return ValueError(
            f"{action}连接失败：服务器无法连接 OpenAI 接口（{endpoint}）。请检查服务器网络、"
            "OPENAI_BASE_URL 是否正确，以及是否需要给服务器配置出站代理。"
        )
    if isinstance(error, AuthenticationError):
        return ValueError(f"{action}鉴权失败：OPENAI_API_KEY 无效、已撤销，或没有对应项目权限。")
    if isinstance(error, RateLimitError):
        return ValueError(f"{action}额度不足或限流：请检查 OpenAI 账户余额、用量限制和模型额度。")
    if isinstance(error, BadRequestError):
        return ValueError(f"{action}请求参数不被模型接受：{error}")
    if isinstance(error, APIStatusError):
        return ValueError(f"{action}返回异常（HTTP {error.status_code}）：{error}")
    return error


DEFAULT_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_TRANSCRIPTION_MAX_FILE_MB = 24
DEFAULT_TRANSCRIPTION_MAX_DURATION_SECONDS = 1800


class SubtitleExtractor:
    """从视频 URL 提取平台字幕（人工字幕 > 自动字幕）"""

    PREFERRED_LANGS = ["zh-Hans", "zh", "zh-CN", "en", "ja", "ko"]
    SUBTITLE_FORMAT = "json3"

    def __init__(self):
        self.enable_audio_fallback = _get_bool_env(
            "ENABLE_AUDIO_TRANSCRIPTION_FALLBACK",
            default=True,
        )
        self.transcription_model = _get_first_env(
            "OPENAI_TRANSCRIPTION_MODEL",
            default=DEFAULT_TRANSCRIPTION_MODEL,
        )
        self.transcription_max_bytes = (
            _get_int_env(
                "OPENAI_TRANSCRIPTION_MAX_FILE_MB",
                DEFAULT_TRANSCRIPTION_MAX_FILE_MB,
            )
            * 1024
            * 1024
        )
        self.transcription_max_duration_seconds = _get_int_env(
            "OPENAI_TRANSCRIPTION_MAX_DURATION_SECONDS",
            DEFAULT_TRANSCRIPTION_MAX_DURATION_SECONDS,
        )
        self.enable_metadata_fallback = _get_bool_env(
            "ENABLE_METADATA_SUMMARY_FALLBACK",
            default=True,
        )
        self._transcription_client: Optional[OpenAI] = None

    def extract(self, url: str) -> dict:
        """
        提取视频字幕，返回:
        {
            "has_subtitle": bool,
            "language": str,
            "subtitle_type": "manual" | "auto" | "transcribed" | "none",
            "segments": [{"start": float, "end": float, "text": str}, ...],
            "full_text": str,
            "detail_message": str
        }
        """
        if _is_bilibili_url(url):
            result = self._extract_bilibili(url)
            if result["has_subtitle"]:
                return result

        try:
            info = self._get_video_info(url)
        except Exception as error:
            if _is_bilibili_url(url):
                public_info = self._get_bilibili_public_info(url)
                if public_info:
                    return self._metadata_summary_fallback(
                        public_info,
                        f"B 站字幕/音频接口被服务器出口拦截，已改用公开视频信息做有限总结。原始错误：{error}",
                    )
            return self._empty_result(f"视频信息解析失败，无法继续提取字幕或音频：{error}")

        manual_subs = info.get("subtitles") or {}
        auto_subs = info.get("automatic_captions") or {}

        manual_subs = {k: v for k, v in manual_subs.items() if k != "danmaku"}

        lang, sub_url, sub_type = self._pick_best_subtitle(manual_subs, auto_subs)
        subtitle_error_message = ""
        if sub_url:
            try:
                segments = self._download_and_parse(url, lang, sub_type)
            except Exception as error:
                segments = []
                subtitle_error_message = str(error)
            if segments:
                return self._build_subtitle_result(
                    language=lang,
                    subtitle_type=sub_type,
                    segments=segments,
                )

        return self._transcribe_audio_fallback(url, info, subtitle_error_message)

    @staticmethod
    def _empty_result(detail_message: str = "") -> dict:
        return {
            "has_subtitle": False,
            "language": "",
            "subtitle_type": "none",
            "segments": [],
            "full_text": "",
            "detail_message": detail_message,
        }

    @staticmethod
    def _build_subtitle_result(
        *,
        language: str,
        subtitle_type: str,
        segments: list[dict],
        detail_message: str = "",
    ) -> dict:
        full_text = " ".join(seg["text"] for seg in segments)
        return {
            "has_subtitle": True,
            "language": language,
            "subtitle_type": subtitle_type,
            "segments": segments,
            "full_text": full_text,
            "detail_message": detail_message,
        }

    def _metadata_summary_fallback(self, info: dict, detail_message: str) -> dict:
        if not self.enable_metadata_fallback:
            return self._empty_result(detail_message)

        title = str(info.get("title") or "").strip()
        description = str(info.get("description") or "").strip()
        uploader = str(info.get("uploader") or "").strip()
        platform = str(info.get("platform") or info.get("extractor_key") or "").strip()
        duration = info.get("duration") or 0

        lines = [
            "注意：这里不是完整视频字幕或音频转写，而是根据公开视频标题、简介和基础信息生成的有限上下文。",
        ]
        if title:
            lines.append(f"标题：{title}")
        if uploader:
            lines.append(f"作者：{uploader}")
        if platform:
            lines.append(f"平台：{platform}")
        if duration:
            lines.append(f"时长：{self._format_duration_for_text(duration)}")
        if description:
            lines.append(f"简介：{description[:3000]}")

        if len(lines) <= 1:
            return self._empty_result(detail_message)

        text = "\n".join(lines)
        return self._build_subtitle_result(
            language=str(info.get("language") or "auto"),
            subtitle_type="metadata",
            segments=[{"start": 0, "end": float(duration or 1), "text": text}],
            detail_message=detail_message,
        )

    @staticmethod
    def _format_duration_for_text(duration) -> str:
        try:
            seconds = int(float(duration))
        except (TypeError, ValueError):
            return ""
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}小时{minutes}分{sec}秒"
        return f"{minutes}分{sec}秒"

    def _httpx_proxy(self) -> Optional[str]:
        return os.getenv("YTDLP_PROXY", "").strip() or None

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

    def _get_bilibili_public_info(self, url: str) -> dict:
        try:
            resolved_url = self._resolve_bilibili_url(url)
            bvid = self._parse_bvid(resolved_url)
            if not bvid:
                return {}

            with httpx.Client(
                headers=self._bilibili_headers(f"https://www.bilibili.com/video/{bvid}"),
                timeout=15,
                proxy=self._httpx_proxy(),
            ) as client:
                response = client.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
                response.raise_for_status()
                payload = response.json()

            if payload.get("code") != 0:
                return {}

            data = payload.get("data") or {}
            owner = data.get("owner") or {}
            return {
                "title": data.get("title", ""),
                "description": data.get("desc", ""),
                "uploader": owner.get("name", ""),
                "platform": "BiliBili",
                "duration": data.get("duration") or 0,
                "language": "zh",
            }
        except Exception:
            return {}

    def _extract_bilibili(self, url: str) -> dict:
        """B 站专用字幕提取（通过 dm/view API 获取 CC 字幕和 AI 字幕）"""
        empty = self._empty_result()
        try:
            bvid = self._parse_bvid(url)
            if not bvid:
                return empty

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": f"https://www.bilibili.com/video/{bvid}",
            }

            view_resp = httpx.get(
                f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                headers=headers, timeout=15,
            )
            view_data = view_resp.json().get("data", {})
            cid = view_data.get("cid")
            aid = view_data.get("aid")
            if not cid or not aid:
                return empty

            dm_resp = httpx.get(
                f"https://api.bilibili.com/x/v2/dm/view?aid={aid}&oid={cid}&type=1",
                headers=headers, timeout=15,
            )
            dm_data = dm_resp.json().get("data", {})
            subtitle_list = dm_data.get("subtitle", {}).get("subtitles", [])

            if not subtitle_list:
                return empty

            best = subtitle_list[0]
            for s in subtitle_list:
                lang = s.get("lan", "")
                if lang == "zh" or lang == "zh-Hans":
                    best = s
                    break

            sub_type = "auto" if best.get("lan", "").startswith("ai-") else "manual"

            sub_url = best.get("subtitle_url", "")
            if sub_url.startswith("//"):
                sub_url = "https:" + sub_url
            if sub_url.startswith("http://"):
                sub_url = "https://" + sub_url[7:]

            if not sub_url:
                return empty

            sub_resp = httpx.get(sub_url, headers=headers, timeout=15)
            sub_json = sub_resp.json()
            body = sub_json.get("body", [])

            segments = []
            for item in body:
                content = item.get("content", "").strip()
                if not content:
                    continue
                segments.append({
                    "start": round(item.get("from", 0), 2),
                    "end": round(item.get("to", 0), 2),
                    "text": content,
                })

            return self._build_subtitle_result(
                language=best.get("lan", "zh"),
                subtitle_type=sub_type,
                segments=segments,
            )
        except Exception:
            return empty

    @staticmethod
    def _parse_bvid(url: str) -> Optional[str]:
        m = re.search(r"(BV[a-zA-Z0-9]+)", url)
        return m.group(1) if m else None

    def _get_video_info(self, url: str) -> dict:
        ydl_opts = _build_ydl_opts(
            url,
            extract_flat=False,
            writesubtitles=True,
            writeautomaticsub=True,
            skip_download=True,
        )
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise _normalize_subtitle_error(url, e)
        if not info:
            raise ValueError("无法解析该视频链接")
        return info

    def _pick_best_subtitle(
        self, manual_subs: dict, auto_subs: dict
    ) -> tuple[str, Optional[str], str]:
        """按优先级选择最佳字幕，返回 (lang, url, type)"""
        for lang in self.PREFERRED_LANGS:
            if lang in manual_subs:
                formats = manual_subs[lang]
                url = self._get_format_url(formats)
                if url:
                    return lang, url, "manual"

        for lang in self.PREFERRED_LANGS:
            if lang in auto_subs:
                formats = auto_subs[lang]
                url = self._get_format_url(formats)
                if url:
                    return lang, url, "auto"

        if manual_subs:
            first_lang = next(iter(manual_subs))
            url = self._get_format_url(manual_subs[first_lang])
            if url:
                return first_lang, url, "manual"

        if auto_subs:
            first_lang = next(iter(auto_subs))
            url = self._get_format_url(auto_subs[first_lang])
            if url:
                return first_lang, url, "auto"

        return "", None, "none"

    @staticmethod
    def _get_format_url(formats: list) -> Optional[str]:
        preferred = ["json3", "srv3", "vtt", "ttml"]
        for pref in preferred:
            for fmt in formats:
                if fmt.get("ext") == pref:
                    return fmt.get("url")
        return formats[0].get("url") if formats else None

    def _download_and_parse(self, url: str, lang: str, sub_type: str) -> list[dict]:
        """通过 yt-dlp 下载字幕文件并解析为分段列表"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = _build_ydl_opts(
                url,
                skip_download=True,
                writesubtitles=sub_type == "manual",
                writeautomaticsub=sub_type == "auto",
                subtitleslangs=[lang],
                subtitlesformat="vtt",
                outtmpl=os.path.join(tmp_dir, "subtitle"),
            )
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                raise _normalize_subtitle_error(url, e)

            vtt_files = [
                f for f in os.listdir(tmp_dir) if f.endswith(".vtt")
            ]
            if not vtt_files:
                return []

            vtt_path = os.path.join(tmp_dir, vtt_files[0])
            return self._parse_vtt(vtt_path)

    def _transcribe_audio_fallback(self, url: str, info: dict, subtitle_error_message: str = "") -> dict:
        reason_prefix = "该视频暂无平台字幕"
        if subtitle_error_message:
            reason_prefix = f"平台字幕提取失败（{subtitle_error_message}）"

        if not self.enable_audio_fallback:
            return self._metadata_summary_fallback(
                info,
                f"{reason_prefix}，且当前站点未开启语音转写兜底。",
            )

        if not _get_first_env("OPENAI_API_KEY"):
            return self._empty_result(f"{reason_prefix}，且当前站点未配置 OpenAI 语音转写能力。")

        duration = float(info.get("duration") or 0)
        if duration and duration > self.transcription_max_duration_seconds:
            minutes = max(1, self.transcription_max_duration_seconds // 60)
            return self._metadata_summary_fallback(
                info,
                f"{reason_prefix}，且视频时长超过 {minutes} 分钟，当前未执行语音转写。",
            )

        try:
            segments, full_text = self._transcribe_audio(url, duration)
        except Exception as error:
            return self._metadata_summary_fallback(
                info,
                f"{reason_prefix}，语音转写兜底也失败了：{error}",
            )

        if not full_text.strip():
            return self._metadata_summary_fallback(
                info,
                f"{reason_prefix}，语音转写也没有返回可用文本。",
            )

        if not segments:
            segments = self._build_transcribed_segments(
                full_text,
                start_offset=0,
                duration=duration or max(15.0, len(full_text) / 10),
            )

        return self._build_subtitle_result(
            language=str(info.get("language") or "auto"),
            subtitle_type="transcribed",
            segments=segments,
            detail_message="该文本由 AI 根据视频音轨自动转写生成，时间轴为近似估算。",
        )

    def _transcribe_audio(self, url: str, duration: float) -> tuple[list[dict], str]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = self._download_audio_track(url, tmp_dir)
            chunk_files = self._prepare_audio_files_for_transcription(
                audio_path,
                duration=duration,
                tmp_dir=tmp_dir,
            )

            transcript_segments: list[dict] = []
            transcript_texts: list[str] = []
            cursor = 0.0

            for index, (chunk_path, chunk_duration) in enumerate(chunk_files):
                text = self._transcribe_audio_file(chunk_path)
                if not text:
                    cursor += chunk_duration
                    continue

                transcript_texts.append(text)
                transcript_segments.extend(
                    self._build_transcribed_segments(
                        text,
                        start_offset=cursor,
                        duration=chunk_duration or max(8.0, len(text) / 10),
                    )
                )
                cursor += chunk_duration

            full_text = "\n".join(part for part in transcript_texts if part).strip()
            return transcript_segments, full_text

    def _get_transcription_client(self) -> OpenAI:
        if self._transcription_client is None:
            self._transcription_client = OpenAI(**_build_openai_audio_client_kwargs())
        return self._transcription_client

    def _download_audio_track(self, url: str, tmp_dir: str) -> str:
        output_template = os.path.join(tmp_dir, "audio.%(ext)s")
        ydl_opts = _build_ydl_opts(
            url,
            format="bestaudio[abr<=64]/bestaudio/best",
            skip_download=False,
            outtmpl=output_template,
        )
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                requested_downloads = info.get("requested_downloads") or []
                if requested_downloads:
                    filepath = requested_downloads[0].get("filepath")
                    if filepath and os.path.exists(filepath):
                        return filepath

                prepared = ydl.prepare_filename(info)
                if os.path.exists(prepared):
                    return prepared
        except Exception as error:
            raise _normalize_subtitle_error(url, error)

        for filename in os.listdir(tmp_dir):
            candidate = os.path.join(tmp_dir, filename)
            if os.path.isfile(candidate):
                return candidate

        raise ValueError("下载音轨失败，无法执行语音转写")

    def _prepare_audio_files_for_transcription(
        self,
        audio_path: str,
        *,
        duration: float,
        tmp_dir: str,
    ) -> list[tuple[str, float]]:
        working_path = audio_path
        working_duration = duration or self._probe_duration(audio_path)

        if os.path.getsize(working_path) > self.transcription_max_bytes:
            compressed_path = os.path.join(tmp_dir, "audio-compressed.mp3")
            self._run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    working_path,
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-b:a",
                    "32k",
                    compressed_path,
                ]
            )
            working_path = compressed_path
            working_duration = working_duration or self._probe_duration(working_path)

        if os.path.getsize(working_path) <= self.transcription_max_bytes:
            return [(working_path, working_duration)]

        if not working_duration:
            raise ValueError("音频文件超过 25MB，且无法确定时长来自动分段转写")

        chunk_count = max(2, math.ceil(os.path.getsize(working_path) / self.transcription_max_bytes))
        chunk_duration = max(60, math.ceil(working_duration / chunk_count))
        segment_template = os.path.join(tmp_dir, "chunk_%03d.mp3")
        self._run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                working_path,
                "-f",
                "segment",
                "-segment_time",
                str(chunk_duration),
                "-c",
                "copy",
                segment_template,
            ]
        )

        chunk_paths = sorted(
            os.path.join(tmp_dir, name)
            for name in os.listdir(tmp_dir)
            if name.startswith("chunk_") and name.endswith(".mp3")
        )
        if not chunk_paths:
            raise ValueError("音频分段失败，无法执行语音转写")

        remaining = working_duration
        prepared_chunks: list[tuple[str, float]] = []
        for index, chunk_path in enumerate(chunk_paths):
            is_last = index == len(chunk_paths) - 1
            current_duration = remaining if is_last else min(chunk_duration, remaining)
            prepared_chunks.append((chunk_path, max(1.0, current_duration)))
            remaining = max(0.0, remaining - current_duration)

        return prepared_chunks

    def _transcribe_audio_file(self, audio_path: str) -> str:
        client = self._get_transcription_client()
        with open(audio_path, "rb") as audio_file:
            try:
                response = client.audio.transcriptions.create(
                    model=self.transcription_model,
                    file=audio_file,
                    response_format="text",
                )
            except Exception as error:
                raise _friendly_openai_error(error, "语音转写")

        if isinstance(response, str):
            return response.strip()

        text = getattr(response, "text", "")
        if text:
            return text.strip()

        if hasattr(response, "model_dump"):
            data = response.model_dump()
            return str(data.get("text", "")).strip()

        return ""

    @staticmethod
    def _split_transcribed_text(text: str, max_chars: int = 90) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[。！？!?\.])\s+", normalized)
            if sentence.strip()
        ]
        if not sentences:
            sentences = [normalized]

        chunks: list[str] = []
        for sentence in sentences:
            if len(sentence) <= max_chars:
                chunks.append(sentence)
                continue

            if " " in sentence:
                words = sentence.split(" ")
                current = []
                current_len = 0
                for word in words:
                    extra = len(word) + (1 if current else 0)
                    if current and current_len + extra > max_chars:
                        chunks.append(" ".join(current))
                        current = [word]
                        current_len = len(word)
                    else:
                        current.append(word)
                        current_len += extra
                if current:
                    chunks.append(" ".join(current))
            else:
                for start in range(0, len(sentence), max_chars):
                    chunks.append(sentence[start : start + max_chars])

        return [chunk for chunk in chunks if chunk]

    def _build_transcribed_segments(
        self,
        text: str,
        *,
        start_offset: float,
        duration: float,
    ) -> list[dict]:
        chunks = self._split_transcribed_text(text)
        if not chunks:
            return []

        total_length = sum(len(chunk) for chunk in chunks)
        if total_length <= 0:
            total_length = len(text)
        if duration <= 0:
            duration = max(8.0, len(text) / 10)

        segments: list[dict] = []
        cursor = start_offset
        for index, chunk in enumerate(chunks):
            is_last = index == len(chunks) - 1
            weight = len(chunk) / total_length if total_length else 1 / len(chunks)
            chunk_duration = max(1.5, round(duration * weight, 2))
            end = start_offset + duration if is_last else min(start_offset + duration, cursor + chunk_duration)
            segments.append(
                {
                    "start": round(cursor, 2),
                    "end": round(end, 2),
                    "text": chunk,
                }
            )
            cursor = end
        return segments

    @staticmethod
    def _probe_duration(filepath: str) -> float:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filepath,
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return 0.0
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    @staticmethod
    def _run_ffmpeg(command: list[str]) -> None:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "未知错误").strip()
            raise ValueError(f"音频处理失败：{message}")

    @staticmethod
    def _parse_vtt(filepath: str) -> list[dict]:
        """解析 VTT 字幕文件为结构化分段"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        segments = []
        blocks = re.split(r"\n\n+", content)
        time_pattern = re.compile(
            r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})"
        )

        seen_texts = set()
        for block in blocks:
            lines = block.strip().split("\n")
            time_match = None
            text_lines = []
            for line in lines:
                m = time_pattern.search(line)
                if m:
                    time_match = m
                elif time_match and line.strip() and not line.strip().isdigit():
                    clean = re.sub(r"<[^>]+>", "", line.strip())
                    if clean:
                        text_lines.append(clean)

            if time_match and text_lines:
                text = " ".join(text_lines)
                if text in seen_texts:
                    continue
                seen_texts.add(text)

                start = _time_to_seconds(time_match.group(1))
                end = _time_to_seconds(time_match.group(2))
                segments.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "text": text,
                })

        return segments


class VideoSummarizer:
    """使用 OpenAI / DeepSeek 兼容接口生成视频总结、思维导图、问答"""

    def __init__(self):
        self.provider = self._resolve_provider()
        client_kwargs = self._build_client_kwargs(self.provider)
        self.client = OpenAI(**client_kwargs)
        self.model = self._resolve_model(self.provider)

    @staticmethod
    def _resolve_provider() -> str:
        explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
        if explicit:
            if explicit not in {"openai", "deepseek"}:
                raise ValueError("LLM_PROVIDER 仅支持 openai 或 deepseek")
            return explicit

        if _get_first_env("OPENAI_API_KEY", "LLM_API_KEY"):
            return "openai"
        if _get_first_env("DEEPSEEK_API_KEY", "LLM_API_KEY"):
            return "deepseek"
        return "openai"

    @staticmethod
    def _build_client_kwargs(provider: str) -> dict:
        if provider == "openai":
            api_key = _get_first_env("OPENAI_API_KEY", "LLM_API_KEY")
            if not api_key:
                raise ValueError("未找到 OpenAI API Key，请设置 OPENAI_API_KEY")

            base_url = _get_first_env("OPENAI_BASE_URL", "LLM_BASE_URL")
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            kwargs["timeout"] = _get_int_env("OPENAI_TIMEOUT_SECONDS", 120)
            return kwargs

        api_key = _get_first_env("DEEPSEEK_API_KEY", "LLM_API_KEY")
        if not api_key:
            raise ValueError("未找到 DeepSeek API Key，请设置 DEEPSEEK_API_KEY")

        return {
            "api_key": api_key,
            "base_url": _get_first_env(
                "DEEPSEEK_BASE_URL",
                "LLM_BASE_URL",
                default="https://api.deepseek.com",
            ),
            "timeout": _get_int_env("OPENAI_TIMEOUT_SECONDS", 120),
        }

    @staticmethod
    def _resolve_model(provider: str) -> str:
        if provider == "openai":
            return _get_first_env("OPENAI_MODEL", "LLM_MODEL", default="gpt-5.4")
        return _get_first_env("DEEPSEEK_MODEL", "LLM_MODEL", default="deepseek-chat")

    def _create_completion(self, *, messages: list[dict], stream: bool, temperature: float, max_tokens: int):
        options = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if self.provider == "openai":
            options["max_completion_tokens"] = max_tokens
        else:
            options["max_tokens"] = max_tokens
        try:
            return self.client.chat.completions.create(**options)
        except Exception as error:
            raise _friendly_openai_error(error, "AI 总结")

    def summarize_stream(self, subtitle_text: str, language: str = "zh"):
        """流式生成视频总结，yield 每个 token"""
        prompt = self._build_summary_prompt(subtitle_text, language)
        response = self._create_completion(
            messages=[
                {"role": "system", "content": "你是一个专业的视频内容分析助手，擅长提取关键信息并生成结构化的总结。"},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=0.7,
            max_tokens=4096,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def generate_mindmap(self, subtitle_text: str, language: str = "zh") -> str:
        """生成思维导图 Markdown（非流式，一次性返回）"""
        prompt = self._build_mindmap_prompt(subtitle_text, language)
        response = self._create_completion(
            messages=[
                {"role": "system", "content": "你是一个专业的思维导图生成助手，擅长将内容组织为清晰的层级结构。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=0.5,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    def chat_stream(self, subtitle_text: str, question: str):
        """基于视频内容的 AI 问答，流式返回"""
        prompt = self._build_chat_prompt(subtitle_text, question)
        response = self._create_completion(
            messages=[
                {"role": "system", "content": "你是一个视频内容问答助手。根据提供的视频字幕内容来回答用户的问题。如果问题超出视频内容范围，请诚实告知。"},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=0.7,
            max_tokens=2048,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    @staticmethod
    def _build_summary_prompt(subtitle_text: str, language: str) -> str:
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请对以下视频字幕内容进行深度总结分析，使用{lang_hint}输出。

要求输出格式：
## 视频概述
（用2-3句话概括视频的主题和核心内容）

## 内容大纲
（按视频内容的逻辑顺序，列出主要章节/段落，每个章节包含要点）

## 核心知识要点
（提取视频中最重要的知识点、观点或结论，用编号列表形式）

## 总结
（用1-2句话给出整体评价或一句话总结）

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_mindmap_prompt(subtitle_text: str, language: str) -> str:
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请将以下视频字幕内容整理为思维导图结构，使用{lang_hint}输出。

要求：
1. 使用 Markdown 标题层级格式（# 一级标题，## 二级标题，### 三级标题）
2. 最外层是视频主题
3. 第二层是主要章节/模块
4. 第三层是各章节的要点
5. 可以有第四层做更细的展开
6. 每个节点的文字要简洁精炼
7. 只输出 Markdown 内容，不要其他说明文字

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_chat_prompt(subtitle_text: str, question: str) -> str:
        truncated = subtitle_text[:12000]
        return f"""以下是一个视频的字幕内容，请根据这些内容回答用户的问题。

视频字幕内容：
{truncated}

---
用户问题：{question}

请基于视频内容给出准确、详细的回答。如果视频内容中没有相关信息，请诚实说明。"""


def _time_to_seconds(time_str: str) -> float:
    """将 HH:MM:SS.mmm 转为秒数"""
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds
