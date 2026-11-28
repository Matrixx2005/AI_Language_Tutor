/**
 * Định dạng nhẹ cho câu trả lời của gia sư, KHÔNG dùng HTML (React tự escape từng đoạn chữ).
 * Prompt đã yêu cầu văn bản thuần; hàm này là lớp thứ hai cho câu trả lời cũ hoặc khi model vẫn viết Markdown:
 *  - dòng bắt đầu bằng "- ", "* ", "• " hoặc "1. " → mục danh sách;
 *  - "**đậm**" / "__đậm__" → chữ đậm; "*nghiêng*" → chữ thường; dấu * và ` lẻ bị bỏ; "# Tiêu đề" → dòng đậm;
 *  - nhãn đầu dòng ngắn như "Quy tắc:" → đậm;
 *  - dòng trống tách đoạn.
 */
export interface Inline {
  text: string
  bold: boolean
}

export type Block = { kind: 'paragraph'; lines: Inline[][] } | { kind: 'list'; ordered: boolean; items: Inline[][] }

const BULLET = /^\s*(?:[-*•]\s+)/
const ORDERED = /^\s*\d{1,2}[.)]\s+/
const HEADING = /^\s*#{1,6}\s+/
// Nhãn đầu dòng: 1–4 từ rồi dấu hai chấm, ví dụ "Quy tắc:", "Lỗi thường gặp:", "Tự kiểm tra:".
const LABEL = /^((?:[^\s:*]+\s){0,3}[^\s:*]+):(\s|$)/

/** Bỏ dấu Markdown lẻ trong một đoạn chữ thường (sau khi đã tách phần đậm). */
function clean(text: string): string {
  return text.replace(/(^|[^\w])\*(?=\S)([^*\n]+?)\*(?=[^\w]|$)/g, '$1$2').replace(/[*`]/g, '')
}

export function parseInline(line: string): Inline[] {
  const out: Inline[] = []
  const push = (text: string, bold: boolean) => {
    const value = clean(text)
    if (!value) return
    const last = out[out.length - 1]
    if (last && last.bold === bold) last.text += value
    else out.push({ text: value, bold })
  }
  let rest = line
  const label = rest.match(LABEL)
  if (label && !/\*\*/.test(label[1])) {
    push(`${label[1]}:`, true)
    rest = rest.slice(label[1].length + 1)
  }
  const pattern = /\*\*(.+?)\*\*|__(.+?)__/g
  let index = 0
  for (const match of rest.matchAll(pattern)) {
    push(rest.slice(index, match.index), false)
    push(match[1] ?? match[2], true)
    index = (match.index ?? 0) + match[0].length
  }
  push(rest.slice(index), false)
  return out
}

export function parseRichText(text: string): Block[] {
  const blocks: Block[] = []
  let paragraph: Inline[][] = []
  const flush = () => {
    if (paragraph.length) blocks.push({ kind: 'paragraph', lines: paragraph })
    paragraph = []
  }
  for (const raw of text.replace(/\r\n?/g, '\n').split('\n')) {
    if (!raw.trim()) { flush(); continue }
    const bullet = BULLET.test(raw)
    const ordered = !bullet && ORDERED.test(raw)
    if (bullet || ordered) {
      flush()
      const item = parseInline(raw.replace(bullet ? BULLET : ORDERED, ''))
      const last = blocks[blocks.length - 1]
      if (last && last.kind === 'list' && last.ordered === ordered) last.items.push(item)
      else blocks.push({ kind: 'list', ordered, items: [item] })
      continue
    }
    if (HEADING.test(raw)) {
      paragraph.push([{ text: clean(raw.replace(HEADING, '')), bold: true }])
      continue
    }
    paragraph.push(parseInline(raw.trim()))
  }
  flush()
  return blocks
}
