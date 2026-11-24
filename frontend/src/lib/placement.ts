/** Logic thuần cho trang placement. Không phụ thuộc React. */

const CATEGORY_LABELS: Record<string, string> = { grammar: 'Ngữ pháp', vocabulary: 'Từ vựng' }

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category
}

/** Số câu đã chọn đáp án (bỏ qua câu bỏ trống). */
export function countAnswered(answers: Readonly<Record<string, string | undefined>>, questionIds: readonly string[]): number {
  return questionIds.filter((id) => Boolean(answers[id])).length
}

export interface AttemptSummaryLike {
  attempt_id: string
  status: string
  started_at: string
  completed_at: string | null
}

/** Lượt hoàn thành MỚI NHẤT (theo completed_at, rồi started_at) — chỉ lượt này được "Dùng trình độ này". */
export function latestCompletedId(summaries: readonly AttemptSummaryLike[]): string | null {
  const completed = summaries.filter((s) => s.status === 'completed' && s.completed_at)
  completed.sort((a, b) =>
    (b.completed_at ?? '').localeCompare(a.completed_at ?? '') || b.started_at.localeCompare(a.started_at),
  )
  return completed[0]?.attempt_id ?? null
}

export function inProgressId(summaries: readonly AttemptSummaryLike[]): string | null {
  return summaries.find((s) => s.status === 'in_progress')?.attempt_id ?? null
}

/** Chỉ cho xác nhận ở lượt mới nhất chưa áp dụng. */
export function canApply(attemptId: string, summaries: readonly AttemptSummaryLike[], appliedAt: string | null): boolean {
  return appliedAt === null && latestCompletedId(summaries) === attemptId
}
