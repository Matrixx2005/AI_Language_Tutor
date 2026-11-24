import { Navigate } from 'react-router-dom'
import { api } from '../api/client'

/** Chỉ hiển thị khi đã đăng nhập; chưa có token → về trang đăng nhập. */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return api.hasToken ? <>{children}</> : <Navigate to="/login" replace />
}
