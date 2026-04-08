import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useStudioStore } from './studioStore'
import './App.css'

function labelAgent(id: string) {
  if (id === 'user') return '你'
  if (id === 'producer') return 'Producer'
  return id
}

function App() {
  const {
    scene,
    error,
    loading,
    loadScene,
    approvePhase,
    rejectPhase,
    submitRequirement,
    userReply,
    producerClarify,
    generatePlan,
    invokeAgent,
    requestComputer,
    releaseComputer,
  } = useStudioStore()
  const [reqDraft, setReqDraft] = useState('')
  const [replyDraft, setReplyDraft] = useState('')
  const [agentPick, setAgentPick] = useState('producer')
  const [agentExtra, setAgentExtra] = useState('')
  const [grantComputer, setGrantComputer] = useState(false)

  const agentOptions = useMemo(
    () =>
      [
        ['producer', 'Producer'],
        ['designer', 'Designer'],
        ['developer', 'Developer'],
        ['artist', 'Artist'],
        ['qa', 'QA'],
      ] as const,
    [],
  )

  useEffect(() => {
    void loadScene()
  }, [loadScene])

  const online = scene?.agents.length ?? 0
  const phaseTitle = scene?.current_phase.title ?? '—'
  const phaseStatusRaw = scene?.current_phase.status ?? ''
  const phaseStatusDisplay = phaseStatusRaw || '—'
  const lockHolder = scene?.computer_lock.holder_agent_id
  const queueLen = scene?.computer_lock.queue.length ?? 0
  const phaseId = scene?.current_phase.id
  const phaseIdOk = Boolean(phaseId && phaseId !== '—')
  const canDecide =
    phaseStatusRaw === 'needs_confirmation' || phaseStatusRaw === 'waiting_acceptance'

  const meta = scene?.studio_meta
  const canSubmitReq = !meta?.plan_generated
  const canReply = Boolean(meta?.requirement_submitted && !meta?.plan_generated)
  const canGenPlan = Boolean(
    meta?.requirement_submitted &&
      meta?.clarification_answered &&
      !meta?.plan_generated,
  )
  const canExtraClarify = Boolean(meta?.requirement_submitted && !meta?.plan_generated)

  return (
    <div className="app">
      <header className="topbar">
        <h1>AI Game Studio</h1>
        <div className="topbar-meta">
          <span>
            阶段：<strong>{phaseTitle}</strong>
          </span>
          <span>
            状态：<strong>{phaseStatusDisplay}</strong>
          </span>
          <span>
            角色：<strong>{online}</strong>
          </span>
          <span>
            Agent：<strong>{scene?.cursor_integration?.mode ?? '—'}</strong>
          </span>
        </div>
      </header>

      {error ? (
        <div className="error-banner">
          <strong>无法连接后端：</strong>
          {error}
          {error.includes('Not Found') ? (
            <>
              {' '}
              这通常是<strong>页面未走 Vite 代理</strong>（例如用预览打开 dist、或端口不对）。
              请在本机运行 <code>cd frontend && npm run dev</code>，用{' '}
              <code>http://127.0.0.1:5174</code> 访问；并确保后端{' '}
              <code>uvicorn</code> 已在 <code>8010</code> 端口启动。也可在{' '}
              <code>frontend/.env</code> 设置{' '}
              <code>VITE_API_BASE=http://127.0.0.1:8010</code> 直连 API。
            </>
          ) : (
            <>（请先启动 API：默认端口 8010）</>
          )}
        </div>
      ) : null}

      <main className="layout">
        <motion.section
          className="panel"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <h2>办公室</h2>
          {loading && !scene ? <p className="loading">加载场景…</p> : null}
          <div className="agent-grid">
            {scene?.agents.map((a) => (
              <div key={a.id} className="agent-card">
                <div className="name">{a.name}</div>
                <div className="role">{a.role}</div>
                <div className="state">{a.state}</div>
              </div>
            ))}
          </div>
          <div className="computer-row">
            <h2 style={{ marginBottom: '0.5rem' }}>电脑与队列（Stage F）</h2>
            <div className="computer-box">
              <div className="computer-icon" aria-hidden />
              <div>
                <div style={{ fontWeight: 600 }}>共享工作站</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                  占用：{lockHolder ?? '空闲'}
                </div>
                {queueLen > 0 ? (
                  <div className="queue-tags" title="等待顺序">
                    队列：{(scene?.computer_lock.queue ?? []).join(' → ')}
                  </div>
                ) : (
                  <div className="queue">队列：空</div>
                )}
              </div>
            </div>
            <div className="computer-actions">
              <button
                type="button"
                disabled={loading}
                onClick={() => void requestComputer('developer')}
              >
                Developer 申请工作站
              </button>
              <button
                type="button"
                disabled={loading || lockHolder !== 'developer'}
                onClick={() => void releaseComputer('developer')}
              >
                Developer 释放工作站
              </button>
            </div>
            <p className="meta-hint" style={{ marginTop: '0.5rem' }}>
              调用 Developer 且勾选「需要写代码」时，须先占用工作站；模拟调用成功后会自动释放并推进队列。
            </p>
          </div>

          <div className="agent-cloud-panel">
            <h2>Cloud Agent</h2>
            <p className="meta-hint">
              {scene?.cursor_integration?.mode === 'live'
                ? `已配置密钥与仓库（分支 ${scene?.cursor_integration?.branch ?? 'main'}）；Agent 将改 GitHub 上仓库内产出目录。`
                : '当前为模拟模式。请在 backend/.env 配置 CURSOR_API_KEY 与 CURSOR_REPOSITORY，详见仓库 ai_game_studio_docs/08_cursor_cloud_agent_setup.md。'}
            </p>
            <label className="field-label" htmlFor="agent-role">
              角色
            </label>
            <select
              id="agent-role"
              className="select-in"
              value={agentPick}
              onChange={(e) => setAgentPick(e.target.value)}
              disabled={loading}
            >
              {agentOptions.map(([v, lab]) => (
                <option key={v} value={v}>
                  {lab}
                </option>
              ))}
            </select>
            <textarea
              className="text-in"
              rows={2}
              placeholder="附加说明（可选）"
              value={agentExtra}
              onChange={(e) => setAgentExtra(e.target.value)}
              disabled={loading}
            />
            <label className="check-row">
              <input
                type="checkbox"
                checked={grantComputer}
                onChange={(e) => setGrantComputer(e.target.checked)}
                disabled={loading}
              />
              本次任务需要写代码（仅 Developer；须已在左侧占用工作站）
            </label>
            <button
              type="button"
              className="invoke-btn"
              disabled={loading}
              onClick={() =>
                void invokeAgent(agentPick, agentExtra, grantComputer && agentPick === 'developer')
              }
            >
              调用 Agent
            </button>
            {scene?.agent_invocations?.length ? (
              <ul className="inv-list">
                {scene.agent_invocations.map((inv) => (
                  <li key={inv.id}>
                    <span className="inv-agent">{inv.agent_id}</span>
                    <span className="inv-st">{inv.status}</span>
                    <div className="inv-sum">{inv.prompt_summary}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="meta-hint">尚无调用记录。</p>
            )}
          </div>
        </motion.section>

        <motion.section
          className="panel"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05 }}
        >
          <h2>小黑板</h2>
          <div className="blackboard-phase">
            {scene?.current_phase.title ?? '—'}
            <span className="status">{phaseStatusDisplay}</span>
          </div>

          <div className="collab-block">
            <h3>需求与制作人（Stage D）</h3>
            {meta?.requirement_preview ? (
              <p className="meta-hint">已记录需求摘要：{meta.requirement_preview}</p>
            ) : (
              <p className="meta-hint">尚未提交需求。描述想做的小游戏目标（至少 3 字）。</p>
            )}
            <textarea
              className="text-in"
              rows={3}
              placeholder="例如：做一款点击攒金币、能升级点击力的极简网页小游戏……"
              value={reqDraft}
              onChange={(e) => setReqDraft(e.target.value)}
              disabled={loading || !canSubmitReq}
            />
            <div className="row-btns">
              <button
                type="button"
                disabled={loading || !canSubmitReq || reqDraft.trim().length < 3}
                onClick={() => void submitRequirement(reqDraft).then(() => setReqDraft(''))}
              >
                提交需求
              </button>
            </div>
            <textarea
              className="text-in"
              rows={2}
              placeholder="回复制作人的澄清问题……"
              value={replyDraft}
              onChange={(e) => setReplyDraft(e.target.value)}
              disabled={loading || !canReply}
            />
            <div className="row-btns">
              <button
                type="button"
                disabled={loading || !canReply || !replyDraft.trim()}
                onClick={() => void userReply(replyDraft).then(() => setReplyDraft(''))}
              >
                发送回复
              </button>
              <button
                type="button"
                disabled={loading || !canExtraClarify}
                onClick={() => void producerClarify()}
              >
                制作人追加澄清
              </button>
              <button
                type="button"
                disabled={loading || !canGenPlan}
                onClick={() => void generatePlan()}
              >
                生成阶段计划
              </button>
            </div>
          </div>

          {scene?.blackboard.tasks.length ? (
            <ul className="task-list">
              {scene.blackboard.tasks.map((t) => (
                <li key={t.id}>
                  <span className="task-title">{t.title}</span>
                  <span className="task-meta">
                    {t.owner_agent_id ?? '—'} · {t.status}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="task-placeholder">当前阶段暂无任务行。</div>
          )}
          <div className="actions">
            <button
              type="button"
              disabled={!canDecide || !phaseIdOk || loading}
              onClick={() => phaseId && void approvePhase(phaseId)}
            >
              批准阶段
            </button>
            <button
              type="button"
              disabled={!canDecide || !phaseIdOk || loading}
              onClick={() => {
                if (!phaseId) return
                const r = window.prompt('驳回原因（可留空）', '')
                if (r === null) return
                void rejectPhase(phaseId, r || undefined)
              }}
            >
              驳回阶段
            </button>
            <button type="button" onClick={() => void loadScene()} disabled={loading}>
              {loading ? '刷新中…' : '刷新数据'}
            </button>
          </div>
        </motion.section>

        <motion.section
          className="panel"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.1 }}
        >
          <h2>用户与制作人</h2>
          <div className="msg-thread">
            {scene?.latest_messages?.length ? (
              scene.latest_messages.map((m) => (
                <div key={m.id} className={`msg-bubble from-${m.from_agent}`}>
                  <div className="msg-who">
                    {labelAgent(m.from_agent)}
                    {m.type ? ` · ${m.type}` : ''}
                  </div>
                  <div className="msg-body">{m.body}</div>
                </div>
              ))
            ) : (
              <p className="meta-hint">暂无对话。提交需求后将出现澄清与回复。</p>
            )}
          </div>
          <h2 className="log-heading">系统日志</h2>
          <ul className="log-list">
            {scene?.event_logs.map((log, i) => (
              <li key={`${log.message}-${i}`}>{log.message}</li>
            ))}
          </ul>
        </motion.section>
      </main>

      <section className="output-preview-strip panel" aria-label="产出项目实时预览">
        <h2>产出项目 · 本地预览</h2>
        <p className="meta-hint">
          {scene?.output_project?.hint ??
            '小游戏与交付物在独立目录 output/mini-game，与控制台 frontend 分离；由 Cloud Agent 在仓库内实现。'}
        </p>
        {scene?.output_project ? (
          <>
            <p className="meta-hint">
              绝对路径：<code>{scene.output_project.folder_path}</code>
            </p>
            <p className="meta-hint">
              配置项（相对 backend）：<code>{scene.output_project.folder_config}</code> · 预览 URL：
              <code>{scene.output_project.preview_url}</code>
            </p>
            <div className="output-preview-toolbar">
              <a href={scene.output_project.preview_url} target="_blank" rel="noreferrer">
                新窗口打开预览
              </a>
            </div>
            <div className="output-preview-frame-wrap">
              <iframe
                title="产出项目预览"
                src={scene.output_project.preview_url}
                className="output-preview-iframe"
                sandbox="allow-scripts allow-same-origin allow-forms"
              />
            </div>
          </>
        ) : (
          <p className="meta-hint">加载场景后可显示预览地址。</p>
        )}
      </section>

      <footer className="footer-hint">
        产出目录 <code>output/mini-game</code> · Cloud Agents 配置见{' '}
        <code>ai_game_studio_docs/08_cursor_cloud_agent_setup.md</code> ·{' '}
        <code>backend/data/studio.db</code>
      </footer>
    </div>
  )
}

export default App
