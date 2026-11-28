# Duyệt corpus bài ngữ pháp (Tuần 4)

Corpus: `data/processed/grammar_lessons_v1.json`, gồm **33 bài**:
- 11 bài A1, 11 bài A2, 11 bài B1;
- 15 bài cũ từ Tuần 1, **không đổi id hay nội dung**;
- 18 bài mới soạn nháp ở Tuần 4.

Tất cả nội dung là bản nháp gốc (*Original content drafted for AI Language Tutor; pending human review*), license CC BY 4.0, phiên bản `v1.0-draft` hoặc `v1.1-draft`.

**Claude không được và không tự ghi "đã duyệt".** Cột trạng thái chỉ đổi khi người duyệt xác nhận.

**Kết quả duyệt (2026-11-28):** người quản lý dự án duyệt **đạt cả 18 bài mới** và chọn chính tả **Anh–Mỹ** cho toàn bộ corpus. Đã sửa 4 bài:
- 016: `at the weekend (British English)` → `on the weekend`; `on 5 May` → `on May 5`;
- 020: `neighbours` → `neighbors`;
- 025: `practise` → `practice`;
- 027: `apologise` → `apologize`.

15 bài cũ không có chính tả Anh–Anh nên không đổi. Trường `source` của 18 bài ghi người duyệt và ngày; phiên bản `v1.0`, riêng 4 bài đã sửa là `v1.1`.

## Rà soát tự động (lớp phụ, KHÔNG thay thế duyệt người)

`python scripts/validate_dataset.py` kiểm tra:
- đủ trường bắt buộc, trình độ hợp lệ;
- `document_id` không trùng và theo quy ước `gram-<lang>-<level>-<slug>-<NNN>`, khớp `language_code` và `level` của bài;
- nội dung không quá 160 từ (bài mới dài nhất 118 từ);
- không trùng nội dung, kể cả sau khi chuẩn hóa;
- không gần trùng: tập từ của hai bài trùng nhau ≥ 60% (Jaccard) thì báo lỗi.

Kết quả: **33 bài, 0 lỗi**. Ba cặp bài giống nhau nhất (Jaccard tập từ): `gram-en-a2-present-perfect-011` – `gram-en-b1-present-perfect-past-012`: 0.36; `gram-en-b1-first-conditional-014` – `gram-en-b1-second-conditional-027`: 0.35; `gram-en-a1-be-001` – `gram-en-a2-going-to-010`: 0.33. Cả ba cặp đều dưới ngưỡng 0,6.

Validator **không** kiểm tra ngữ pháp, độ đúng của ví dụ hay mức độ phù hợp trình độ; những việc đó cần người duyệt.

Từ khóa tiếng Việt cho từng bài nằm trong `data/processed/keywords_vi_v1.json`, trạng thái CHƯA DUYỆT, mặc định không dùng (xem `experiments/README.md`).

## Việc người duyệt cần làm với mỗi bài mới

1. Quy tắc đúng với cách dùng chuẩn.
2. Mọi câu ví dụ đúng ngữ pháp và tự nhiên.
3. Mục "lỗi thường gặp" đúng với lỗi của người Việt.
4. Bài phù hợp với trình độ đã gán.

Sau khi kiểm, ghi tên người duyệt và ngày vào cột trạng thái.

| # | document_id | Chủ đề | Cấp | Số từ | Nguồn gốc | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `gram-en-a1-be-001` | verb be | A1 | 92 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 2 | `gram-en-a1-present-simple-002` | present simple | A1 | 92 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 3 | `gram-en-a1-articles-003` | articles | A1 | 97 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 4 | `gram-en-a1-plurals-004` | plural nouns | A1 | 101 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 5 | `gram-en-a1-there-be-005` | there is and there are | A1 | 93 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 6 | `gram-en-a2-past-simple-006` | past simple | A2 | 87 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 7 | `gram-en-a2-present-continuous-007` | present continuous | A2 | 98 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 8 | `gram-en-a2-count-noncount-008` | countable and uncountable nouns | A2 | 109 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 9 | `gram-en-a2-comparatives-009` | comparative adjectives | A2 | 91 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 10 | `gram-en-a2-going-to-010` | future plans | A2 | 112 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 11 | `gram-en-a2-present-perfect-011` | present perfect | A2 | 105 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 12 | `gram-en-b1-present-perfect-past-012` | present perfect versus past simple | B1 | 105 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 13 | `gram-en-b1-modals-013` | modal verbs | B1 | 102 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 14 | `gram-en-b1-first-conditional-014` | first conditional | B1 | 117 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 15 | `gram-en-b1-relative-clauses-015` | relative clauses | B1 | 128 | cũ | Có từ Tuần 1 (license CC BY 4.0 đã chốt 2026-11-18; nội dung do Claude rà soát, chưa có giáo viên duyệt) |
| 16 | `gram-en-a1-prepositions-time-016` | prepositions of time | A1 | 98 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28; đã sửa chính tả sang Anh–Mỹ (v1.1) |
| 17 | `gram-en-a1-prepositions-place-017` | prepositions of place | A1 | 106 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 18 | `gram-en-a1-possessives-018` | possessives | A1 | 91 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 19 | `gram-en-a1-can-ability-019` | can for ability | A1 | 90 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 20 | `gram-en-a1-demonstratives-020` | demonstratives | A1 | 77 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28; đã sửa chính tả sang Anh–Mỹ (v1.1) |
| 21 | `gram-en-a1-frequency-adverbs-021` | adverbs of frequency | A1 | 92 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 22 | `gram-en-a2-superlatives-022` | superlative adjectives | A2 | 96 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 23 | `gram-en-a2-past-continuous-023` | past continuous | A2 | 103 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 24 | `gram-en-a2-will-future-024` | future with will | A2 | 99 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 25 | `gram-en-a2-verb-patterns-025` | gerunds and infinitives | A2 | 94 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28; đã sửa chính tả sang Anh–Mỹ (v1.1) |
| 26 | `gram-en-a2-adverbs-manner-026` | adverbs of manner | A2 | 98 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 27 | `gram-en-b1-second-conditional-027` | second conditional | B1 | 118 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28; đã sửa chính tả sang Anh–Mỹ (v1.1) |
| 28 | `gram-en-b1-passive-voice-028` | passive voice | B1 | 100 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 29 | `gram-en-b1-reported-speech-029` | reported speech | B1 | 113 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 30 | `gram-en-b1-used-to-030` | used to | B1 | 104 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 31 | `gram-en-b1-past-perfect-031` | past perfect | B1 | 113 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 32 | `gram-en-b1-too-enough-032` | too and enough | B1 | 106 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
| 33 | `gram-en-b1-zero-conditional-033` | zero conditional | B1 | 91 | mới (Tuần 4) | Đã duyệt — người quản lý dự án — 2026-11-28 (v1.0) |
