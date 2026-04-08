import { defineConfig } from 'vite'

// 与办公室 STUDIO_OUTPUT_PREVIEW_URL 默认端口一致；勿与控制台 frontend（5174）混用
export default defineConfig({
  server: {
    port: 5180,
    strictPort: true,
    host: true,
  },
  preview: {
    port: 5180,
    strictPort: true,
    host: true,
  },
})
