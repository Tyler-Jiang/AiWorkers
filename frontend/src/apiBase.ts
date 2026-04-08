/**
 * API 请求地址：
 * - 默认使用相对路径 `/api/...`（须由 `npm run dev` 的 Vite 代理到后端）
 * - 可选 `VITE_API_BASE`：只写「协议 + 主机 + 端口」，**不要**带 `/api`
 *   正确：http://127.0.0.1:8010
 *   错误：http://127.0.0.1:8010/api  （会导致 /api/api/... 而 404）
 */
export function apiUrl(path: string): string {
  const raw = import.meta.env.VITE_API_BASE
  let base = typeof raw === 'string' ? raw.trim() : ''
  if (!base) {
    return path.startsWith('/') ? path : `/${path}`
  }
  base = base.replace(/\/$/, '')
  // 用户若误写成 .../8010/api，去掉末尾 /api，避免 /api/api/requirements
  if (path.startsWith('/api') && base.endsWith('/api')) {
    base = base.slice(0, -4)
  }
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}
