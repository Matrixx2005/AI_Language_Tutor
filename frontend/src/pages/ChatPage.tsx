import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { AlertTriangle, Bot, Info, MessageSquarePlus, RotateCcw, Send, ShieldAlert } from 'lucide-react'
import { ApiRequestError, api } from '../api/client'
import { FormMessage } from '../components/FormMessage'
import { Loading } from '../components/Loading'
import { useCountdown } from '../hooks/useCountdown'
import { canRetry, isLimitCode, isLlmCode, messageForCode } from '../lib/apiErrors'
import { SESSION_SWITCH_LOCKED_REASON, charCount, collapseRetriedTurns, isForCurrentSession, pickSession, precedingUserContent } from '../lib/chat'
import { hasNoValidCitation, orderSources, ragModeLabel, resolveMode, showNoSourceNotice } from '../lib/rag'
import { parseRichText, type Inline } from '../lib/richText'
import { formatWait, formatWaitApprox } from '../lib/time'
import type { ChatMessage, ChatSession, RagConfig, RagMode } from '../types'

/** Mặc định hiển thị; máy chủ (CHAT_MAX_MESSAGE_CHARS) mới là nơi quyết định và báo message_too_long. */
const MAX_CHARS = 2000
/** Khi máy chủ không gửi Retry-After (không nên xảy ra), vẫn khóa ngắn để tránh gửi dồn. */
const FALLBACK_WAIT_SECONDS = 10

type LoadState = 'loading' | 'ready' | 'error'

interface UiError { code: string; message: string }

/** Tin đang gửi (hiện ngay, trước khi máy chủ trả lời). Lỗi giới hạn/mạng: giữ lại để "Thử lại". */
interface Pending { content: string; state: 'sending' | 'failed'; error?: UiError }

function toUiError(caught: unknown): UiError {
  if (caught instanceof ApiRequestError) return { code: caught.code, message: messageForCode(caught.code, caught.message) }
  return { code: 'unknown', message: messageForCode(null) }
}

export function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [sessionsState, setSessionsState] = useState<LoadState>('loading')
  const [selectedId, setSelectedIdState] = useState<string | null>(null)
  /**
   * Phiên đang chọn, cập nhật ĐỒNG BỘ cùng state: các yêu cầu bất đồng bộ (gửi tin, tải lịch sử) so với
   * ref này khi có kết quả, vì giá trị `selectedId` trong closure có thể đã cũ.
   */
  const selectedIdRef = useRef<string | null>(null)
  const setSelectedId = useCallback((id: string | null) => {
    selectedIdRef.current = id
    setSelectedIdState(id)
  }, [])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [messagesState, setMessagesState] = useState<LoadState>('ready')
  const [pending, setPending] = useState<Pending | null>(null)
  const [retryingMessageId, setRetryingMessageId] = useState<string | null>(null)
  const [text, setText] = useState('')
  const [composerError, setComposerError] = useState('')
  const [limitError, setLimitError] = useState<UiError | null>(null)
  const [showSessions, setShowSessions] = useState(false)
  const [creating, setCreating] = useState(false)
  const [ragConfig, setRagConfig] = useState<RagConfig | null>(null)
  /** '' = theo chế độ mặc định của máy chủ. */
  const [ragMode, setRagMode] = useState<RagMode | ''>('')
  const countdown = useCountdown()
  const endRef = useRef<HTMLDivElement>(null)
  /** Phiên vừa được tạo NGAY trong lúc gửi tin: không xóa tin đang chờ, không tải lại lịch sử rỗng. */
  const createdWhileSendingRef = useRef<string | null>(null)

  const loadSessions = useCallback(async (preferredId: string | null) => {
    try {
      const list = await api.listChatSessions()
      setSessions(list)
      setSessionsState('ready')
      return pickSession(list, preferredId)
    } catch {
      setSessionsState('error')
      return preferredId
    }
  }, [])

  const loadMessages = useCallback(async (sessionId: string) => {
    setMessagesState('loading')
    try {
      const list = await api.listChatMessages(sessionId)
      // Lịch sử của phiên khác về muộn (người dùng đã chuyển phiên): bỏ qua.
      if (!isForCurrentSession(sessionId, selectedIdRef.current)) return
      setMessages(list)
      setMessagesState('ready')
    } catch {
      if (isForCurrentSession(sessionId, selectedIdRef.current)) setMessagesState('error')
    }
  }, [])

  useEffect(() => {
    loadSessions(null).then((id) => setSelectedId(id))
  }, [loadSessions, setSelectedId])

  useEffect(() => {
    // Không tải được cấu hình thì vẫn chat được (theo mặc định máy chủ); chỉ không biết trước chế độ.
    api.getRagConfig().then(setRagConfig).catch(() => setRagConfig(null))
  }, [])

  useEffect(() => {
    if (selectedId && selectedId === createdWhileSendingRef.current) {
      createdWhileSendingRef.current = null
      return
    }
    setPending(null)
    setComposerError('')
    if (selectedId) loadMessages(selectedId)
    else setMessages([])
  }, [selectedId, loadMessages])

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, pending])

  async function newSession() {
    setCreating(true)
    try {
      const created = await api.createChatSession()
      setSessions((list) => [created, ...list.filter((s) => s.session_id !== created.session_id)])
      setSelectedId(created.session_id)
      setShowSessions(false)
    } catch (caught) {
      setComposerError(toUiError(caught).message)
    } finally {
      setCreating(false)
    }
  }

  /** Gửi `content`. Dùng cho tin mới, "Thử lại" tin pending, và "Thử lại" lượt lỗi đã lưu. */
  async function send(content: string, retryOfMessageId: string | null = null) {
    const trimmed = content.trim()
    if (!trimmed) return
    setComposerError('')
    setLimitError(null)
    setRetryingMessageId(retryOfMessageId)
    setPending({ content: trimmed, state: 'sending' })

    let sessionId = selectedId
    try {
      if (!sessionId) {
        const created = await api.createChatSession()
        sessionId = created.session_id
        createdWhileSendingRef.current = sessionId
        setMessages([])
        setSessions((list) => [created, ...list])
        setSelectedId(sessionId)
      }
      const turn = await api.sendChatMessage(sessionId, trimmed, ragMode || undefined)
      if (!isForCurrentSession(sessionId, selectedIdRef.current)) {
        // Người dùng đã sang phiên khác (nút đổi phiên bị khóa khi đang gửi, đây là lớp chặn thứ hai):
        // tin đã lưu ở máy chủ, sẽ hiện khi mở lại phiên đó; chỉ làm mới danh sách phiên.
        loadSessions(selectedIdRef.current)
        return
      }
      // Lượt lỗi vừa được thử lại thành công: tải lại lịch sử để máy chủ là nguồn sự thật.
      if (retryOfMessageId) await loadMessages(sessionId)
      else setMessages((list) => [...list, turn.user_message, turn.assistant_message])
      setPending(null)
      loadSessions(sessionId) // tiêu đề/thứ tự phiên đổi sau tin đầu tiên
    } catch (caught) {
      const error = toUiError(caught)
      const retryAfter = caught instanceof ApiRequestError ? caught.retryAfterSeconds : undefined
      // Giới hạn tần suất áp dụng cho cả tài khoản, nên đếm ngược luôn bật kể cả khi đã đổi phiên.
      const current = isForCurrentSession(sessionId, selectedIdRef.current)
      if (isLlmCode(error.code) || error.code === 'internal_error') {
        // Máy chủ ĐÃ lưu tin người dùng + dòng trợ lý status="error": hiển thị theo lịch sử máy chủ.
        if (sessionId) await loadMessages(sessionId) // tự bỏ qua nếu không còn là phiên đang chọn
        if (current) setPending(null)
        if (error.code === 'llm_rate_limited' || error.code === 'llm_quota_exhausted') {
          countdown.start(retryAfter ?? FALLBACK_WAIT_SECONDS)
        }
      } else if (isLimitCode(error.code)) {
        // Bị từ chối trước khi lưu: giữ tin để "Thử lại" sau khi hết giờ chờ.
        setLimitError(error)
        countdown.start(retryAfter ?? FALLBACK_WAIT_SECONDS)
        if (current) setPending({ content: trimmed, state: 'failed', error })
      } else if (!canRetry(error.code)) {
        // Phải sửa nội dung (quá dài, sai định dạng...): trả nội dung về ô nhập.
        if (current) setPending(null)
        setText(trimmed)
        setComposerError(error.message)
      } else {
        if (error.code === 'chat_session_not_found') loadSessions(null).then(setSelectedId)
        if (current) setPending({ content: trimmed, state: 'failed', error })
      }
    } finally {
      setRetryingMessageId(null)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (sendBlocked) return
    const content = text
    setText('')
    send(content)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter gửi, Shift+Enter xuống dòng. Bỏ qua khi đang gõ bằng bộ gõ (Telex/VNI xác nhận chữ bằng Enter).
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  const sending = pending?.state === 'sending'
  const waiting = countdown.remaining > 0
  const dailyLimit = limitError?.code === 'chat_daily_limit_reached'
  const waitText = dailyLimit ? formatWaitApprox(countdown.remaining) : formatWait(countdown.remaining)
  const sendBlocked = sending || waiting || !text.trim()
  const blockedReason = sending ? 'Đang chờ gia sư trả lời…' : waiting ? `Đợi ${waitText}` : ''
  const counter = charCount(text.length, MAX_CHARS)
  const activeMode = resolveMode(ragMode, ragConfig?.default_mode ?? null)

  // Ẩn lượt lỗi đã được thử lại; khi đang thử lại một lượt lỗi, tạm ẩn lượt đó để không hiện hai lần.
  const visible = collapseRetriedTurns(messages).filter((_, index, list) => {
    if (!retryingMessageId) return true
    const retryIndex = list.findIndex((m) => m.message_id === retryingMessageId)
    return index !== retryIndex && index !== retryIndex - 1
  })
  const lastFailedId = (() => {
    const last = visible[visible.length - 1]
    return last && last.role === 'assistant' && last.status === 'error' ? last.message_id : null
  })()

  return <div className="mx-auto max-w-6xl">
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><p className="text-sm font-medium text-[#43836a]">GIA SƯ AI</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">Hỏi đáp tiếng Anh</h1></div>
      <button type="button" className="secondary-button lg:hidden" aria-expanded={showSessions} onClick={() => setShowSessions((v) => !v)}>
        Các cuộc trò chuyện ({sessions.length})
      </button>
    </div>

    <div className="grid gap-5 lg:grid-cols-[17rem_1fr]">
      <aside className={`${showSessions ? 'block' : 'hidden'} rounded-[1.5rem] bg-white p-4 lg:block`} aria-label="Danh sách cuộc trò chuyện">
        <button type="button" className="primary-button w-full gap-2" onClick={newSession} disabled={creating || sending}
          title={sending ? SESSION_SWITCH_LOCKED_REASON : undefined} aria-describedby={sending ? 'session-lock-hint' : undefined}>
          <MessageSquarePlus size={17} /> {creating ? 'Đang tạo…' : 'Cuộc trò chuyện mới'}
        </button>
        {sending && <p id="session-lock-hint" className="mt-2 text-xs text-[#74867e]">{SESSION_SWITCH_LOCKED_REASON}</p>}
        <div className="mt-4">
          {sessionsState === 'loading' && <Loading label="Đang tải cuộc trò chuyện…" />}
          {sessionsState === 'error' && <div className="space-y-2"><FormMessage>Không tải được danh sách cuộc trò chuyện.</FormMessage><button type="button" className="secondary-button w-full" onClick={() => loadSessions(selectedId)}>Thử lại</button></div>}
          {sessionsState === 'ready' && sessions.length === 0 && <p className="px-2 py-6 text-center text-sm text-[#74867e]">Chưa có cuộc trò chuyện nào. Hãy gửi câu hỏi đầu tiên.</p>}
          {sessionsState === 'ready' && sessions.length > 0 && <ul className="space-y-1">
            {sessions.map((s) => <li key={s.session_id}>
              <button type="button" onClick={() => { setSelectedId(s.session_id); setShowSessions(false) }}
                aria-current={s.session_id === selectedId ? 'true' : undefined}
                disabled={sending && s.session_id !== selectedId}
                title={sending && s.session_id !== selectedId ? SESSION_SWITCH_LOCKED_REASON : undefined}
                aria-describedby={sending ? 'session-lock-hint' : undefined}
                className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition ${s.session_id === selectedId ? 'bg-[#edf5ef] font-semibold text-[#28765c]' : 'hover:bg-[#f5f7f2] disabled:hover:bg-transparent'}`}>
                <span className="block truncate">{s.title || 'Cuộc trò chuyện mới'}</span>
                <span className="block text-xs font-normal text-[#87958f]">{new Date(s.updated_at).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })}</span>
              </button>
            </li>)}
          </ul>}
        </div>
      </aside>

      <section className="flex min-h-[32rem] flex-col rounded-[1.5rem] bg-white" aria-label="Khung chat">
        <div className="space-y-1.5 border-b border-[#eef2ee] px-4 py-3 text-xs text-[#5f736b] sm:px-6">
          {showNoSourceNotice(activeMode)
            ? <p className="flex items-start gap-2"><Info size={14} className="mt-0.5 shrink-0" />Chế độ "Chỉ AI": câu trả lời không dẫn nguồn (không dùng tài liệu). Hãy kiểm tra lại kiến thức quan trọng.</p>
            : <p className="flex items-start gap-2"><Info size={14} className="mt-0.5 shrink-0" />Câu trả lời dựa trên các bài ngữ pháp của ứng dụng (bản nháp, chưa được giáo viên duyệt); nguồn hiện dưới mỗi câu trả lời.</p>}
          <p className="flex items-start gap-2"><ShieldAlert size={14} className="mt-0.5 shrink-0" />Nội dung chat được gửi tới Google Gemini. Với gói miễn phí, Google có thể dùng nội dung để cải thiện sản phẩm và người đánh giá có thể đọc — không nhập thông tin cá nhân.</p>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-6" aria-live="polite">
          {messagesState === 'loading' && <Loading label="Đang tải tin nhắn…" />}
          {messagesState === 'error' && selectedId && <div className="space-y-2"><FormMessage>Không tải được tin nhắn.</FormMessage><button type="button" className="secondary-button" onClick={() => loadMessages(selectedId)}>Tải lại</button></div>}
          {messagesState === 'ready' && visible.length === 0 && !pending && <div className="py-12 text-center text-sm text-[#74867e]"><Bot className="mx-auto mb-3 text-[#9fc3b1]" size={32} />Hỏi gia sư bất cứ điều gì về ngữ pháp, từ vựng hay cách dùng tiếng Anh.</div>}
          {messagesState === 'ready' && visible.map((m, index) => <MessageBubble key={m.message_id} message={m}
            onRetry={m.message_id === lastFailedId && m.error_code && canRetry(m.error_code) && !sending && !waiting
              ? () => { const content = precedingUserContent(visible, index); if (content) send(content, m.message_id) }
              : undefined} />)}
          {pending && <div className="flex justify-end">
            <div className="max-w-[85%] space-y-1.5">
              <p className="whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-[#28765c] px-4 py-2.5 text-sm text-white">{pending.content}</p>
              {pending.state === 'failed' && pending.error && <div role="alert" className="flex flex-wrap items-center justify-end gap-2 text-xs text-[#a14f3d]">
                <span>{pending.error.message}</span>
                <button type="button" className="inline-flex items-center gap-1 font-semibold underline disabled:no-underline" disabled={waiting}
                  onClick={() => send(pending.content)}><RotateCcw size={13} />{waiting ? `Thử lại sau ${waitText}` : 'Thử lại'}</button>
              </div>}
            </div>
          </div>}
          {sending && <p className="text-sm text-[#74867e]" role="status"><span className="inline-block size-2 animate-pulse rounded-full bg-[#6da98c]" /> Gia sư đang trả lời…</p>}
          <div ref={endRef} />
        </div>

        <form onSubmit={submit} className="border-t border-[#eef2ee] px-4 py-4 sm:px-6">
          {limitError && waiting && <div className="mb-3"><FormMessage>
            {limitError.message} {dailyLimit ? `Bạn có thể hỏi tiếp sau ${waitText}.` : `Vui lòng thử lại sau ${waitText}.`}
          </FormMessage></div>}
          {composerError && <div className="mb-3"><FormMessage>{composerError}</FormMessage></div>}
          <label htmlFor="chat-input" className="field-label">Tin nhắn của bạn</label>
          <textarea id="chat-input" className="field-input min-h-24 resize-y" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKeyDown}
            placeholder="Ví dụ: Khi nào dùng present perfect?" aria-describedby="chat-hint" />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <p id="chat-hint" className="text-xs text-[#87958f]">
                Enter để gửi, Shift+Enter để xuống dòng · <span className={counter.over ? 'font-semibold text-[#a14f3d]' : ''}>{counter.label} ký tự</span>
              </p>
              <label className="flex items-center gap-1.5 text-xs text-[#5f736b]">
                Chế độ trả lời
                <select value={ragMode} onChange={(e) => setRagMode(e.target.value as RagMode | '')}
                  className="max-w-[14rem] rounded-lg border border-[#dfe7e0] bg-white px-2 py-1 text-xs text-[#19342d]">
                  <option value="">Mặc định ({ragModeLabel(ragConfig?.default_mode)})</option>
                  {(ragConfig?.modes ?? ['llm_only', 'dense', 'hybrid']).map((m) => <option key={m} value={m}>{ragModeLabel(m)}</option>)}
                </select>
              </label>
            </div>
            <div className="flex items-center gap-3">
              {blockedReason && <span className="text-xs text-[#74867e]" aria-live="polite">{blockedReason}</span>}
              <button className="primary-button gap-2" disabled={sendBlocked} title={blockedReason || undefined}><Send size={16} /> Gửi</button>
            </div>
          </div>
        </form>
      </section>
    </div>
  </div>
}

function MessageBubble({ message, onRetry }: { message: ChatMessage; onRetry?: () => void }) {
  if (message.role === 'user') {
    return <div className="flex justify-end">
      <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-[#28765c] px-4 py-2.5 text-sm text-white">{message.content}</p>
    </div>
  }
  if (message.status === 'error') {
    return <div className="flex">
      <div role="alert" className="max-w-[85%] rounded-2xl rounded-bl-md border border-[#f1d0c8] bg-[#fff5f2] px-4 py-2.5 text-sm text-[#a14f3d]">
        <p className="flex items-start gap-2"><AlertTriangle size={16} className="mt-0.5 shrink-0" />{messageForCode(message.error_code)}</p>
        {onRetry && <button type="button" onClick={onRetry} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold underline"><RotateCcw size={13} /> Thử lại</button>}
      </div>
    </div>
  }
  return <div className="flex">
    <div className="max-w-[85%] space-y-1.5">
      <RichText text={message.content} />
      {message.truncated && <p className="text-xs text-[#8a6d2f]">Câu trả lời có thể bị cắt, hãy hỏi tiếp để xem phần còn lại.</p>}
      {message.rag_fallback && <p className="text-xs text-[#8a6d2f]">Không truy xuất được tài liệu lúc này nên câu trả lời không dùng tài liệu (không có nguồn).</p>}
      {hasNoValidCitation(message.sources) && <p className="text-xs text-[#8a6d2f]">Câu trả lời không trích dẫn tài liệu nào bên dưới — hãy kiểm tra lại.</p>}
      {message.sources && message.sources.length > 0 && <SourceList sources={message.sources} />}
    </div>
  </div>
}

/** Câu trả lời của gia sư: đoạn, danh sách, chữ đậm — dựng bằng phần tử React (không HTML, không thư viện). */
function RichText({ text }: { text: string }) {
  const inline = (parts: Inline[]) => parts.map((p, i) => p.bold ? <strong key={i}>{p.text}</strong> : <span key={i}>{p.text}</span>)
  return <div className="space-y-2 break-words rounded-2xl rounded-bl-md bg-[#f1f5f1] px-4 py-2.5 text-sm leading-relaxed text-[#19342d]">
    {parseRichText(text).map((block, i) => block.kind === 'list'
      ? (block.ordered
        ? <ol key={i} className="list-decimal space-y-1 pl-5">{block.items.map((item, j) => <li key={j}>{inline(item)}</li>)}</ol>
        : <ul key={i} className="list-disc space-y-1 pl-5">{block.items.map((item, j) => <li key={j}>{inline(item)}</li>)}</ul>)
      : <p key={i}>{block.lines.map((line, j) => <span key={j} className="block">{inline(line)}</span>)}</p>)}
  </div>
}

function SourceList({ sources }: { sources: NonNullable<ChatMessage['sources']> }) {
  return <div className="rounded-xl border border-[#e3e9e2] bg-white px-3 py-2 text-xs text-[#304b42]">
    <p className="mb-1 font-semibold">Nguồn (bài ngữ pháp của ứng dụng)</p>
    <ul className="space-y-1">
      {orderSources(sources).map((s) => <li key={s.n}>
        <details>
          <summary className="cursor-pointer">
            <span className="font-semibold">[{s.n}]</span> {s.title} · {s.level}{s.cited ? '' : ' · (không được trích dẫn)'}
          </summary>
          {/* Văn bản thuần: React tự escape. */}
          <p className="mt-1 whitespace-pre-wrap rounded-lg bg-[#f5f7f2] p-2 text-[#19342d]">{s.text}</p>
        </details>
      </li>)}
    </ul>
  </div>
}
