import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiRequestError, api } from '../api/client'
import { FieldError, FormMessage } from '../components/FormMessage'

export function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [emailError, setEmailError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setEmailError(''); setBusy(true)
    try {
      await api.login({ email, password })
      navigate('/profile', { replace: true })
    } catch (caught) {
      if (caught instanceof ApiRequestError && caught.code === 'validation_error') {
        setEmailError(caught.details?.find((item) => item.field === 'email')?.message || '')
        setError(caught.details?.some((item) => item.field === 'password') ? 'Vui lòng kiểm tra lại mật khẩu.' : caught.message)
      } else setError(caught instanceof Error ? caught.message : 'Đăng nhập chưa thành công.')
    } finally { setBusy(false) }
  }

  return <section className="mx-auto grid max-w-5xl overflow-hidden rounded-[2rem] bg-white shadow-[0_20px_70px_-45px_#426b5a] md:grid-cols-[0.92fr_1.08fr]">
    <aside className="relative hidden min-h-[560px] flex-col justify-between overflow-hidden bg-[#234d40] p-10 text-white md:flex">
      <div className="absolute -right-16 -top-20 size-72 rounded-full border border-white/10" /><div className="absolute -bottom-32 -left-24 size-80 rounded-full bg-[#6ea98d]/20" />
      <p className="relative text-sm text-white/70">KHÔNG GIAN HỌC CỦA BẠN</p>
      <div className="relative"><span className="mb-6 block text-5xl">✦</span><h1 className="max-w-sm text-4xl font-semibold leading-tight tracking-tight">Học ngôn ngữ theo nhịp của riêng bạn.</h1><p className="mt-5 max-w-sm leading-7 text-white/70">Mục tiêu rõ ràng, lộ trình vừa sức và từng bước tiến bộ được lưu lại.</p></div>
      <p className="relative text-sm text-white/60">Chào mừng bạn quay trở lại.</p>
    </aside>
    <div className="p-7 sm:p-12 md:p-14">
      <p className="text-sm font-medium text-[#43836a]">Rất vui được gặp lại</p><h2 className="mt-2 text-3xl font-semibold tracking-tight">Đăng nhập</h2><p className="mt-2 text-sm leading-6 text-[#74867e]">Tiếp tục hành trình học tập của bạn.</p>
      <form onSubmit={submit} className="mt-8 space-y-5">
        {error && <FormMessage>{error}</FormMessage>}
        <label className="field-label">Email<input className="field-input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ban@example.com" /><FieldError>{emailError}</FieldError></label>
        <label className="field-label">Mật khẩu<input className="field-input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Nhập mật khẩu" /></label>
        <button disabled={busy} className="primary-button w-full">{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
      </form>
      <p className="mt-7 text-center text-sm text-[#74867e]">Chưa có tài khoản? <Link className="font-semibold text-[#28765c] hover:underline" to="/register">Tạo tài khoản</Link></p>
    </div>
  </section>
}
