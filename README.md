# AI Game Studio

本地可视化控制台 + 后端 API，目标见 `ai_game_studio_docs/`。

## 本地运行（开发）

**默认端口（避免与本机已有 8000/5173 冲突）：API `8010`，前端 `5174`。**

需要两个终端。

**1. 后端（FastAPI）**

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

- 健康检查：<http://127.0.0.1:8010/health>
- 场景快照（聚合接口）：<http://127.0.0.1:8010/api/scene>
- OpenAPI 文档：<http://127.0.0.1:8010/docs>

**2. 前端（Vite）**

```powershell
cd frontend
npm run dev
```

- 控制台界面：<http://127.0.0.1:5174>（Vite **固定 5174 端口** `strictPort`，并监听 `host` 以便本机 IPv4 访问；通过代理访问 `/api`，请保持后端已启动）
- 若页面报 **Not Found**：说明 `/api` 未代理到后端（常见于未用 `npm run dev`、或端口不是 5174）。可改用 `frontend/.env` 中 **`VITE_API_BASE=http://127.0.0.1:8010`**（**不要**写成 `...8010/api`，否则会请求 `/api/api/...` 导致 404）。

### 如何确认后端已用「当前代码」重启

打开 <http://127.0.0.1:8010/docs> 页面**左上角**版本号应为 **`0.4.0`**。若仍是 **`0.2.0` 等旧版本**，说明 uvicorn 还在跑旧进程：请关掉原来的后端窗口后，在 `backend` 目录重新执行上面的 `uvicorn` 命令。旧版本**没有** `GET /api/ping`，因此 <http://127.0.0.1:5174/api/ping> 会一直是 `Not Found`；**重启后端**后再试。

### 验证代理（不依赖 /ping）

只要后端已更新，也可访问：<http://127.0.0.1:5174/api/scene> — 应返回一大段 JSON（场景数据）。若此处为 Not Found，再检查是否用 `npm run dev` 起的 5174。

### 在 CMD 里怎么测（没有 Invoke-RestMethod）

`Invoke-RestMethod` 是 **PowerShell** 专用，**CMD 里没有**。任选其一：

**A. 仍用 CMD，调用系统自带的 curl（Win10+ 一般有）：**

```bat
curl -s http://127.0.0.1:8010/health
curl -s http://127.0.0.1:8010/api/ping
curl -s http://127.0.0.1:8010/api/scene
```

**B. 在 CMD 输入 `powershell` 回车，进入蓝色 PowerShell 窗口后**再执行（不要用 CMD 直接敲 `Invoke-RestMethod`）：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8010/api/requirements" -Method Post -ContentType "application/json" -Body '{"text":"这是一条至少三字的测试需求"}'
```

**C. 最省事**：打开 <http://127.0.0.1:8010/docs>，找到 **`POST /api/requirements`**，点 **Try it out**，在 Request body 里填 `{"text":"这是一条至少三字的测试需求"}`，点 **Execute**。

## 数据与重置（Stage C+）

- 状态库：`backend/data/studio.db`（SQLite，目录已加入 `backend/.gitignore`）
- 恢复初始种子数据：关闭后端进程后删除 `backend/data/studio.db`，再启动；会自动建表并写入初始角色、阶段与示例任务。
- 升级自旧库时启动会自动补全 `studio_meta` 表与空行；新增表 `agent_invocations` 由 SQLAlchemy 自动创建。

## Cursor Cloud Agents（Stage E，可选）

在 `backend/` 下创建 `.env`（已加入 `backend/.gitignore`），例如：

```env
CURSOR_API_KEY=你的_Cloud_Agents_API_Key
CURSOR_REPOSITORY=GitHub 的 owner/repo
CURSOR_BRANCH=main
# 可选：Webhook 简易密钥（请求头 X-Studio-Webhook-Secret）
# CURSOR_WEBHOOK_SECRET=随机字符串
```

未配置密钥或仓库时，**调用 Agent** 为**模拟模式**（仅写库与对话，不访问外网）。配置完整后，后端会向 `CURSOR_API_BASE`（默认 `https://api.cursor.com`）请求 `POST /v0/agents`（Basic 认证：用户名=API Key，密码空），具体以 Cursor 当前文档为准。

## 已实现 API（节选）

- `GET /api/scene` — 聚合场景（含 `studio_meta`、`cursor_integration`、`agent_invocations`）
- `POST /api/agents/{agent_id}/invoke` — 按角色调用（拼接 Prompt 基线 + 场景上下文）
- `GET /api/agents/invocations`、`GET /api/integrations/cursor` — 调用记录与配置状态
- `POST /api/requirements` — 提交用户需求（模板澄清一条）
- `POST /api/conversation/user-reply` — 用户回复制作人
- `POST /api/producer/clarify` — 制作人追加澄清（轮换模板）
- `POST /api/producer/generate-plan` — 生成「点击成长小游戏」阶段计划（并自动验收未结的 `bootstrap` 工程阶段）
- `GET /api/blackboard`、`/api/message-board`、`/api/logs`、`/api/computer-lock`
- `POST /api/phases/{phase_id}/approve`、`/api/phases/{phase_id}/reject`
- `POST /api/command/global`、`/api/command/agent/{agent_id}`（写事件日志）
- `POST /api/webhooks/cursor` — Cursor 回调（可选头 `X-Studio-Webhook-Secret`；体尽量匹配 `external_ref` 以更新调用状态）

## 如何了解项目进度

1. **路线图**：打开 `ai_game_studio_docs/07_implementation_roadmap_and_tasks.md`，按 Stage A～H 对照当前完成到哪一阶段。
2. **运行时**：浏览器打开控制台；左侧可 **调用 Cloud Agent**（顶栏显示 `simulation` / `live`）；小黑板内可走 Producer 流程并批准阶段；右侧为对话与系统日志。
3. **接口文档**：后端 `http://127.0.0.1:8010/docs` 可查看并调试 API。

## 仓库结构（初始）

- `backend/` — FastAPI 应用
- `frontend/` — React + TypeScript + Vite 控制台
- `ai_game_studio_docs/` — 设计文档
