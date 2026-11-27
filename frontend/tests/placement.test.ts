// Logic trang kiểm tra đầu vào (src/lib/placement.ts).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { canApply, categoryLabel, countAnswered, inProgressId, latestCompletedId } from '../src/lib/placement.ts'

const attempt = (attempt_id: string, status: string, started_at: string, completed_at: string | null) =>
  ({ attempt_id, status, started_at, completed_at })

const SUMMARIES = [
  attempt('old', 'completed', '2026-11-20T08:00:00Z', '2026-11-20T08:10:00Z'),
  attempt('newest', 'completed', '2026-11-22T08:00:00Z', '2026-11-22T08:20:00Z'),
  attempt('middle', 'completed', '2026-11-21T08:00:00Z', '2026-11-21T08:15:00Z'),
  attempt('doing', 'in_progress', '2026-11-23T08:00:00Z', null),
]

test('latestCompletedId và inProgressId', () => {
  assert.equal(latestCompletedId(SUMMARIES), 'newest') // không phụ thuộc thứ tự danh sách
  assert.equal(latestCompletedId([...SUMMARIES].reverse()), 'newest')
  assert.equal(latestCompletedId([attempt('doing', 'in_progress', '2026-11-23T08:00:00Z', null)]), null)
  assert.equal(latestCompletedId([]), null)
  // Cùng completed_at → lượt bắt đầu sau thắng.
  const tie = [
    attempt('a', 'completed', '2026-11-20T08:00:00Z', '2026-11-20T09:00:00Z'),
    attempt('b', 'completed', '2026-11-20T08:30:00Z', '2026-11-20T09:00:00Z'),
  ]
  assert.equal(latestCompletedId(tie), 'b')
  assert.equal(inProgressId(SUMMARIES), 'doing')
  assert.equal(inProgressId(SUMMARIES.slice(0, 3)), null)
})

test('canApply, countAnswered, categoryLabel', () => {
  assert.equal(canApply('newest', SUMMARIES, null), true)
  assert.equal(canApply('newest', SUMMARIES, '2026-11-22T09:00:00Z'), false) // đã áp dụng
  assert.equal(canApply('old', SUMMARIES, null), false) // không phải lượt mới nhất

  assert.equal(countAnswered({ q1: 'a', q2: '', q3: 'c', other: 'x' }, ['q1', 'q2', 'q3', 'q4']), 2)
  assert.equal(countAnswered({}, ['q1']), 0)

  assert.equal(categoryLabel('grammar'), 'Ngữ pháp')
  assert.equal(categoryLabel('vocabulary'), 'Từ vựng')
  assert.equal(categoryLabel('listening'), 'listening')
})
