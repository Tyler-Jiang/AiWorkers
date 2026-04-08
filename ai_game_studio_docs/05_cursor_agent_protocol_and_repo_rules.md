# AI Game Studio - Cursor Agent 调用协议与项目仓库操作规范

## 1. 目标
定义本地后端如何调用 Cursor Cloud Agents，以及云端 agent 如何围绕项目仓库工作，避免混乱、越权和并发写冲突。

## 2. 执行模式
- 本地控制台 + 本地后端调度
- 云端 Cursor Cloud Agents 执行
- 单项目仓库
- 单电脑写入权限

## 3. 调用原则
1. 每次调用都必须带完整阶段上下文
2. 每次调用都必须带角色 Prompt 基线
3. 每次调用都必须指定期望输出结构
4. 开发类任务必须说明电脑锁是否已授予
5. 仅 Developer 在 granted 时可执行仓库写入类任务

## 4. 仓库操作规则
### Developer 唯一写入者
第一版只有 Developer 可对项目代码做正式写入。

### 其他角色
- Producer：文档建议
- Designer：玩法说明
- Artist：视觉规范
- QA：测试报告

## 5. 命令执行规则
允许：
- 安装依赖
- 启动项目
- 运行构建
- 运行 lint
- 执行测试

禁止：
- 超出项目目录的大范围操作
- 删除无关文件
- 修改当前阶段范围外模块
- 擅自引入重型基础设施

## 6. 文档落盘建议
- requirement_summary.md
- phase_plan.md
- gameplay_design.md
- ui_style_spec.md
- qa_report_phase_x.md

## 7. 成功验收
1. 调用边界清晰
2. Developer 只有在锁授权下才修改代码
3. Agent 输出能被后端解析
4. 项目代码能逐步推进
