// Logic trang chat (src/lib/chat.ts).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { charCount, collapseRetriedTurns, isForCurrentSession, pickSession, precedingUserContent } from '../src/lib/chat.ts'

const u = (content: string, id = content) => ({ message_id: `u-${id}`, role: 'user', content, status: 'ok' })
const ok = (content: string) => ({ message_id: `a-${content}`, role: 'assistant', content, status: 'ok' })
const err = (id: string) => ({ message_id: `e-${id}`, role: 'assistant', content: '', status: 'error' })

test('collapseRetriedTurns: ẩn lượt lỗi đã được thử lại, giữ lượt lỗi chưa thử lại', () => {
  const retried = [u('hi', '1'), err('1'), u('hi', '2'), ok('hello')]
  assert.deepEqual(collapseRetriedTurns(retried).map((m) => m.message_id), ['u-2', 'a-hello'])

  const notRetried = [u('hi'), err('1')]
  assert.deepEqual(collapseRetriedTurns(notRetried).map((m) => m.message_id), ['u-hi', 'e-1'])

  // Tin kế tiếp có nội dung khác → lượt lỗi không bị ẩn.
  const different = [u('a'), err('1'), u('b'), ok('x')]
  assert.equal(collapseRetriedTurns(different).length, 4)

  // Thử lại nhiều lần: chỉ còn lần cuối.
  const twice = [u('q', '1'), err('1'), u('q', '2'), err('2'), u('q', '3'), ok('done')]
  assert.deepEqual(collapseRetriedTurns(twice).map((m) => m.message_id), ['u-3', 'a-done'])

  // Lượt thành công trùng nội dung không bị ẩn.
  const okTwice = [u('q', '1'), ok('a1'), u('q', '2'), ok('a2')]
  assert.equal(collapseRetriedTurns(okTwice).length, 4)
  assert.deepEqual(collapseRetriedTurns([]), [])
})

test('precedingUserContent, pickSession, charCount', () => {
  const list = [u('first'), ok('r1'), u('second'), err('1')]
  assert.equal(precedingUserContent(list, 3), 'second')
  assert.equal(precedingUserContent(list, 1), 'first')
  assert.equal(precedingUserContent(list, 0), null)

  const sessions = [{ session_id: 'new' }, { session_id: 'old' }]
  assert.equal(pickSession(sessions, 'old'), 'old')
  assert.equal(pickSession(sessions, 'deleted'), 'new')
  assert.equal(pickSession(sessions, null), 'new')
  assert.equal(pickSession([], 'x'), null)

  assert.deepEqual(charCount(12, 2000), { label: '12/2000', over: false })
  assert.deepEqual(charCount(2000, 2000), { label: '2000/2000', over: false })
  assert.deepEqual(charCount(2001, 2000), { label: '2001/2000', over: true })
})

test('isForCurrentSession: chỉ áp dụng phản hồi/lịch sử khi phiên của yêu cầu vẫn đang được chọn', () => {
  assert.equal(isForCurrentSession('s1', 's1'), true)
  assert.equal(isForCurrentSession('s1', 's2'), false) // đã chuyển phiên trong lúc chờ
  assert.equal(isForCurrentSession('s1', null), false)
  assert.equal(isForCurrentSession(null, null), false) // yêu cầu không gắn phiên nào
  assert.equal(isForCurrentSession(null, 's1'), false)
})
