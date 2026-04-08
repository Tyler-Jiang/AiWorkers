import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// 默认端口：因本机 8000/5173 常被占用，API 用 8010、前端用 5174（与 README 一致）
// 若 8001 上仍有旧 uvicorn 进程，8010 可避免打到旧版 0.2.0
const API_PORT = 8010

const proxy = {
  '/api': { target: `http://127.0.0.1:${API_PORT}`, changeOrigin: true },
  '/health': { target: `http://127.0.0.1:${API_PORT}`, changeOrigin: true },
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    host: true,
    proxy,
  },
  /** 与 dev 相同代理，避免 `npm run preview` 时 /api 返回 404 */
  preview: {
    port: 5174,
    strictPort: true,
    proxy,
  },
})
