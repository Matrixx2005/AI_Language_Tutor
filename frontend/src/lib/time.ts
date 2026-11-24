/** Thời gian chờ: đọc Retry-After, đếm ngược theo mốc kết thúc, định dạng tiếng Việt. Không phụ thuộc React. */

/**
 * Retry-After (RFC 9110): số giây nguyên hoặc ngày giờ HTTP. Trả số giây nguyên (≥ 0) hoặc undefined
 * nếu thiếu/không hợp lệ.
 */
export function parseRetryAfter(value: string | null | undefined, nowMs: number = Date.now()): number | undefined {
  if (!value) return undefined
  const trimmed = value.trim()
  if (/^\d+$/.test(trimmed)) return Number.parseInt(trimmed, 10)
  // Chỉ nhận ngày HTTP (IMF-fixdate, ví dụ "Tue, 24 Nov 2026 10:00:30 GMT"): Date.parse quá dễ dãi,
  // "-5" bị hiểu thành năm -5.
  if (!/^[A-Za-z]{3}, /.test(trimmed)) return undefined
  const at = Date.parse(trimmed)
  if (Number.isNaN(at)) return undefined
  return Math.max(0, Math.ceil((at - nowMs) / 1000))
}

/** Giây còn lại tính từ MỐC KẾT THÚC (không trôi khi tab bị ẩn hay timer chạy chậm). */
export function secondsLeft(endMs: number, nowMs: number): number {
  return Math.max(0, Math.ceil((endMs - nowMs) / 1000))
}

/** "12 giây", "2 phút 5 giây", "1 giờ 3 phút". */
export function formatWait(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds))
  if (s < 60) return `${s} giây`
  if (s < 3600) {
    const minutes = Math.floor(s / 60)
    const rest = s % 60
    return rest ? `${minutes} phút ${rest} giây` : `${minutes} phút`
  }
  const hours = Math.floor(s / 3600)
  const minutes = Math.ceil((s % 3600) / 60)
  if (minutes === 60) return `${hours + 1} giờ`
  return minutes ? `${hours} giờ ${minutes} phút` : `${hours} giờ`
}

/** Dạng xấp xỉ cho thời gian dài (ví dụ hết lượt trong ngày): "khoảng 5 giờ 12 phút". */
export function formatWaitApprox(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds))
  if (s < 60) return `khoảng ${Math.max(1, s)} giây`
  if (s < 3600) return `khoảng ${Math.ceil(s / 60)} phút`
  return `khoảng ${formatWait(s)}`
}
