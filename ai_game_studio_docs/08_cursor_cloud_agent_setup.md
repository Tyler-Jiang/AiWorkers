# Cursor Cloud Agents 配置说明（真实写产出代码）

本控制台通过后端调用 Cursor **Cloud Agents API**（`POST /v0/agents`），让远程 Agent 在 **GitHub 仓库** 里改代码。小游戏应写在仓库内的 **`output/mini-game/`**（与 `frontend/` 分离），本地再起 Vite 做实时预览。

## 你需要准备什么

| 配置项 | 环境变量 | 说明 |
|--------|----------|------|
| API Key | `CURSOR_API_KEY` | 在 Cursor 控制台获取（见下）。用于 Basic 认证调用 `https://api.cursor.com/v0/agents`。 |
| API 根 URL | `CURSOR_API_BASE` | 默认 `https://api.cursor.com`，一般无需改。 |
| GitHub 仓库 | `CURSOR_REPOSITORY` | 格式 `owner/repo`（如 `myorg/AiWorkers`）。**必须**是已连接到 Cursor、且包含本仓库 `output/mini-game/` 的远程仓库。 |
| 分支 | `CURSOR_BRANCH` | Agent 基于该分支工作，默认 `main`。 |
| Webhook 密钥（可选） | `CURSOR_WEBHOOK_SECRET` | 若配置，请求 `POST /api/webhooks/cursor` 时需带头 `X-Studio-Webhook-Secret`。 |

### API Key 去哪里拿

1. 打开浏览器进入 Cursor 账户相关页面（以当前官方为准）：  
   [Cursor Dashboard — Cloud Agents](https://cursor.com/dashboard)（若界面有调整，在 Dashboard 中找到 **Cloud Agents** / **API Keys**）。
2. 创建或复制 **用于 Cloud Agents / `POST /v0/agents` 的 API Key**（部分文档区分「普通 Dashboard Key」与「Agent 专用 Key」；若创建 Agent 失败 401/403，请换用 Cloud Agents 专用密钥）。
3. 将密钥写入 **`backend/.env`**（勿提交到 Git）：

```env
CURSOR_API_KEY=你的密钥
CURSOR_REPOSITORY=你的GitHub用户名或组织名/仓库名
CURSOR_BRANCH=main
```

官方 API 文档入口（路径与字段以最新为准）：  
[Cloud Agents API 文档](https://cursor.com/docs/cloud-agent/api/endpoints)

### 仓库与产出目录的关系

- Cloud Agent **不能**直接访问你笔记本上的未提交文件；它克隆的是 **GitHub 上的 `CURSOR_REPOSITORY`**。
- 因此请把 **`output/mini-game/`** 纳入同一 Git 仓库并 **push**，Agent 才能在 PR/分支里改到小游戏代码。
- 本地开发：在 `output/mini-game` 执行 `npm install && npm run dev`（默认端口 **5180**），办公室内嵌预览 `STUDIO_OUTPUT_PREVIEW_URL`（默认 `http://127.0.0.1:5180`）。

### 可选：产出路径与预览地址

在 `backend/.env` 中可覆盖（默认相对 `backend` 目录）：

```env
STUDIO_OUTPUT_DIR=../output/mini-game
STUDIO_OUTPUT_PREVIEW_URL=http://127.0.0.1:5180
```

`GET /api/scene` 会返回 `output_project` 字段（含解析后的绝对路径），供界面与 Prompt 使用。

## 怎样确认已切到 Live

1. 打开 `http://127.0.0.1:8010/docs`（或你的 API 端口），看 **GET /api/scene** 中 `cursor_integration.mode` 是否为 **`live`**（需同时配置 `CURSOR_API_KEY` 与 `CURSOR_REPOSITORY`）。
2. 在办公室调用 Agent：模拟模式会提示配置 `CURSOR_API_KEY` 与 `CURSOR_REPOSITORY`；Live 成功会返回 `mode: "live"` 与 `dispatch` 相关信息。

## 安全提示

- `.env` 已在 `backend/.gitignore` 中忽略；不要截图或提交密钥。
- Webhook 若暴露到公网，务必配置 `CURSOR_WEBHOOK_SECRET` 并在 Cursor 侧填写回调 URL（本地开发常用 **ngrok** 等工具映射到本机后端）。
