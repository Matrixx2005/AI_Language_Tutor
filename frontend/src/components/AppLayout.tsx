import { BookOpen, LogOut, UserRound } from 'lucide-react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { api } from '../api/client'

export function AppLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const loggedIn = api.hasToken

  function logout() {
    api.clearToken()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#f5f7f2] text-[#19342d]">
      <header className="border-b border-[#e3e9e2] bg-white/85">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link to={loggedIn ? '/profile' : '/login'} className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-2xl bg-[#dff0e7] text-[#28765c]"><BookOpen size={20} /></span>
            <span><strong className="block text-sm tracking-tight">Học cùng bạn</strong><span className="text-xs text-[#74867e]">AI Language Tutor</span></span>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            {loggedIn ? <>
              <NavLink to="/profile" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}><UserRound size={16} /> Hồ sơ</NavLink>
              <button onClick={logout} className="nav-link text-[#74867e] hover:text-[#19342d]"><LogOut size={16} /> Đăng xuất</button>
            </> : <>
              <NavLink to="/login" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>Đăng nhập</NavLink>
              <NavLink to="/register" className="rounded-full bg-[#28765c] px-4 py-2.5 font-medium text-white transition hover:bg-[#205e49]">Tạo tài khoản</NavLink>
            </>}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">{children}</main>
      <footer className="mx-auto max-w-6xl px-5 pb-8 text-xs text-[#87958f] sm:px-8">Một bước nhỏ mỗi ngày, tiến bộ theo cách của bạn.</footer>
    </div>
  )
}
