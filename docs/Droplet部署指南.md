# VideoBrief 在 DigitalOcean Droplet 部署指南

这份说明按 Ubuntu 24.04 Droplet 编写，目标是先让项目通过服务器 IP 跑起来，之后再切换到正式域名和 HTTPS。

## 你还需要准备的东西

1. 服务器登录方式
   你至少需要 `root` 或 sudo 用户的 SSH 登录权限。
2. AI Key
   推荐配置 `OPENAI_API_KEY`，并把模型设为 `gpt-5.4`。
3. 域名
   不是现在必须，但如果你要正式上线，后面需要把 `video.kateai.cn` 解析到服务器 IP。
4. Stripe 配置
   如果要启用真实支付，你还需要 `STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET`、`STRIPE_PRICE_ID_MONTHLY`。

如果你只是想先看效果：

- 可以先直接用服务器 IP 访问站点
- 可以先不配 Stripe
- 只要配好 `OPENAI_API_KEY`，解析、下载、AI 总结就能先跑起来
- 现在预览模式下，`backend/.env` 只填 API key 也能启动

## 1. 登录服务器

```bash
ssh root@159.65.12.145
```

如果你不是 `root`，把 `root` 替换成你的用户名。

## 2. 安装 Docker 和 Compose 插件

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
```

## 3. 上传项目到服务器

如果你已经把项目放到 Git 仓库：

```bash
git clone <你的仓库地址> /opt/videobrief
cd /opt/videobrief
```

如果还没放到 Git 仓库，也可以先从本地把整个项目目录传上去。

## 4. 配置后端环境变量

先复制环境变量模板：

```bash
cd /opt/videobrief
cp backend/.env.example backend/.env
```

然后编辑：

```bash
nano backend/.env
```

最少要改这些：

```env
OPENAI_API_KEY=你的真实 OpenAI key
```

如果你只是先预览，现在真的只改这一行就可以。其他项都可以先保持为空。
正式上线前再补：

- `JWT_SECRET`
- `CORS_ALLOW_ORIGINS`
- `FRONTEND_URL`
- Stripe 配置

## 5. IP 预览时前端域名设置

这一步现在不是必须。

你可以直接用仓库里的默认前端配置跑起来，通过服务器 IP 访问页面，核心功能照样可用。
只有 SEO、canonical 和分享图链接仍会先指向未来域名，不影响你自己预览。

如果你想把页面里的站点域名也临时显示成 IP，再额外编辑前端配置文件：

```bash
nano frontend/.env
```

临时改成：

```env
VITE_SITE_DOMAIN=http://159.65.12.145
VITE_OG_IMAGE=http://159.65.12.145/og-image.png
```

等正式域名解析好了，再改回 `https://video.kateai.cn` 后重新构建。

## 6. 启动服务

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

## 7. 开放防火墙

如果你启用了 UFW：

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

同时记得在 DigitalOcean 控制台的防火墙或 Networking 配置里放行 `80` 和 `443`。

## 8. 访问预览

浏览器里先打开：

```text
http://159.65.12.145
```

如果页面能打开但 AI 总结失败，优先检查：

1. `backend/.env` 里的 `OPENAI_API_KEY` 是否正确
   如果你切回 DeepSeek，则检查 `DEEPSEEK_API_KEY`
2. `docker compose logs -f backend` 是否报 API 调用错误

## 9. 正式域名上线

等你准备好域名后：

1. 在 DNS 里把 `video.kateai.cn` 指向 `159.65.12.145`
2. 把 `frontend/.env` 改回 `https://video.kateai.cn`
3. 把 `backend/.env` 里的 `CORS_ALLOW_ORIGINS` 和 `FRONTEND_URL` 改成正式域名
4. 重新执行：

```bash
docker compose up -d --build
```

## 10. HTTPS 建议

现在这套部署骨架先解决“跑起来”和“能预览”。

如果你要正式对外：

1. 最简单的方式是后面再加一层 Caddy 自动签发证书
2. 或者用 Nginx + Certbot
3. 如果你愿意，我下一步可以继续直接帮你补 `HTTPS + 域名 + 自动续期` 这一套
