# 📡 CunRadar

**AI 驱动的个人信息雷达** — 自动追踪互联网上重要的人、项目和内容变化，生成每日信息日报。

不是监控工具，而是帮你从信息洪流中筛选出真正值得关注的更新。

---

## 功能

| 功能 | 说明 |
|------|------|
| 🎬 **YouTube 频道追踪** | 订阅 YouTube 频道，自动获取最新视频 |
| 📺 **B站 UP 主追踪** | 关注 B站 UP 主更新 |
| 📝 **博客 / RSS 订阅** | 任何支持 RSS 的博客或新闻源 |
| 💻 **GitHub 项目追踪** | 关注指定仓库的 commits |
| 🔥 **GitHub Trending** | 每日 GitHub 热门仓库排行榜（前 N 名） |
| 🤖 **AI 智能摘要** | 使用 DeepSeek 模型，自动生成今日技术动态摘要 |
| 📄 **HTML 日报** | 生成响应式网页报告，自动部署到 GitHub Pages |
| 📱 **Telegram 推送** | 每日定时推送到 Telegram 频道/群组 |

---

## 快速开始（本地测试）

### 1. 克隆仓库

```bash
git clone https://github.com/cunzhangcrypto/CunRadar.git
cd CunRadar
```

### 2. 安装依赖

```bash
pip install -e .
```

> 依赖包括：`requests`、`PyYAML`、`feedparser`、`beautifulsoup4`、`lxml`

### 3. 配置关注列表

编辑 `config/config.yaml`，添加你想追踪的博主、项目和博客：

```yaml
follow:
  youtube:
    - name: "Web3村长"
      channel_id: "UC5MbekhrH8iyFBQLbccBSRg"

  bilibili:
    - name: "村长"
      uid: 1224034462

  rss:
    - name: "村长博客"
      url: "https://www.cunzhangblog.com/rss.xml"

  github:
    - name: "cunzhanglab/cunzhanglab"
      repo: "cunzhangcrypto/cunzhanglab"

  github_trending:
    enabled: true
    language: ""
    limit: 5
```

### 4. 配置密钥

```bash
cp .env.example .env
```

编辑 `.env`，填入实际的 API Key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```

> 如果不需要 Telegram 推送，可以留空。

### 5. 运行

```bash
python -m cunradar
```

---

## GitHub Actions 部署

项目内置了 GitHub Actions 工作流，每天定时运行采集 + 部署到 Cloudflare Pages。

### 前置条件

在 Cloudflare Dashboard 中创建一个 Pages 项目（名称任意，例如 `cunradar`），无需连接 git 仓库，后续通过 wrangler CLI 部署。

### 步骤

#### 1. 在 GitHub 上创建仓库

创建一个新仓库（公开或私有均可），例如 `CunRadar`。

#### 2. 推送代码

```bash
git init
git add .
git commit -m "init: CunRadar - AI-powered Personal Information Radar"
git branch -M main
git remote add origin https://github.com/cunzhangcrypto/CunRadar.git
git push -u origin main
```

#### 3. 配置 Secrets

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中添加以下 Secrets：

| Secret 名称 | 说明 |
|-------------|------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token（Pages 部署权限） |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（可选） |
| `TELEGRAM_CHAT_ID` | Telegram 频道/群组 ID（可选） |

> **Cloudflare API Token 获取**：
> 1. 进入 [Cloudflare Dashboard → My Profile → API Tokens](https://dash.cloudflare.com/profile/api-tokens)
> 2. 创建 Token，权限选择 **Cloudflare Pages → Edit**
> 3. 复制 Token 添加到 GitHub Secrets

> **可选配置**：在 **Settings → Secrets and variables → Actions → Variables** 中添加 `CUNRADAR_PUBLIC_URL`，值为 Cloudflare Pages 分配的域名（如 `https://cunradar.pages.dev`），日报中的链接将指向该地址。

#### 4. 触发运行

- **定时运行**：默认每天早上 08:00（北京时间）自动运行
- **手动运行**：进入 **Actions → CunRadar Daily → Run workflow** 即可手动触发

#### 5. 修改运行时间

编辑 `.github/workflows/daily.yml`，修改 cron 表达式：

```yaml
schedule:
  - cron: "0 0 * * *"    # 北京时间 08:00
```

| 北京时间 | UTC 时间  |
|---------|----------|
| 08:00   | `0 0 * * *` |
| 09:30   | `30 1 * * *` |
| 20:00   | `0 12 * * *` |

> GitHub Actions 使用 UTC 时间，北京时间 = UTC + 8 小时。

---

## 项目结构

```
CunRadar/
├── .github/workflows/
│   └── daily.yml          # GitHub Actions 定时工作流
├── config/
│   └── config.yaml        # 关注列表 & 应用配置
├── public/
│   ├── favicon.ico        # 网站图标
│   ├── logo.png           # Logo
│   └── robots.txt         # SEO
├── cunradar/
│   ├── __main__.py        # 主入口 & 流程编排
│   ├── config.py          # 配置加载器
│   ├── ai/                # AI 摘要生成
│   ├── collectors/        # 各平台采集器
│   │   ├── youtube.py
│   │   ├── bilibili.py
│   │   ├── rss.py
│   │   ├── github.py
│   │   └── base.py
│   ├── storage/           # SQLite 去重存储
│   ├── report/            # HTML 日报生成
│   └── notification/      # Telegram 推送
├── .env.example           # 环境变量模板
├── pyproject.toml         # 项目配置
└── README.md
```

---

## 自定义

### 时间窗口

默认只统计过去 24 小时内发布的内容。可在 `config/config.yaml` 中修改：

```yaml
app:
  max_item_age_hours: 48   # 改为 48 小时
```

### 首次运行兜底

当关注的博主在时间窗口内没有新内容时，CunRadar 会自动取该博主最近一条内容作为基线写入日报和数据库，确保后续运行能够正确识别新增内容。GitHub Trending 不受此影响。

---

## 技术栈

- **语言**：Python ≥ 3.12
- **AI**：DeepSeek API
- **存储**：SQLite
- **部署**：GitHub Actions + GitHub Pages
- **通知**：Telegram Bot API

---

## 链接

- [村长实验室 czlab.com](https://czlab.com)
- [村长博客 cunzhangblog.com](https://cunzhangblog.com)
