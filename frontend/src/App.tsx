import { Navigate, Route, Routes } from 'react-router-dom'
import { api } from './api/client'
import { AppLayout } from './components/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'

function ProtectedProfile() {
  return api.hasToken ? <ProfilePage /> : <Navigate to="/login" replace />
}

export default function App() {
  return <AppLayout><Routes>
    <Route path="/" element={<Navigate to={api.hasToken ? '/profile' : '/login'} replace />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route path="/profile" element={<ProtectedProfile />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></AppLayout>
}
