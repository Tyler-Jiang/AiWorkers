# AI Game Studio - 后端调度与状态机设计文档

## 1. 目标
后端是整个系统的调度核心，负责：
- 维护全局状态
- 驱动阶段推进
- 维护电脑锁
- 调用 Cursor Cloud Agents
- 接收 webhook
- 把结果转换为前端可视化状态

## 2. 技术建议
- Python 3.11+
- FastAPI
- Pydantic
- SQLite
- uvicorn

## 3. 核心模块
- state_store
- scheduler
- computer_lock_manager
- agent_manager
- task_manager
- message_manager
- event_log

## 4. 状态机
### 角色状态
- idle
- discussing
- planning
- waiting_computer
- using_computer
- implementing
- reviewing
- blocked
- done

### 任务状态
- todo
- ready
- queued
- in_progress
- waiting_review
- approved
- blocked
- completed

### 阶段状态
- not_started
- needs_confirmation
- active
- waiting_acceptance
- accepted
- rejected

## 5. 调度主循环
1. 检查当前阶段状态
2. 找出 ready 任务
3. 检查依赖
4. 不需要电脑的任务直接派发
5. 需要电脑的任务进入队列
6. 电脑空闲时分配给下一个任务
7. 调用对应 Agent
8. 记录状态
9. 等待 webhook / 查询结果
10. 更新任务、日志、黑板和留言板

## 6. 电脑锁机制
- 需要代码修改的角色必须申请电脑锁
- 锁一次只授予一个角色
- 完成、失败、超时都必须释放
- 队列状态要实时返回给前端

## 7. API 建议
- POST /api/command/global
- POST /api/command/agent/{agent_id}
- GET /api/scene
- GET /api/blackboard
- GET /api/message-board
- GET /api/logs
- GET /api/computer-lock
- POST /api/phases/{phase_id}/approve
- POST /api/phases/{phase_id}/reject
- POST /api/webhooks/cursor

## 8. 成功验收
1. 用户输入需求后可驱动 Producer
2. 阶段计划可生成并等待批准
3. 角色任务可调度
4. 电脑锁与队列成立
5. 结果可持久化
