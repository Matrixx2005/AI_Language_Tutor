// Ánh xạ mã lỗi máy chủ (src/lib/apiErrors.ts).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { LIMIT_CODES, LLM_CODES, canRetry, isLimitCode, isLlmCode, messageForCode } from '../src/lib/apiErrors.ts'

test('phân nhóm mã: giới hạn ứng dụng và lỗi gia sư AI tách biệt', () => {
  for (const code of LIMIT_CODES) { assert.ok(isLimitCode(code), code); assert.ok(!isLlmCode(code), code) }
  for (const code of LLM_CODES) { assert.ok(isLlmCode(code), code); assert.ok(!isLimitCode(code), code) }
  assert.ok(!isLimitCode('internal_error'))
  assert.ok(!isLlmCode('internal_error'))
  assert.ok(!isLimitCode('placement_superseded'))
})

test('canRetry: chỉ chặn lỗi mà gửi lại y nguyên vô ích', () => {
  for (const code of ['llm_content_blocked', 'llm_not_configured', 'message_too_long', 'validation_error']) {
    assert.equal(canRetry(code), false, code)
  }
  for (const code of ['llm_timeout', 'llm_provider_error', 'llm_rate_limited', 'chat_rate_limited', 'internal_error', 'network_error', 'unknown']) {
    assert.equal(canRetry(code), true, code)
  }
})

test('messageForCode: ưu tiên bản dịch, rồi thông điệp máy chủ, rồi câu chung', () => {
  assert.equal(messageForCode('chat_rate_limited', 'Too many'), 'Bạn đang gửi tin hơi nhanh.')
  assert.equal(messageForCode('chat_daily_limit_reached'), 'Bạn đã dùng hết lượt hỏi gia sư AI hôm nay.')
  assert.equal(messageForCode('message_too_long', 'Tin nhắn dài tối đa 2000 ký tự.'), 'Tin nhắn dài tối đa 2000 ký tự.')
  assert.equal(messageForCode(null), 'Yêu cầu chưa thành công. Vui lòng thử lại.')
  assert.equal(messageForCode('ma_la'), 'Yêu cầu chưa thành công. Vui lòng thử lại.')
  // Mọi mã giới hạn và mã gia sư AI đều có bản dịch tiếng Việt.
  for (const code of [...LIMIT_CODES, ...LLM_CODES]) assert.notEqual(messageForCode(code, 'SERVER'), 'SERVER', code)
})
