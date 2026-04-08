# 产出目录（与控制台分离）

小游戏等**交付物**放在此目录下的独立 npm 项目中（默认 `mini-game/`），**不要**写在 `frontend/`。

- 本地预览：进入 `mini-game`，执行 `npm install && npm run dev`（默认 <http://127.0.0.1:5180>）。
- AI Game Studio 办公室会内嵌该地址作为实时预览。
- Cloud Agent 只会修改 **推送到 GitHub 的仓库** 中的文件；请保证本目录已提交并包含在 `CURSOR_REPOSITORY` 所指仓库里。

详见 `ai_game_studio_docs/08_cursor_cloud_agent_setup.md`。
