import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Mặc định Vite trên Windows chỉ nghe IPv6 ::1 → http://127.0.0.1:5173 không mở được.
    // Ghim IPv4 cho thống nhất với backend (127.0.0.1:8000); http://localhost:5173 vẫn dùng được.
    host: '127.0.0.1',
    port: 5173,
    // Cổng bận thì báo lỗi, không tự đổi sang 5174 (origin mới sẽ bị CORS của backend chặn).
    strictPort: true,
  },
})
