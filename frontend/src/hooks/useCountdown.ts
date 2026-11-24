import { useCallback, useEffect, useState } from 'react'
import { secondsLeft } from '../lib/time'

/**
 * Đếm ngược dùng chung (Retry-After). Tính theo MỐC KẾT THÚC chứ không trừ dần, nên không trôi khi
 * tab bị ẩn hay trình duyệt làm chậm timer; cập nhật lại ngay khi tab hiện lại. Timer tự dọn khi rời trang.
 */
export function useCountdown() {
  const [endMs, setEndMs] = useState<number | null>(null)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (endMs === null) return
    const tick = () => setNow(Date.now())
    tick()
    const timer = window.setInterval(tick, 1000)
    document.addEventListener('visibilitychange', tick)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', tick)
    }
  }, [endMs])

  const remaining = endMs === null ? 0 : secondsLeft(endMs, now)

  useEffect(() => {
    if (endMs !== null && remaining === 0) setEndMs(null)
  }, [endMs, remaining])

  /** Bắt đầu chờ `seconds` giây; không rút ngắn thời gian chờ đang có. */
  const start = useCallback((seconds: number) => {
    const end = Date.now() + Math.max(0, seconds) * 1000
    setNow(Date.now())
    setEndMs((current) => (current === null ? end : Math.max(current, end)))
  }, [])

  const reset = useCallback(() => setEndMs(null), [])

  return { remaining, start, reset }
}
