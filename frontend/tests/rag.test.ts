// Logic RAG trên giao diện (src/lib/rag.ts).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { hasNoValidCitation, orderSources, ragModeLabel, resolveMode, showNoSourceNotice } from '../src/lib/rag.ts'

const src = (n: number, cited: boolean) => ({ n, document_id: `d${n}`, title: `Bài ${n}`, level: 'A1', rank: n, score: 1, text: 't', cited })

test('resolveMode: lựa chọn của người dùng thắng, bỏ trống thì theo máy chủ', () => {
  assert.equal(resolveMode('hybrid', 'llm_only'), 'hybrid')
  assert.equal(resolveMode('', 'dense'), 'dense')
  assert.equal(resolveMode('', null), null)
})

test('showNoSourceNotice: chỉ ở llm_only, không hiện khi chưa biết chế độ', () => {
  assert.equal(showNoSourceNotice('llm_only'), true)
  assert.equal(showNoSourceNotice('dense'), false)
  assert.equal(showNoSourceNotice('hybrid'), false)
  assert.equal(showNoSourceNotice(null), false)
})

test('orderSources: nguồn được trích dẫn lên trước, giữ thứ tự [n], không đổi mảng gốc', () => {
  const sources = [src(1, false), src(2, true), src(3, false), src(4, true)]
  assert.deepEqual(orderSources(sources).map((s) => s.n), [2, 4, 1, 3])
  assert.deepEqual(sources.map((s) => s.n), [1, 2, 3, 4])
  assert.deepEqual(orderSources(null), [])
})

test('hasNoValidCitation và ragModeLabel', () => {
  assert.equal(hasNoValidCitation([src(1, false)]), true)
  assert.equal(hasNoValidCitation([src(1, true)]), false)
  assert.equal(hasNoValidCitation([]), false)
  assert.equal(hasNoValidCitation(null), false)
  assert.equal(ragModeLabel('hybrid'), 'Tài liệu — kết hợp (hybrid)')
  assert.equal(ragModeLabel(null), 'Mặc định của máy chủ')
  assert.equal(ragModeLabel('khac'), 'Mặc định của máy chủ')
})
