# VideoBrief 独立站骨架

这是一个已经整理过品牌和展示层的独立项目骨架，核心能力包括：

- 多平台视频解析与下载
- 字幕提取与导出
- AI 视频摘要、思维导图、问答
- 邮箱登录、会员体系、Stripe 支付
- 前后端分离，适合继续包装成独立产品

## 技术栈

- 前端：Vue 3 + Vite + Tailwind CSS
- 后端：FastAPI
- 视频能力：yt-dlp + 定制抖音解析
- AI：OpenAI / DeepSeek（通过 OpenAI SDK 调用兼容接口）
- 认证：JWT
- 支付：Stripe
- 数据库：SQLite

## 目录结构

```text
free-video-downloader-master/
├── backend/
├── docs/
├── frontend/
└── README.md
```

## 本次整理后的关键入口

- 前端品牌配置：`frontend/src/config/site.js`
- 前端环境变量：`frontend/.env`
- 前端 SEO：`frontend/index.html`
- 后端入口：`backend/main.py`
- 支付配置：`backend/api_payment.py`
- 独立站配置说明：`docs/独立站启动清单.md`

## 本地启动

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python main.py
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 3. 访问

浏览器打开 `http://localhost:5173`

## 服务器部署

这个仓库现在已经带了 Docker 部署骨架，适合直接放到 Ubuntu 服务器上跑：

```bash
cp backend/.env.example backend/.env
docker compose up -d --build
```

如果你只是先预览效果，`backend/.env` 里只填写 `OPENAI_API_KEY` 就能启动。

默认会启动：

- `backend`：FastAPI + yt-dlp + ffmpeg
- `frontend`：打包后的静态站点 + Nginx 反代 `/api`

完整步骤见：[docs/Droplet部署指南.md](./docs/Droplet部署指南.md)

## 你接下来最先要改的内容

1. 在 `frontend/.env` 里换掉品牌名、域名、SEO 描述和价格。
2. 在 `backend/.env` 里配置 `OPENAI_API_KEY`（或 `DEEPSEEK_API_KEY`）、`JWT_SECRET`、Stripe 和生产域名。
3. 在 `frontend/public/sitemap.xml` 里换成你的真实域名。
4. 如果准备正式上线，先看 [`docs/独立站启动清单.md`](./docs/独立站启动清单.md)。

## 合规提示

本项目仅适合处理你拥有合法授权的内容。请遵守所在地法律法规及目标平台服务条款。
