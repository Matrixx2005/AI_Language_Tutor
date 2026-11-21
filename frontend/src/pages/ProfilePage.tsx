import { useEffect, useState, type FormEvent } from 'react'
import { ArrowUpRight, Check, Target, UserRound } from 'lucide-react'
import { ApiRequestError, api } from '../api/client'
import { FormMessage } from '../components/FormMessage'
import { Loading } from '../components/Loading'
import type { LevelOption, Profile } from '../types'

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [name, setName] = useState('')
  const [goal, setGoal] = useState('')
  const [level, setLevel] = useState('')
  const [levels, setLevels] = useState<LevelOption[]>([])
  const [levelsError, setLevelsError] = useState(false)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    api.getMyProfile().then(async (data) => {
      setProfile(data); setName(data.display_name || ''); setGoal(data.learning_goal || ''); setLevel(data.current_level_code)
      // Trình độ hợp lệ lấy từ cấu hình ngôn ngữ của chính hồ sơ (languages/<code>.yaml).
      try { setLevels((await api.getLanguage(data.language_code)).levels) } catch { setLevelsError(true) }
    }).catch((caught: unknown) => {
      if (!(caught instanceof ApiRequestError && caught.status === 401)) setError(caught instanceof Error ? caught.message : 'Không tải được hồ sơ.')
    }).finally(() => setLoading(false))
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try {
      const updated = await api.updateMyProfile({ display_name: name.trim() || null, learning_goal: goal.trim() || null, current_level_code: level.trim() })
      setProfile(updated); setName(updated.display_name || ''); setGoal(updated.learning_goal || '')
      setNotice('Hồ sơ của bạn đã được cập nhật.')
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Chưa lưu được thay đổi.') }
    finally { setBusy(false) }
  }

  if (loading) return <div className="mx-auto max-w-3xl rounded-[2rem] bg-white p-8"><Loading label="Đang tải hồ sơ của bạn…" /></div>
  return <div className="mx-auto max-w-5xl">
    <div className="mb-8"><p className="text-sm font-medium text-[#43836a]">KHÔNG GIAN CỦA BẠN</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Hồ sơ học tập</h1><p className="mt-2 text-[#74867e]">Điều chỉnh thông tin để hành trình học phù hợp với bạn.</p></div>
    {error && <div className="mb-5"><FormMessage>{error}</FormMessage></div>}
    <div className="grid gap-6 lg:grid-cols-[0.78fr_1.22fr]">
      <aside className="rounded-[1.75rem] bg-[#234d40] p-7 text-white sm:p-8"><span className="grid size-12 place-items-center rounded-2xl bg-white/10"><UserRound /></span><p className="mt-7 text-sm text-white/60">Tài khoản</p><h2 className="mt-1 break-all text-xl font-semibold">{profile?.display_name || profile?.email}</h2>{profile?.display_name && <p className="mt-1 break-all text-sm text-white/65">{profile.email}</p>}
        <div className="mt-8 border-t border-white/15 pt-6"><p className="text-sm text-white/60">Ngôn ngữ đang học</p><p className="mt-2 flex items-center gap-2 font-medium">{profile?.language_code.toUpperCase()} <ArrowUpRight size={16} className="text-[#a4d4b9]" /></p></div>
        <div className="mt-6 rounded-2xl bg-white/10 p-4"><p className="text-xs text-white/60">Hồ sơ được tạo</p><p className="mt-1 text-sm">{profile ? new Date(profile.created_at).toLocaleDateString('vi-VN', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'}</p></div>
      </aside>
      <section className="rounded-[1.75rem] bg-white p-6 shadow-[0_18px_60px_-48px_#426b5a] sm:p-9">
        <div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#e8f3ec] text-[#28765c]"><Target size={19} /></span><div><h2 className="text-lg font-semibold">Thông tin học tập</h2><p className="mt-1 text-sm text-[#74867e]">Các thay đổi sẽ được lưu vào hồ sơ của bạn.</p></div></div>
        {notice && <div role="status" className="mt-5 flex items-center gap-2 rounded-xl bg-[#edf7f0] px-4 py-3 text-sm text-[#28765c]"><Check size={17} />{notice}</div>}
        <form onSubmit={submit} className="mt-7 space-y-5">
          <label className="field-label">Tên hiển thị<input className="field-input" autoComplete="name" maxLength={100} value={name} onChange={(e) => setName(e.target.value)} placeholder="Tên bạn muốn mọi người gọi" /></label>
          <label className="field-label">Trình độ hiện tại
            <select className="field-input" required value={level} onChange={(e) => setLevel(e.target.value)} disabled={levelsError || levels.length === 0}>
              {/* Giữ trình độ đang lưu làm lựa chọn ngay cả khi chưa tải được danh sách. */}
              {!levels.some((option) => option.code === level) && level && <option value={level}>{level}</option>}
              {levels.map((option) => <option key={option.code} value={option.code}>{option.code} — {option.display_name_vi}</option>)}
            </select>
            <span className="mt-1.5 block text-xs font-normal text-[#87958f]">{levelsError ? 'Chưa tải được danh sách trình độ; trình độ hiện tại được giữ nguyên.' : 'Chọn trình độ bạn đang học.'}</span>
          </label>
          <label className="field-label">Mục tiêu học tập<textarea className="field-input min-h-28 resize-y" maxLength={1000} value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Bạn muốn đạt được điều gì khi học?" /></label>
          <button disabled={busy || !profile} className="primary-button">{busy ? 'Đang lưu…' : 'Lưu thay đổi'}</button>
        </form>
      </section>
    </div>
  </div>
}
