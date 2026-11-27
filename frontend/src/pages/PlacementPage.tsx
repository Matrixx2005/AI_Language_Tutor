import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, ClipboardCheck, RotateCcw, XCircle } from 'lucide-react'
import { ApiRequestError, api } from '../api/client'
import { FormMessage } from '../components/FormMessage'
import { Loading } from '../components/Loading'
import { messageForCode } from '../lib/apiErrors'
import { canApply, categoryLabel, countAnswered, inProgressId, latestCompletedId } from '../lib/placement'
import type { PlacementAttempt, PlacementAttemptSummary } from '../types'

/**
 * Làm bài CẢ TRANG (30 câu trắc nghiệm ngắn trên một trang): thấy toàn bộ đề, bỏ qua rồi quay lại dễ,
 * tiến độ luôn hiển thị, ít thao tác hơn làm từng câu. Đáp án chỉ nằm trong state của trang (không lưu
 * localStorage/sessionStorage); máy chủ không gửi đáp án đúng trước khi nộp.
 */
type View = 'loading' | 'intro' | 'taking' | 'result' | 'error'

function errorOf(caught: unknown): { code: string; message: string } {
  if (caught instanceof ApiRequestError) return { code: caught.code, message: messageForCode(caught.code, caught.message) }
  return { code: 'unknown', message: messageForCode(null) }
}

export function PlacementPage() {
  const [view, setView] = useState<View>('loading')
  const [summaries, setSummaries] = useState<PlacementAttemptSummary[]>([])
  const [attempt, setAttempt] = useState<PlacementAttempt | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [confirmBlank, setConfirmBlank] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [appliedLevel, setAppliedLevel] = useState('')

  const refreshSummaries = useCallback(async () => {
    const list = await api.listPlacementAttempts()
    setSummaries(list)
    return list
  }, [])

  const showAttempt = useCallback(async (attemptId: string) => {
    const detail = await api.getPlacementAttempt(attemptId)
    setAttempt(detail)
    setView(detail.status === 'completed' ? 'result' : 'taking')
  }, [])

  useEffect(() => {
    (async () => {
      try {
        const list = await refreshSummaries()
        const latest = latestCompletedId(list)
        if (!inProgressId(list) && latest) await showAttempt(latest)
        else setView('intro')
      } catch (caught) {
        setError(errorOf(caught).message)
        setView('error')
      }
    })()
  }, [refreshSummaries, showAttempt])

  /** `keepNotice`: thông báo hiển thị cùng bài mới (ví dụ bộ câu hỏi vừa đổi); mặc định xóa thông báo cũ. */
  async function start(keepNotice = '') {
    setBusy(true); setError(''); setNotice(keepNotice); setAppliedLevel('')
    try {
      const started = await api.startPlacement()
      setAttempt(started)
      setAnswers({})
      setConfirmBlank(false)
      setView('taking')
      window.scrollTo({ top: 0 })
      await refreshSummaries()
    } catch (caught) {
      setError(errorOf(caught).message)
    } finally {
      setBusy(false)
    }
  }

  async function submit() {
    if (!attempt?.questions) return
    const unanswered = attempt.questions.length - countAnswered(answers, attempt.questions.map((q) => q.question_id))
    if (unanswered > 0 && !confirmBlank) { setConfirmBlank(true); return }
    setBusy(true); setError(''); setNotice('')
    try {
      const done = await api.submitPlacement(attempt.attempt_id, answers)
      setAttempt(done)
      setAnswers({})
      setConfirmBlank(false)
      setView('result')
      window.scrollTo({ top: 0 })
      await refreshSummaries()
    } catch (caught) {
      const { code, message } = errorOf(caught)
      if (code === 'placement_already_submitted') {
        setNotice(message)
        await showAttempt(attempt.attempt_id)
      } else if (code === 'placement_questions_changed') {
        // Bộ câu hỏi đổi: máy chủ thay lượt dở bằng lượt mới khi gọi lại POST /placement/attempts.
        await start(`${message} Đã tạo bài mới, các lựa chọn trước đó chưa được lưu.`)
      } else {
        setError(message)
      }
    } finally {
      setBusy(false)
    }
  }

  async function apply() {
    if (!attempt) return
    setBusy(true); setError(''); setNotice('')
    try {
      const profile = await api.applyPlacement(attempt.attempt_id)
      setAppliedLevel(profile.current_level_code)
      await showAttempt(attempt.attempt_id)
      await refreshSummaries()
    } catch (caught) {
      const { code, message } = errorOf(caught)
      if (code === 'placement_superseded') {
        const list = await refreshSummaries()
        const latest = latestCompletedId(list)
        setNotice(`${message} Đang hiển thị kết quả bài làm gần nhất.`)
        if (latest) await showAttempt(latest)
      } else {
        setError(message)
      }
    } finally {
      setBusy(false)
    }
  }

  const header = <div className="mb-6"><p className="text-sm font-medium text-[#43836a]">KIỂM TRA ĐẦU VÀO</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">Xếp trình độ tiếng Anh</h1></div>
  const messages = <>
    {notice && <div role="status" className="mb-4 rounded-xl bg-[#edf5ef] px-4 py-3 text-sm text-[#28765c]">{notice}</div>}
    {error && <div className="mb-4"><FormMessage>{error}</FormMessage></div>}
  </>

  if (view === 'loading') return <div className="mx-auto max-w-3xl">{header}<Loading label="Đang tải bài kiểm tra…" /></div>
  if (view === 'error') return <div className="mx-auto max-w-3xl">{header}{messages}<button type="button" className="secondary-button" onClick={() => window.location.reload()}>Tải lại trang</button></div>

  if (view === 'intro') {
    const resuming = Boolean(inProgressId(summaries))
    return <div className="mx-auto max-w-3xl">{header}{messages}
      <section className="rounded-[1.5rem] bg-white p-6 sm:p-8">
        <ClipboardCheck className="text-[#28765c]" size={32} />
        <h2 className="mt-4 text-xl font-semibold">{resuming ? 'Bạn đang có một bài làm dở' : 'Bài kiểm tra 30 câu trắc nghiệm'}</h2>
        <p className="mt-2 text-sm leading-6 text-[#5f736b]">
          Gồm ngữ pháp và từ vựng ở nhiều mức độ. Mất khoảng 10–15 phút. Kết quả chỉ là <strong>đề xuất</strong> trình độ;
          bạn tự quyết định có cập nhật hồ sơ hay không. Chấm điểm tự động trên máy chủ, không dùng AI.
          {resuming && ' Các lựa chọn chưa nộp không được lưu, bạn sẽ làm lại từ đầu với cùng bộ câu hỏi.'}
        </p>
        <button type="button" className="primary-button mt-6" onClick={() => start()} disabled={busy}>
          {busy ? 'Đang chuẩn bị…' : resuming ? 'Tiếp tục bài đang làm' : 'Bắt đầu'}
        </button>
      </section>
      <History summaries={summaries} current={null} onView={(id) => showAttempt(id)} />
    </div>
  }

  if (view === 'taking' && attempt?.questions) {
    const questions = attempt.questions
    const answered = countAnswered(answers, questions.map((q) => q.question_id))
    const unanswered = questions.length - answered
    return <div className="mx-auto max-w-3xl">{header}{messages}
      <div className="sticky top-0 z-10 -mx-2 mb-5 rounded-2xl bg-[#f5f7f2]/95 px-2 py-3 backdrop-blur">
        <div className="flex items-center justify-between text-sm font-medium"><span>Đã trả lời {answered}/{questions.length}</span><span className="text-[#74867e]">Bỏ trống tính là sai</span></div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#dfe7e0]" role="progressbar" aria-valuemin={0} aria-valuemax={questions.length} aria-valuenow={answered} aria-label="Tiến độ làm bài">
          <div className="h-full rounded-full bg-[#28765c] transition-all" style={{ width: `${(answered / questions.length) * 100}%` }} />
        </div>
      </div>
      <ol className="space-y-4">
        {questions.map((q) => <li key={q.question_id}>
          <fieldset className="rounded-[1.25rem] bg-white p-5">
            <legend className="block w-full">
              <span className="block text-xs font-medium text-[#74867e]">Câu {q.position} · {categoryLabel(q.category)}</span>
              <span className="mt-1.5 block font-medium">{q.prompt}</span>
            </legend>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {q.options.map((option) => <label key={option} className={`flex cursor-pointer items-center gap-2.5 rounded-xl border px-3 py-2.5 text-sm transition ${answers[q.question_id] === option ? 'border-[#6da98c] bg-[#edf5ef]' : 'border-[#dfe7e0] hover:bg-[#fbfcfa]'}`}>
                <input type="radio" name={q.question_id} value={option} checked={answers[q.question_id] === option}
                  onChange={() => setAnswers((current) => ({ ...current, [q.question_id]: option }))} className="accent-[#28765c]" />
                {option}
              </label>)}
            </div>
            {answers[q.question_id] && <button type="button" className="mt-2 text-xs text-[#74867e] underline"
              onClick={() => setAnswers((current) => { const next = { ...current }; delete next[q.question_id]; return next })}>Bỏ chọn</button>}
          </fieldset>
        </li>)}
      </ol>
      <div className="mt-6 rounded-[1.25rem] bg-white p-5">
        {confirmBlank && unanswered > 0 && <div className="mb-4"><FormMessage>Bạn còn {unanswered} câu bỏ trống (tính là sai). Vẫn nộp bài?</FormMessage></div>}
        <div className="flex flex-wrap gap-3">
          <button type="button" className="primary-button" onClick={submit} disabled={busy}>
            {busy ? 'Đang chấm…' : confirmBlank && unanswered > 0 ? 'Vẫn nộp bài' : 'Nộp bài'}
          </button>
          {confirmBlank && unanswered > 0 && <button type="button" className="secondary-button" onClick={() => setConfirmBlank(false)}>Quay lại làm tiếp</button>}
        </div>
      </div>
    </div>
  }

  if (view === 'result' && attempt?.result) {
    const result = attempt.result
    const applicable = canApply(attempt.attempt_id, summaries, result.applied_at)
    const isLatest = latestCompletedId(summaries) === attempt.attempt_id
    return <div className="mx-auto max-w-3xl">{header}{messages}
      <section className="rounded-[1.5rem] bg-[#234d40] p-6 text-white sm:p-8">
        <p className="text-sm text-white/70">Trình độ đề xuất</p>
        <p className="mt-1 text-3xl font-semibold">{result.suggested_level_code} · {result.suggested_level_name_vi}</p>
        <p className="mt-3 text-sm text-white/80">Đúng {result.score}/{result.max_score} câu ({result.percent}%)</p>
        {appliedLevel && <p role="status" className="mt-4 rounded-xl bg-white/10 px-4 py-3 text-sm">Đã cập nhật trình độ hồ sơ thành {appliedLevel}.</p>}
        {!appliedLevel && result.applied_at && <p className="mt-4 text-sm text-white/80">Bạn đã dùng trình độ này cho hồ sơ.</p>}
        <div className="mt-5 flex flex-wrap gap-3">
          {applicable && <button type="button" className="primary-button bg-white text-[#234d40] hover:bg-[#edf5ef]" onClick={apply} disabled={busy}>{busy ? 'Đang cập nhật…' : 'Dùng trình độ này'}</button>}
          <button type="button" className="secondary-button border-white/40 bg-transparent text-white hover:bg-white/10" onClick={() => start()} disabled={busy}><RotateCcw size={15} /> Làm lại bài kiểm tra</button>
        </div>
        {!isLatest && <p className="mt-3 text-xs text-white/70">Đây là kết quả cũ; chỉ kết quả mới nhất mới dùng để cập nhật hồ sơ.</p>}
      </section>
      <p className="mt-3 text-xs leading-5 text-[#74867e]">{result.disclaimer}</p>

      <section className="mt-6 rounded-[1.5rem] bg-white p-6">
        <h2 className="text-lg font-semibold">Nhóm cần cải thiện</h2>
        {result.weak_groups.length === 0 ? <p className="mt-2 text-sm text-[#5f736b]">Không có nhóm nào dưới 60%.</p>
          : <ul className="mt-3 space-y-2">{result.weak_groups.map((g) => <li key={`${g.level_code}-${g.category}`} className="flex justify-between rounded-xl bg-[#fff5f2] px-4 py-2.5 text-sm"><span>{categoryLabel(g.category)} {g.level_code}</span><span>{g.correct}/{g.total} ({g.percent}%)</span></li>)}</ul>}
        <h2 className="mt-6 text-lg font-semibold">Chủ đề cần ôn</h2>
        {result.missed_topics.length === 0 ? <p className="mt-2 text-sm text-[#5f736b]">Không có.</p>
          : <ul className="mt-3 flex flex-wrap gap-2">{result.missed_topics.map((t) => <li key={t} className="rounded-full bg-[#f1f5f1] px-3 py-1 text-xs">{t}</li>)}</ul>}
      </section>

      <section className="mt-6 rounded-[1.5rem] bg-white p-6">
        <h2 className="text-lg font-semibold">Xem lại từng câu</h2>
        <ol className="mt-3 space-y-2">
          {result.review.map((item, index) => <li key={item.question_id}>
            <details className="rounded-xl border border-[#eef2ee] px-4 py-3">
              <summary className="flex cursor-pointer items-start gap-2 text-sm">
                {item.is_correct ? <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-[#28765c]" aria-label="Đúng" /> : <XCircle size={17} className="mt-0.5 shrink-0 text-[#a14f3d]" aria-label="Sai" />}
                <span>Câu {index + 1}: {item.prompt}</span>
              </summary>
              <dl className="mt-3 space-y-1 pl-6 text-sm">
                <div><dt className="inline text-[#74867e]">Bạn chọn: </dt><dd className="inline">{item.selected ?? '(bỏ trống)'}</dd></div>
                <div><dt className="inline text-[#74867e]">Đáp án đúng: </dt><dd className="inline font-medium">{item.correct_answer}</dd></div>
                {item.explanation && <div><dt className="inline text-[#74867e]">Giải thích: </dt><dd className="inline">{item.explanation}</dd></div>}
              </dl>
            </details>
          </li>)}
        </ol>
      </section>
      <History summaries={summaries} current={attempt.attempt_id} onView={(id) => { setNotice(''); setAppliedLevel(''); showAttempt(id) }} />
    </div>
  }

  return <div className="mx-auto max-w-3xl">{header}{messages}<button type="button" className="primary-button" onClick={() => start()}>Bắt đầu</button></div>
}

function History({ summaries, current, onView }: { summaries: PlacementAttemptSummary[]; current: string | null; onView: (id: string) => void }) {
  const completed = summaries.filter((s) => s.status === 'completed')
  if (completed.length === 0) return null
  return <section className="mt-6 rounded-[1.5rem] bg-white p-6">
    <h2 className="text-lg font-semibold">Các lần làm trước</h2>
    <ul className="mt-3 divide-y divide-[#eef2ee]">
      {completed.map((s) => <li key={s.attempt_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
        <span>{s.completed_at ? new Date(s.completed_at).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' }) : ''} · {s.suggested_level_code} · {s.score}/{s.max_score}{s.applied_at ? ' · đã áp dụng' : ''}</span>
        {s.attempt_id === current ? <span className="text-xs text-[#74867e]">Đang xem</span>
          : <button type="button" className="text-xs font-semibold text-[#28765c] underline" onClick={() => onView(s.attempt_id)}>Xem kết quả</button>}
      </li>)}
    </ul>
  </section>
}
