import { BookOpen, ClipboardCheck, LogOut, MessagesSquare, UserRound } from 'lucide-react'
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
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 sm:px-8">
          <Link to={loggedIn ? '/profile' : '/login'} className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-2xl bg-[#dff0e7] text-[#28765c]"><BookOpen size={20} /></span>
            <span className="hidden min-[400px]:block"><strong className="block text-sm tracking-tight">Học cùng bạn</strong><span className="text-xs text-[#74867e]">AI Language Tutor</span></span>
          </Link>
          <nav className="flex items-center gap-1 text-sm sm:gap-2">
            {loggedIn ? <>
              {/* Màn hình hẹp chỉ hiện biểu tượng; aria-label giữ tên cho trình đọc màn hình. */}
              <NavLink to="/chat" aria-label="Gia sư AI" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}><MessagesSquare size={16} /><span className="hidden sm:inline">Gia sư AI</span></NavLink>
              <NavLink to="/placement" aria-label="Kiểm tra đầu vào" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}><ClipboardCheck size={16} /><span className="hidden sm:inline">Kiểm tra đầu vào</span></NavLink>
              <NavLink to="/profile" aria-label="Hồ sơ" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}><UserRound size={16} /><span className="hidden sm:inline">Hồ sơ</span></NavLink>
              <button onClick={logout} aria-label="Đăng xuất" className="nav-link text-[#74867e] hover:text-[#19342d]"><LogOut size={16} /><span className="hidden sm:inline">Đăng xuất</span></button>
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
