/** Logic thuần cho chế độ RAG và nguồn trích dẫn trên trang chat. Không phụ thuộc React. */
import type { ChatSource, RagMode } from '../types'

export const RAG_MODE_LABELS: Record<RagMode, string> = {
  llm_only: 'Chỉ AI (không dùng tài liệu)',
  dense: 'Tài liệu — tìm theo nghĩa (dense)',
  hybrid: 'Tài liệu — kết hợp (hybrid)',
}

export function ragModeLabel(mode: string | null | undefined): string {
  return mode && mode in RAG_MODE_LABELS ? RAG_MODE_LABELS[mode as RagMode] : 'Mặc định của máy chủ'
}

/** Chế độ sẽ dùng: lựa chọn của người dùng, nếu bỏ trống thì mặc định của máy chủ (null = chưa biết). */
export function resolveMode(selected: RagMode | '', serverDefault: RagMode | null): RagMode | null {
  return selected || serverDefault
}

/** Thông báo "AI không dẫn nguồn" chỉ hiện khi chắc chắn đang ở chế độ llm_only. */
export function showNoSourceNotice(mode: RagMode | null): boolean {
  return mode === 'llm_only'
}

/** Nguồn được trích dẫn lên trước, rồi theo số [n]. Không đổi mảng gốc. */
export function orderSources(sources: readonly ChatSource[] | null | undefined): ChatSource[] {
  return [...(sources ?? [])].sort((a, b) => Number(b.cited) - Number(a.cited) || a.n - b.n)
}

/** Câu trả lời RAG không trích dẫn nguồn nào hợp lệ (để giao diện nhắc người học tự kiểm tra). */
export function hasNoValidCitation(sources: readonly ChatSource[] | null | undefined): boolean {
  return Boolean(sources && sources.length > 0 && !sources.some((s) => s.cited))
}
