/** Ánh xạ mã lỗi máy chủ → thông điệp tiếng Việt và cách xử lý. Thuần TypeScript, không phụ thuộc React. */

/** Giới hạn tần suất của ứng dụng (khác lỗi của nhà cung cấp AI). Luôn kèm Retry-After. */
export const LIMIT_CODES = [
  'chat_rate_limited',
  'chat_daily_limit_reached',
  'chat_busy',
  'service_busy',
  'auth_rate_limited',
] as const

/** Lỗi phía gia sư AI (nhà cung cấp LLM). */
export const LLM_CODES = [
  'llm_timeout',
  'llm_provider_error',
  'llm_invalid_response',
  'llm_content_blocked',
  'llm_not_configured',
  'llm_rate_limited',
  'llm_quota_exhausted',
] as const

const MESSAGES: Record<string, string> = {
  // Giới hạn của ứng dụng
  chat_rate_limited: 'Bạn đang gửi tin hơi nhanh.',
  chat_daily_limit_reached: 'Bạn đã dùng hết lượt hỏi gia sư AI hôm nay.',
  chat_busy: 'Gia sư AI đang trả lời tin trước của bạn.',
  service_busy: 'Hệ thống đang bận.',
  auth_rate_limited: 'Bạn đã thử quá nhiều lần.',
  // Gia sư AI
  llm_timeout: 'Gia sư AI phản hồi quá lâu nên chưa trả lời được.',
  llm_provider_error: 'Gia sư AI tạm thời không phản hồi.',
  llm_invalid_response: 'Gia sư AI trả lời không hợp lệ.',
  llm_content_blocked: 'Nội dung này không thể xử lý. Hãy diễn đạt câu hỏi theo cách khác.',
  llm_not_configured: 'Gia sư AI chưa được cấu hình trên máy chủ.',
  llm_rate_limited: 'Gia sư AI đang quá tải.',
  llm_quota_exhausted: 'Gia sư AI đã hết lượt dùng trong hôm nay.',
  internal_error: 'Đã có lỗi ngoài dự kiến.',
  network_error: 'Không thể kết nối máy chủ.',
  // Chat
  chat_session_not_found: 'Không tìm thấy cuộc trò chuyện.',
  // Placement
  placement_not_available: 'Chưa có bài kiểm tra đầu vào cho ngôn ngữ của bạn.',
  placement_already_submitted: 'Bài kiểm tra này đã được nộp.',
  placement_questions_changed: 'Bộ câu hỏi vừa được cập nhật nên bài làm dở không còn dùng được.',
  placement_superseded: 'Đã có kết quả mới hơn.',
  placement_not_completed: 'Hãy nộp bài trước khi cập nhật trình độ.',
  placement_not_found: 'Không tìm thấy bài kiểm tra.',
}

/** Lỗi mà gửi lại y nguyên vô ích (phải sửa nội dung hoặc cấu hình). */
const NOT_RETRYABLE = new Set(['llm_content_blocked', 'llm_not_configured', 'message_too_long', 'validation_error'])

export function isLimitCode(code: string): boolean {
  return (LIMIT_CODES as readonly string[]).includes(code)
}

export function isLlmCode(code: string): boolean {
  return (LLM_CODES as readonly string[]).includes(code)
}

export function canRetry(code: string): boolean {
  return !NOT_RETRYABLE.has(code)
}

/**
 * Thông điệp hiển thị. Ưu tiên bản dịch theo mã; riêng lỗi kiểm tra dữ liệu (message_too_long,
 * validation_error...) dùng thông điệp máy chủ vì nó chứa chi tiết (ví dụ giới hạn ký tự).
 */
export function messageForCode(code: string | null | undefined, serverMessage?: string): string {
  if (code && MESSAGES[code]) return MESSAGES[code]
  if (serverMessage) return serverMessage
  return 'Yêu cầu chưa thành công. Vui lòng thử lại.'
}
