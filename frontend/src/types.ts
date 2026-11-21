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

export interface ApiError {
  code: string
  message: string
  details?: Array<{ field: string; type: string; message: string }>
}
