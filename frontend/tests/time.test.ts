// Logic thời gian chờ (src/lib/time.ts). Chạy: npm test (Node 24 chạy trực tiếp .ts, không thêm thư viện).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { formatWait, formatWaitApprox, parseRetryAfter, secondsLeft } from '../src/lib/time.ts'

const NOW = Date.parse('2026-11-24T10:00:00Z')

test('parseRetryAfter: số giây nguyên', () => {
  assert.equal(parseRetryAfter('60', NOW), 60)
  assert.equal(parseRetryAfter(' 900 ', NOW), 900)
  assert.equal(parseRetryAfter('0', NOW), 0)
})

test('parseRetryAfter: ngày HTTP, giá trị thiếu hoặc không hợp lệ', () => {
  assert.equal(parseRetryAfter('Tue, 24 Nov 2026 10:00:30 GMT', NOW), 30)
  assert.equal(parseRetryAfter('Tue, 24 Nov 2026 09:59:00 GMT', NOW), 0) // đã qua → 0, không âm
  assert.equal(parseRetryAfter(null, NOW), undefined)
  assert.equal(parseRetryAfter('', NOW), undefined)
  assert.equal(parseRetryAfter('-5', NOW), undefined) // lỗi thật đã gặp: Date.parse hiểu là năm -5
  assert.equal(parseRetryAfter('1.5', NOW), undefined)
  assert.equal(parseRetryAfter('abc', NOW), undefined)
  assert.equal(parseRetryAfter('Xyz, 99 Foo 2026 GMT', NOW), undefined)
})

test('secondsLeft: làm tròn lên, không âm', () => {
  assert.equal(secondsLeft(NOW + 1500, NOW), 2)
  assert.equal(secondsLeft(NOW + 1000, NOW), 1)
  assert.equal(secondsLeft(NOW, NOW), 0)
  assert.equal(secondsLeft(NOW - 5000, NOW), 0)
})

test('formatWait: giây / phút / giờ', () => {
  assert.equal(formatWait(0), '0 giây')
  assert.equal(formatWait(12), '12 giây')
  assert.equal(formatWait(59.2), '1 phút')
  assert.equal(formatWait(60), '1 phút')
  assert.equal(formatWait(125), '2 phút 5 giây')
  assert.equal(formatWait(900), '15 phút')
  assert.equal(formatWait(3600), '1 giờ')
  assert.equal(formatWait(3780), '1 giờ 3 phút')
  assert.equal(formatWait(7199), '2 giờ') // 1 giờ 59 phút 59 giây → phút làm tròn lên 60 → 2 giờ
  assert.equal(formatWait(-3), '0 giây')
})

test('formatWaitApprox: dạng "khoảng …" cho giới hạn ngày', () => {
  assert.equal(formatWaitApprox(0), 'khoảng 1 giây')
  assert.equal(formatWaitApprox(45), 'khoảng 45 giây')
  assert.equal(formatWaitApprox(61), 'khoảng 2 phút')
  assert.equal(formatWaitApprox(5 * 3600 + 12 * 60), 'khoảng 5 giờ 12 phút')
})
