export interface Profile {
  user_id: string
  email: string
  display_name: string | null
  language_code: string
  current_level_code: string
  native_language_code: string
  learning_goal: string | null
  created_at: string
  updated_at: string
}

export interface ProfileUpdate {
  display_name?: string | null
  learning_goal?: string | null
  current_level_code?: string
}

export interface LevelOption {
  code: string
  display_name: string
  display_name_vi: string
}

/** Cấu hình ngôn ngữ từ languages/<code>.yaml (qua GET /languages/{code}). */
export interface Language {
  language_code: string
  display_name: string
  display_name_vi: string
  levels: LevelOption[]
}

// ---------- Chat (khớp backend/app/schemas/chat.py) ----------

export interface ChatSession {
  session_id: string
  language_code: string
  level_code: string | null
  retrieval_mode: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  message_id: string
  role: 'user' | 'assistant'
  content: string
  status: 'ok' | 'error'
  error_code: string | null
  truncated: boolean
  created_at: string
  /** Chế độ THỰC SỰ dùng cho câu trả lời (llm_only khi hạ cấp); null ở tin người dùng / dữ liệu cũ. */
  rag_mode?: RagMode | null
  rag_fallback?: boolean
  sources?: ChatSource[] | null
}

export type RagMode = 'llm_only' | 'dense' | 'hybrid'

/** Tài liệu đã truy xuất (khớp SourceRead); `n` là số dùng trong trích dẫn [n]. */
export interface ChatSource {
  n: number
  document_id: string
  title: string
  level: string
  rank: number
  score: number
  text: string
  cited: boolean
}

export interface RagConfig {
  default_mode: RagMode
  modes: RagMode[]
  top_k: number
}

export interface ChatTurn {
  user_message: ChatMessage
  assistant_message: ChatMessage
  has_citations: boolean
}

// ---------- Placement (khớp backend/app/schemas/placement.py) ----------

/** Câu hỏi khi đang làm bài: máy chủ KHÔNG gửi đáp án, giải thích, trình độ hay chủ đề. */
export interface PlacementQuestion {
  question_id: string
  position: number
  category: string
  prompt: string
  options: string[]
}

export interface PlacementGroup {
  level_code: string
  category: string
  correct: number
  total: number
  percent: number
  weak: boolean
}

/** Chỉ có SAU khi nộp bài. */
export interface PlacementReviewItem {
  question_id: string
  prompt: string
  options: string[]
  selected: string | null
  correct_answer: string
  is_correct: boolean
  explanation: string | null
}

export interface PlacementOutcome {
  score: number
  max_score: number
  percent: number
  suggested_level_code: string
  suggested_level_name_vi: string
  groups: PlacementGroup[]
  weak_groups: PlacementGroup[]
  missed_topics: string[]
  review: PlacementReviewItem[]
  applied_at: string | null
  disclaimer: string
}

export interface PlacementAttempt {
  attempt_id: string
  status: 'in_progress' | 'completed'
  language_code: string
  started_at: string
  completed_at: string | null
  questions: PlacementQuestion[] | null
  result: PlacementOutcome | null
}

export interface PlacementAttemptSummary {
  attempt_id: string
  status: 'in_progress' | 'completed'
  language_code: string
  started_at: string
  completed_at: string | null
  suggested_level_code: string | null
  score: number | null
  max_score: number | null
  applied_at: string | null
}

export interface ApiError {
  code: string
  message: string
  details?: Array<{ field: string; type: string; message: string }>
}
