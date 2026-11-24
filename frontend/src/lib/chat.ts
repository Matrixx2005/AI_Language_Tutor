/** Logic thuần cho trang chat. Không phụ thuộc React. */

export interface MessageLike {
  role: string
  content: string
  status: string
}

/**
 * Ẩn các lượt lỗi ĐÃ ĐƯỢC THỬ LẠI để không nhân đôi tin hiển thị.
 * Lượt lỗi = tin người dùng + ngay sau là tin trợ lý status="error". Nếu tin người dùng KẾ TIẾP có cùng
 * nội dung thì lượt lỗi đó đã được gửi lại → ẩn. Lượt lỗi chưa thử lại vẫn hiện (kèm nút "Thử lại").
 */
export function collapseRetriedTurns<T extends MessageLike>(messages: readonly T[]): T[] {
  const hidden = new Set<number>()
  for (let i = 0; i + 1 < messages.length; i += 1) {
    const user = messages[i]
    const reply = messages[i + 1]
    if (user.role !== 'user' || reply.role !== 'assistant' || reply.status !== 'error') continue
    const nextUser = messages.slice(i + 2).find((m) => m.role === 'user')
    if (nextUser && nextUser.content === user.content) {
      hidden.add(i)
      hidden.add(i + 1)
    }
  }
  return messages.filter((_, index) => !hidden.has(index))
}

/** Nội dung tin người dùng ngay trước tin trợ lý ở vị trí `index` (để "Thử lại" gửi đúng nội dung). */
export function precedingUserContent(messages: readonly MessageLike[], index: number): string | null {
  for (let i = index - 1; i >= 0; i -= 1) {
    if (messages[i].role === 'user') return messages[i].content
  }
  return null
}

/** Chọn phiên: phiên đang chọn nếu còn tồn tại, nếu không thì phiên mới nhất (đầu danh sách), hoặc null. */
export function pickSession(sessions: readonly { session_id: string }[], preferredId: string | null): string | null {
  if (preferredId && sessions.some((s) => s.session_id === preferredId)) return preferredId
  return sessions[0]?.session_id ?? null
}

/** Trạng thái bộ đếm ký tự (chỉ để hiển thị; máy chủ mới là nơi quyết định giới hạn). */
export function charCount(length: number, max: number): { label: string; over: boolean } {
  return { label: `${length}/${max}`, over: length > max }
}
