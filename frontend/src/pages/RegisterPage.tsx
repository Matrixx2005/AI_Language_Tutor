import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiRequestError, api } from '../api/client'
import { FieldError, FormMessage } from '../components/FormMessage'
import { useCountdown } from '../hooks/useCountdown'
import { messageForCode } from '../lib/apiErrors'
import { formatWait } from '../lib/time'

export function RegisterPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const countdown = useCountdown()
  const waiting = countdown.remaining > 0

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (waiting) return
    setError(''); setFieldErrors({}); setBusy(true)
    try {
      await api.register({ email, password, ...(name.trim() ? { display_name: name.trim() } : {}) })
      navigate('/login', { replace: true, state: { message: 'Tài khoản đã được tạo. Hãy đăng nhập để tiếp tục.' } })
    } catch (caught) {
      if (caught instanceof ApiRequestError && caught.code === 'auth_rate_limited') {
        countdown.start(caught.retryAfterSeconds ?? 60)
      } else if (caught instanceof ApiRequestError && caught.code === 'validation_error') {
        setFieldErrors(Object.fromEntries((caught.details || []).map((item) => [item.field, item.message])))
        setError(caught.message)
      } else setError(caught instanceof Error ? caught.message : 'Đăng ký chưa thành công.')
    } finally { setBusy(false) }
  }

  return <section className="mx-auto max-w-2xl rounded-[2rem] bg-white p-7 shadow-[0_20px_70px_-45px_#426b5a] sm:p-12">
    <div className="mx-auto max-w-lg"><p className="text-sm font-medium text-[#43836a]">Bắt đầu hành trình</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Tạo tài khoản</h1><p className="mt-2 text-sm leading-6 text-[#74867e]">Tài khoản của bạn sẽ có hồ sơ học tập riêng để lưu mục tiêu và trình độ hiện tại.</p>
      <form onSubmit={submit} className="mt-8 space-y-5">
        {waiting && <FormMessage>{messageForCode('auth_rate_limited')} Vui lòng thử lại sau {formatWait(countdown.remaining)}.</FormMessage>}
        {error && !waiting && <FormMessage>{error}</FormMessage>}
        <label className="field-label">Tên hiển thị <span className="font-normal text-[#96a39d]">(không bắt buộc)</span><input className="field-input" autoComplete="name" maxLength={100} value={name} onChange={(e) => setName(e.target.value)} placeholder="Tên bạn muốn mọi người gọi" /><FieldError>{fieldErrors.display_name}</FieldError></label>
        <label className="field-label">Email<input className="field-input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ban@example.com" /><FieldError>{fieldErrors.email}</FieldError></label>
        <label className="field-label">Mật khẩu<input className="field-input" type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Ít nhất 8 ký tự" /><span className="mt-1.5 block text-xs font-normal text-[#87958f]">Dùng ít nhất 8 ký tự và không dùng email làm mật khẩu.</span><FieldError>{fieldErrors.password}</FieldError></label>
        <button disabled={busy || waiting} className="primary-button w-full">{waiting ? `Đợi ${formatWait(countdown.remaining)}` : busy ? 'Đang tạo tài khoản…' : 'Tạo tài khoản'}</button>
      </form>
      <p className="mt-7 text-center text-sm text-[#74867e]">Đã có tài khoản? <Link className="font-semibold text-[#28765c] hover:underline" to="/login">Đăng nhập</Link></p>
    </div>
  </section>
}
