import { parseRetryAfter } from '../lib/time'
import type {
  ApiError,
  ChatMessage,
  ChatSession,
  ChatTurn,
  Language,
  PlacementAttempt,
  PlacementAttemptSummary,
  Profile,
  ProfileUpdate,
  RagConfig,
  RagMode,
} from '../types'

const TOKEN_KEY = 'alt_access_token'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
    public readonly details?: ApiError['details'],
    /** Giây cần chờ từ header Retry-After (429); undefined nếu máy chủ không gửi. */
    public readonly retryAfterSeconds?: number,
  ) {
    super(message)
    this.name = 'ApiRequestError'
  }
}

/** Lớp duy nhất giao tiếp với backend; token chỉ được thêm tại đây. */
class ApiClient {
  get hasToken() {
    return Boolean(sessionStorage.getItem(TOKEN_KEY))
  }

  setToken(token: string) {
    sessionStorage.setItem(TOKEN_KEY, token)
  }

  clearToken() {
    sessionStorage.removeItem(TOKEN_KEY)
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers)
    headers.set('Accept', 'application/json')
    if (init.body) headers.set('Content-Type', 'application/json')
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (token) headers.set('Authorization', `Bearer ${token}`)

    let response: Response
    try {
      response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
    } catch {
      throw new ApiRequestError('Không thể kết nối máy chủ. Vui lòng thử lại.', 0, 'network_error')
    }

    if (response.status === 401) {
      this.clearToken()
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { error?: ApiError } | null
      const error = payload?.error
      throw new ApiRequestError(
        error?.message || 'Yêu cầu chưa thành công. Vui lòng thử lại.',
        response.status,
        error?.code || 'http_error',
        error?.details,
        parseRetryAfter(response.headers.get('Retry-After')),
      )
    }

    if (response.status === 204) return undefined as T
    return (await response.json()) as T
  }

  register(data: { email: string; password: string; display_name?: string }) {
    return this.request<Profile>('/auth/register', { method: 'POST', body: JSON.stringify(data) })
  }

  async login(data: { email: string; password: string }) {
    const result = await this.request<{ access_token: string; token_type: string; expires_in: number }>(
      '/auth/login', { method: 'POST', body: JSON.stringify(data) },
    )
    this.setToken(result.access_token)
    return result
  }

  getMyProfile() {
    return this.request<Profile>('/profile/me')
  }

  updateMyProfile(data: ProfileUpdate) {
    return this.request<Profile>('/profile/me', { method: 'PATCH', body: JSON.stringify(data) })
  }

  /** Danh sách trình độ hợp lệ; không hardcode A1/A2/B1 ở frontend. */
  getLanguage(languageCode: string) {
    return this.request<Language>(`/languages/${encodeURIComponent(languageCode)}`)
  }

  // ---------- Chat ----------

  listChatSessions() {
    return this.request<ChatSession[]>('/chat/sessions')
  }

  createChatSession() {
    return this.request<ChatSession>('/chat/sessions', { method: 'POST' })
  }

  listChatMessages(sessionId: string) {
    return this.request<ChatMessage[]>(`/chat/sessions/${encodeURIComponent(sessionId)}/messages`)
  }

  /** `ragMode` bỏ trống = chế độ mặc định của máy chủ (RAG_MODE). */
  sendChatMessage(sessionId: string, content: string, ragMode?: RagMode) {
    return this.request<ChatTurn>(`/chat/sessions/${encodeURIComponent(sessionId)}/messages`, {
      method: 'POST', body: JSON.stringify(ragMode ? { content, rag_mode: ragMode } : { content }),
    })
  }

  getRagConfig() {
    return this.request<RagConfig>('/chat/rag-config')
  }

  // ---------- Placement ----------

  /** Bắt đầu, hoặc nhận lại lượt đang làm. Câu hỏi KHÔNG kèm đáp án. */
  startPlacement() {
    return this.request<PlacementAttempt>('/placement/attempts', { method: 'POST' })
  }

  listPlacementAttempts() {
    return this.request<PlacementAttemptSummary[]>('/placement/attempts')
  }

  getPlacementAttempt(attemptId: string) {
    return this.request<PlacementAttempt>(`/placement/attempts/${encodeURIComponent(attemptId)}`)
  }

  /** Câu bỏ trống không cần gửi (máy chủ tính là sai). */
  submitPlacement(attemptId: string, answers: Record<string, string>) {
    return this.request<PlacementAttempt>(`/placement/attempts/${encodeURIComponent(attemptId)}/submit`, {
      method: 'POST', body: JSON.stringify({ answers }),
    })
  }

  applyPlacement(attemptId: string) {
    return this.request<Profile>(`/placement/attempts/${encodeURIComponent(attemptId)}/apply`, { method: 'POST' })
  }
}

export const api = new ApiClient()
