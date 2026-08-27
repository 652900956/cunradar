# 📡 CunRadar（多通道版 · 多 AI 适配）

**AI 驱动的个人信息雷达** —— 自动追踪你在互联网上关心的博主、项目与内容更新，用 AI 生成每日摘要，并**定时推送到飞书 / 企业微信 / 钉钉**（三选一或全开）。

> 这是原版 CunRadar 的改造版，相对原版有 3 处核心变化：
> 1. **推送渠道**：从单一 Telegram 改为**多通道架构**（飞书 / 企业微信 / 钉钉），每个通道独立、按需开启。
> 2. **AI 供应商**：从单一 DeepSeek 改为**多供应商可切换**（DeepSeek / 智谱 GLM-4.7-Flash / 腾讯混元 Lite / 通义千问，均 OpenAI 兼容）。
> 3. **定时时间**：默认每天**北京时间 06:30 / 12:20 / 21:00** 各跑一次。

不是监控工具，而是帮你从信息洪流里筛出真正值得关注的更新。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| 🎬 **YouTube 频道追踪** | 订阅频道，自动获取最新视频 |
| 📺 **B站 UP 主追踪** | 关注 UP 主更新 |
| 📝 **博客 / RSS 订阅** | 任何支持 RSS 的博客或新闻源 |
| 💻 **GitHub 项目追踪** | 关注指定仓库的 commits |
| 🔥 **GitHub Trending** | 每日热门仓库排行榜（前 N 名） |
| 🤖 **AI 智能摘要** | 用可切换的 AI 模型生成中文每日动态摘要 |
| 📄 **HTML 日报** | 生成响应式网页报告，可选部署到 Cloudflare Pages |
| 📱 **多通道推送** | 每日定时把摘要推送到飞书 / 企业微信 / 钉钉（按配置，可全开） |

---

## 目录结构

```
CunRadar-Feishu/
├── .github/workflows/
│   └── daily.yml          # GitHub Actions 定时工作流（6:30/12:20/21:00 北京时间）
├── config/
│   └── config.yaml        # 关注列表 & 应用配置 & AI/推送配置
├── public/                # 网站图标等静态资源
├── cunradar/
│   ├── __main__.py        # 主入口 & 流程编排
│   ├── config.py          # 配置加载器（支持 ${ENV} 与 FOLLOW_CONFIG）
│   ├── ai/                # AI 摘要（多供应商预设）
│   ├── collectors/        # 各平台采集器
│   ├── storage/           # SQLite 去重存储
│   ├── report/            # HTML 日报生成
│   └── notification/      # 多通道推送（飞书/企业微信/钉钉）
├── .env.example           # 环境变量模板
├── pyproject.toml         # 项目配置
└── README.md
```

---

## 一、本地快速体验（5 分钟跑通）

### 1. 前置条件

- **Git**（用于克隆/提交）
- **Python ≥ 3.12**
- （推荐）**uv** 包管理器：`pip install uv` 或见 https://docs.astral.sh/uv/

### 2. 获取项目

如果你已经把代码放本地（如本文件夹 `CunRadar-Feishu`），直接 `cd` 进去即可。否则克隆：

```bash
git clone https://github.com/652900956/cunradar.git
cd cunradar   # 本地文件夹名不同就换成实际目录（如 CunRadar-Feishu）
```

### 3. 安装依赖

**方式 A（推荐，用 uv）：**
```bash
uv sync --no-dev
```

**方式 B（用 pip）：**
```bash
pip install -e .
```
> 依赖包含：`requests`、`PyYAML`、`feedparser`、`beautifulsoup4`、`lxml`、`pytz`、`curl-cffi`。

### 4. 配置密钥（最关键的一步）

复制模板并填写：

```bash
cp .env.example .env
```

用记事本 / VS Code 打开 `.env`，至少填两项（AI Key + 至少一个推送通道的 Webhook）：

```env
# 选一个 AI 供应商，并填入对应的 API Key
AI_PROVIDER=deepseek
AI_API_KEY=你的AI_key

# 飞书群机器人的 Webhook 地址（启用飞书推送就填）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxx
```

### 5. 本地运行

```bash
python -m cunradar
# 或（用 uv 时）: uv run python -m cunradar
```

控制台会依次打印：采集 → AI 摘要 → 生成 HTML → 推送。第一次跑会输出示例关注对象（村长的频道等）的更新，并在你配置的通道群里收到一条日报。

---

## 二、配置 AI（多供应商，可随时切换）

本项目所有 AI 供应商都**兼容 OpenAI 的 `/chat/completions` 接口**，因此代码只用一套逻辑，切换靠配置。

### 内置预设（改 `AI_PROVIDER` 即可）

| `AI_PROVIDER` | 供应商 | 模型（默认） | 费用 | 备注 |
|---------------|--------|--------------|------|------|
| `deepseek` | DeepSeek | `deepseek-v4-flash` | 付费（便宜） | 质量稳定，推荐默认（2026-07-24 起旧名 deepseek-chat/reasoner 已停用） |
| `zhipu` | 智谱 AI | `glm-4.7-flash` | **免费** | OpenAI 兼容地址 `https://open.bigmodel.cn/api/paas/v4` |
| `hunyuan` | 腾讯混元 | `hunyuan-lite` | **免费** | 地址 `https://api.hunyuan.cloud.tencent.com/v1`；更好的免费档是 `hunyuan-turbos-latest` |
| `qwen` | 通义千问 | `qwen3.7-flash` | 便宜 | 地址 `https://dashscope.aliyuncs.com/compatible-mode/v1`；若报模型名错误，改用 `qwen3.6-flash` / `qwen-turbo` |

> 你举的例子（智谱 GLM-4.7-Flash、腾讯混元 Lite、通义千问）都已内置为预设，前两个免费、第三个便宜，开箱即用。

### 怎么选 / 怎么填

**方法一：只填 Provider（推荐）**
```env
AI_PROVIDER=zhipu
AI_API_KEY=你的智谱key
```
代码会自动套用该供应商的接口地址和默认模型。

**方法二：自定义模型或接口（覆盖预设）**
```env
AI_PROVIDER=deepseek
AI_API_KEY=你的key
AI_MODEL=deepseek-v4-flash       # 想换模型就填（deepseek-chat/reasoner 已于 2026-07-24 停用）；默认已开启思考模式
AI_BASE_URL=https://api.deepseek.com/v1   # 想换兼容端点就填
```
> 优先级：**环境变量 > config.yaml 里的设置 > 供应商预设**。也就是说，只要设了 `AI_MODEL` / `AI_BASE_URL`，就以环境变量为准。

### 各供应商 Key 去哪拿（参考）

- **DeepSeek**：https://platform.deepseek.com → API Keys
- **智谱 GLM**：https://open.bigmodel.cn → 控制台 → API Key（注册即送免费额度）
- **腾讯混元**：https://cloud.tencent.com/product/hunyuan → 开通后获取 API Key
- **通义千问**：https://dashscope.console.aliyun.com → 模型服务灵积 / 百炼 → API Key

---

## 三、配置推送（飞书 / 企业微信 / 钉钉，多通道）

三个通道**相互独立**：在配置里填了哪个通道的 `webhook_url`，就推哪个；留空则自动跳过。你可以只开飞书，也可以三路全开（同一条摘要会分别发到三个群）。

`config.yaml` 里 `notification` 段结构如下（实际值通过环境变量 `.env` / GitHub Secrets 注入，**不写死在代码里**）：

```yaml
notification:
  feishu:
    webhook_url: "${FEISHU_WEBHOOK_URL}"
    secret: "${FEISHU_SECRET}"        # 可选
  wecom:
    webhook_url: "${WECOM_WEBHOOK_URL}"
  dingtalk:
    webhook_url: "${DINGTALK_WEBHOOK_URL}"
    secret: "${DINGTALK_SECRET}"      # 可选
```

### 1. 飞书（Lark）

1. 打开目标飞书群 → 右上角 **···** → **设置** → **群机器人** → **添加机器人** → 选择 **自定义机器人**（Webhook）。
2. 给机器人起个名字（如「每日资讯雷达」），安全设置建议选 **签名校验**（可选，更稳）。
3. 创建后复制 **Webhook 地址**，形如：
   ```
   https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx
   ```
4. 填到 `.env`（线上填 GitHub Secrets）：
   ```env
   FEISHU_WEBHOOK_URL=上面复制的Webhook地址
   FEISHU_SECRET=                     # 开了签名校验就填 secret，没开留空
   ```

### 2. 企业微信

1. 打开目标企业微信群 → 右上角 **···** → **群机器人** → **添加机器人** → 复制 **Webhook 地址**，形如：
   ```
   https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx
   ```
2. 企业微信机器人**无需签名**，直接填：
   ```env
   WECOM_WEBHOOK_URL=上面复制的Webhook地址
   ```

### 3. 钉钉

1. 打开目标钉钉群 → 右上角 **···** → **智能群助手** → **添加机器人** → **自定义机器人（通过 Webhook 接入）**。
2. 复制 **Webhook 地址**，形如：
   ```
   https://oapi.dingtalk.com/robot/send?access_token=xxxx
   ```
3. 「安全设置」若选 **加签**，把生成的 **secret** 也记下来（选「自定义关键词」或「IP 地址」则不需 secret）：
   ```env
   DINGTALK_WEBHOOK_URL=上面复制的Webhook地址
   DINGTALK_SECRET=                   # 选了「加签」就填，否则留空
   ```

### 4. 推送内容长什么样

- **飞书**：一条**富文本（post）消息**——标题 + AI 摘要 + 各来源更新（带可点击链接）+ 可选「完整日报」网页链接；内容过长自动截断。
- **企业微信 / 钉钉**：一条 **markdown 消息**——标题 + AI 摘要 + 各来源更新（带链接）+ 可选「完整日报」链接。

> 安全建议：各平台的 Webhook 地址等同于「往群里发消息的钥匙」，**不要提交到公开仓库**。本地放 `.env`（已被 `.gitignore` 忽略），线上放 GitHub Secrets。

---

## 四、部署到 GitHub Actions（免费、自动定时）

CunRadar 完全跑在 GitHub 提供的免费额度上，**公开仓库**额度最宽松。

### 架构

| 做什么 | 平台 | 费用 |
|-------|------|------|
| 数据采集 + AI 摘要 + 多通道推送 | GitHub Actions（定时运行） | ✅ 公开仓库免费 |
| 去重数据库 | GitHub Actions Cache | ✅ 免费 |
| HTML 日报网页（可选） | Cloudflare Pages | ✅ 免费计划够用 |

### 步骤 1：推送到你的仓库

本仓库已假设你推到 `652900956/cunradar`（公开仓库）。首次推送：

```bash
git add .
git commit -m "init: CunRadar 多通道版（多 AI + 定时推送）"
git branch -M main
git remote add origin https://github.com/652900956/cunradar.git
git push -u origin main
```
> 如果本地 `main` 与远端历史不一致（例如远端已有初始 commit），用：
> `git pull origin main --allow-unrelated-histories` 合并后再 `git push`。

### 步骤 2（可选）：创建 Cloudflare Pages 项目

如果你想要「完整日报」网页：
1. 登录 https://dash.cloudflare.com → **Workers & Pages → Pages → Create project**。
2. 项目名称填 `cunradar`（可自定义），**不要连接 git**，直接创建空项目。
3. 拿到项目名和后续分配的域名（如 `cunradar.pages.dev`）。

> 不配 Cloudflare 也完全没问题——推送照常工作，只是日报里没有「完整日报」网页链接。

### 步骤 3：配置 GitHub Secrets（必填项）

仓库 → **Settings → Secrets and variables → Actions → Secrets** → **New repository secret**：

| Secret 名称 | 必填 | 说明 |
|-------------|------|------|
| `AI_API_KEY` | ✅ 是 | AI 供应商的 API Key（也可用旧名 `DEEPSEEK_API_KEY`，代码兼容） |
| `FEISHU_WEBHOOK_URL` | ❌ 否* | 飞书机器人 Webhook 地址（要推飞书就填） |
| `FEISHU_SECRET` | ❌ 否 | 飞书机器人签名 secret（开了签名校验才填） |
| `WECOM_WEBHOOK_URL` | ❌ 否* | 企业微信机器人 Webhook 地址（要推企微就填） |
| `DINGTALK_WEBHOOK_URL` | ❌ 否* | 钉钉机器人 Webhook 地址（要推钉钉就填） |
| `DINGTALK_SECRET` | ❌ 否 | 钉钉机器人加签 secret（选了加签才填） |
| `CLOUDFLARE_API_TOKEN` | ❌ 否 | Cloudflare API Token（要部署网页才填；不填则跳过部署步骤） |
| `FOLLOW_CONFIG` | ❌ 否 | JSON 格式的关注列表（见第五节），优先级高于 config.yaml |

> \*至少填一个推送通道的 Webhook，否则运行时会打印「未配置任何通道」并跳过推送。

**Cloudflare API Token 获取**：Cloudflare → My Profile → API Tokens → Create Token → 选 **Cloudflare Pages: Edit** 模板 → 复制 Token。

### 步骤 4：配置 GitHub Variables（可选）

仓库 → **Settings → Secrets and variables → Actions → Variables**：

| Variable 名称 | 说明 | 默认值 |
|---------------|------|--------|
| `AI_PROVIDER` | 选哪个 AI 供应商 | `deepseek` |
| `CUNRADAR_PUBLIC_URL` | 日报网页公开地址，如 `https://cunradar.pages.dev` | 空（不填则日报无网页链接） |
| `CUNRADAR_PROJECT_NAME` | Cloudflare Pages 项目名 | `cunradar` |
| `FOLLOW_CONFIG` | 也可放这里（Variable 形式） | 空 |

### 步骤 5：手动触发一次，验证流水线

仓库 → **Actions → CunRadar Daily → Run workflow**。观察日志：
- 采集正常 → AI 摘要生成 → HTML 生成 → **推送成功** ✅
- 若某通道报 `code != 0` / `errcode != 0`，检查该通道 Webhook 地址/签名是否正确。

以后每天 06:30 / 12:20 / 21:00（北京时间）自动运行。

---

## 五、配置关注列表（隐私保护）

默认 `config/config.yaml` 里是示例关注（村长的频道等），方便你先跑通。换成你自己的有两种方式：

**方式 A：直接改 `config/config.yaml`**（简单，但会进仓库）
```yaml
follow:
  youtube:
    - name: "喜欢的UP主"
      channel_id: "UCxxxxxxxxxxxx"
  bilibili:
    - name: "某UP主"
      uid: 123456789
  rss:
    - name: "某博客"
      url: "https://example.com/rss.xml"
  github:
    - name: "某项目"
      repo: "owner/repo"
  github_trending:
    enabled: true
    language: ""      # 留空=全语言；填 "python" 只看 Python
    limit: 5
```

**方式 B：用 `FOLLOW_CONFIG` 环境变量（推荐，公钥不暴露订阅）**
把关注列表写成一行 JSON，本地放 `.env`、线上放 GitHub Secrets/Variables，优先级高于 config.yaml：
```env
FOLLOW_CONFIG={"youtube":[{"name":"Web3村长","channel_id":"UC5MbekhrH8iyFBQLbccBSRg"}],"bilibili":[{"name":"Web3村长Official","uid":1224034462}],"rss":[{"name":"村长博客","url":"https://cunzhangblog.com/rss.xml"}],"github":[{"name":"CunRadar","repo":"652900956/cunradar"}],"github_trending":{"enabled":true,"language":"","limit":5}}
```

### 各来源怎么拿到 ID

- **YouTube channel_id**：打开频道主页，地址栏 `UC...` 那段就是。
- **B站 uid**：打开 UP 主空间，地址栏 `space.bilibili.com/` 后面的数字。
- **RSS**：博客通常 `/rss.xml` 或 `/feed`；不知道就搜「站点名 rss」。
- **GitHub repo**：`owner/repo` 格式。

---

## 六、定时时间说明（北京时间 6:30 / 12:20 / 21:00）

GitHub Actions 用的是 **UTC** 时间。本项目的 `.github/workflows/daily.yml` 已按北京时间换算好：

| 北京时间 | UTC 时间 | workflow 里的 cron |
|---------|---------|-------------------|
| 06:30 | 22:30（前一天） | `30 22 * * *` |
| 12:20 | 04:20 | `20 4 * * *` |
| 21:00 | 13:00 | `0 13 * * *` |

**想改时间**：编辑 `daily.yml` 里 `on.schedule` 下的 cron 表达式（只改前两个数字：分钟、小时），其余保持 `*`。例如改成每小时跑一次：`"0 * * * *"`。改完提交推送即生效。

---

## 七、常见问题 / 排查

- **某通道收不到消息**：先在本机 `python -m cunradar` 看日志里 `[Feishu]` / `[WeCom]` / `[DingTalk]` 那行。若报 `code != 0` / `errcode != 0`，多半是 Webhook 地址复制错了；飞书/钉钉若开了签名却没填对应 `SECRET` 也会失败。
- **AI 摘要为空 / 跳过**：日志会打印 `[AI] Skipped (AI_API_KEY ... not configured)` 或 `[AI Digest] Failed`。检查 `AI_API_KEY` 是否填对、`AI_PROVIDER` 是否拼写正确、网络是否可达该供应商。
- **每天重复收到同样内容**：去重库在 GitHub Cache 里跨运行累积。若你清过 Cache，或首次运行会「兜底」发一条最新内容，属正常现象。
- **HTML 日报网页打不开**：确认配了 `CLOUDFLARE_API_TOKEN` 且 `CUNRADAR_PUBLIC_URL` 填了对的地址；没配则消息里不会有「完整日报」链接。
- **工作流一启动就失败（红色 ✗）**：多半是 `uses:` 的 Action 版本号写错。本项目已锁定为真实存在的最新版（`actions/checkout@v7.0.1`、`actions/setup-python@v7.0.0`、`astral-sh/setup-uv@v10.0.1`），不要手改成不存在的版本。

---

## 八、技术栈

- **语言**：Python ≥ 3.12
- **AI**：OpenAI 兼容接口（DeepSeek / 智谱 / 混元 / 通义千问，可切换）
- **存储**：SQLite（GitHub Cache 跨运行持久化去重）
- **部署**：GitHub Actions + 可选 Cloudflare Pages
- **通知**：多通道架构 —— 飞书（post 富文本）/ 企业微信（markdown）/ 钉钉（markdown + 可选加签）

---

## License

[MIT](LICENSE)
