import { create } from 'zustand'

import { apiUrl } from './apiBase'

export type AgentState = {
  id: string
  name: string
  role: string
  state: string
}

export type TaskRow = {
  id: string
  title: string
  owner_agent_id: string | null
  status: string
}

export type StudioMeta = {
  requirement_submitted: boolean
  requirement_preview: string | null
  clarification_answered: boolean
  plan_generated: boolean
}

export type CursorIntegration = {
  mode: string
  api_configured: boolean
  repository_configured: boolean
  branch: string
}

export type OutputProject = {
  preview_url: string
  folder_path: string
  folder_config: string
  hint: string
}

export type AgentInvocationRow = {
  id: string
  agent_id: string
  status: string
  external_ref: string | null
  prompt_summary: string
  created_at: string
}

export type SceneSnapshot = {
  agents: AgentState[]
  computer_lock: { holder_agent_id: string | null; queue: string[] }
  blackboard: { phase: string; tasks: TaskRow[] }
  latest_messages: {
    id: number
    from_agent: string
    to_agent: string | null
    type: string
    body: string
    created_at: string
  }[]
  event_logs: { level?: string; message: string }[]
  current_phase: { id: string; title: string; status: string }
  artifacts_summary: { label: string; detail?: string | null }[]
  studio_meta?: StudioMeta
  cursor_integration?: CursorIntegration
  agent_invocations?: AgentInvocationRow[]
  output_project?: OutputProject
}

type StudioState = {
  scene: SceneSnapshot | null
  error: string | null
  loading: boolean
  loadScene: () => Promise<void>
  approvePhase: (phaseId: string) => Promise<void>
  rejectPhase: (phaseId: string, reason?: string) => Promise<void>
  submitRequirement: (text: string) => Promise<void>
  userReply: (text: string) => Promise<void>
  producerClarify: () => Promise<void>
  generatePlan: () => Promise<void>
  invokeAgent: (agentId: string, promptExtra: string, computerGranted: boolean) => Promise<void>
  requestComputer: (agentId: string) => Promise<void>
  releaseComputer: (agentId: string) => Promise<void>
}

async function readError(res: Response): Promise<string> {
  const code = `HTTP ${res.status}`
  try {
    const j = (await res.json()) as { detail?: unknown }
    if (typeof j.detail === 'string') {
      return `${j.detail}（${code}）`
    }
    if (Array.isArray(j.detail)) {
      return `请求参数校验失败（${code}）`
    }
    const t = await res.text()
    return t ? `${t.slice(0, 200)}（${code}）` : code
  } catch {
    return `${res.statusText}（${code}）`
  }
}

export const useStudioStore = create<StudioState>((set) => ({
  scene: null,
  error: null,
  loading: false,
  loadScene: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl('/api/scene'))
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as SceneSnapshot
      set({ scene: data, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '加载失败'
      set({ error: msg, loading: false })
    }
  },
  approvePhase: async (phaseId: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl(`/api/phases/${encodeURIComponent(phaseId)}/approve`), {
        method: 'POST',
      })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '批准失败'
      set({ error: msg, loading: false })
    }
  },
  rejectPhase: async (phaseId: string, reason?: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl(`/api/phases/${encodeURIComponent(phaseId)}/reject`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason ?? null }),
      })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '驳回失败'
      set({ error: msg, loading: false })
    }
  },
  submitRequirement: async (text: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl('/api/requirements'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '提交失败'
      set({ error: msg, loading: false })
    }
  },
  userReply: async (text: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl('/api/conversation/user-reply'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '发送失败'
      set({ error: msg, loading: false })
    }
  },
  producerClarify: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl('/api/producer/clarify'), { method: 'POST' })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '操作失败'
      set({ error: msg, loading: false })
    }
  },
  generatePlan: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl('/api/producer/generate-plan'), { method: 'POST' })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '生成失败'
      set({ error: msg, loading: false })
    }
  },
  invokeAgent: async (agentId: string, promptExtra: string, computerGranted: boolean) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl(`/api/agents/${encodeURIComponent(agentId)}/invoke`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt_extra: promptExtra, computer_granted: computerGranted }),
      })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '调用失败'
      set({ error: msg, loading: false })
    }
  },
  requestComputer: async (agentId: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl('/api/computer/request'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId }),
      })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '申请失败'
      set({ error: msg, loading: false })
    }
  },
  releaseComputer: async (agentId: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(apiUrl('/api/computer/release'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId }),
      })
      if (!res.ok) {
        throw new Error(await readError(res))
      }
      const data = (await res.json()) as { ok: boolean; scene: SceneSnapshot }
      set({ scene: data.scene, loading: false })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '释放失败'
      set({ error: msg, loading: false })
    }
  },
}))
