// Định dạng câu trả lời không dùng HTML (src/lib/richText.ts).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseInline, parseRichText } from '../src/lib/richText.ts'

const plain = (blocks: ReturnType<typeof parseRichText>) => JSON.stringify(blocks).includes('*')

test('bỏ dấu *: đậm thành bold, nghiêng và dấu lẻ bị xóa', () => {
  assert.deepEqual(parseInline('Dùng **an** trước *nguyên âm* [1].'), [
    { text: 'Dùng ', bold: false }, { text: 'an', bold: true }, { text: ' trước nguyên âm [1].', bold: false },
  ])
  assert.deepEqual(parseInline('5 * 3 và `code` *'), [{ text: '5  3 và code ', bold: false }])
  assert.equal(plain(parseRichText('**Quy tắc:** dùng *an*.\n* ví dụ **một**\n# Tiêu đề')), false)
})

test('danh sách, đoạn và tiêu đề', () => {
  const blocks = parseRichText('Mở đầu\ndòng hai\n\n- a\n* b\n• c\n1. x\n2) y\n## Kết')
  assert.deepEqual(blocks.map((b) => b.kind), ['paragraph', 'list', 'list', 'paragraph'])
  assert.equal(blocks[0].kind === 'paragraph' && blocks[0].lines.length, 2)
  assert.equal(blocks[1].kind === 'list' && blocks[1].items.length, 3)
  assert.equal(blocks[2].kind === 'list' && blocks[2].ordered, true)
  assert.deepEqual(blocks[3].kind === 'paragraph' && blocks[3].lines[0], [{ text: 'Kết', bold: true }])
})

test('nhãn đầu dòng ngắn được in đậm, câu thường thì không', () => {
  assert.deepEqual(parseInline('Lỗi thường gặp: She are → She is'), [
    { text: 'Lỗi thường gặp:', bold: true }, { text: ' She are → She is', bold: false },
  ])
  assert.deepEqual(parseInline('Tự kiểm tra:'), [{ text: 'Tự kiểm tra:', bold: true }])
  // Câu dài có dấu hai chấm không bị coi là nhãn.
  assert.equal(parseInline('Ta dùng thì này khi nói về kinh nghiệm: I have been.')[0].bold, false)
})

test('nội dung giống HTML vẫn chỉ là chữ (React escape khi hiển thị)', () => {
  assert.deepEqual(parseInline('<img src=x onerror=alert(1)>'), [{ text: '<img src=x onerror=alert(1)>', bold: false }])
  assert.deepEqual(parseRichText(''), [])
})
