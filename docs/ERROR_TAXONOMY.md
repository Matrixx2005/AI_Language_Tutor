# Danh mục lỗi (error taxonomy) — tiếng Anh cho người Việt A1–B1 (Tuần 5B)

Nguồn dữ liệu: `languages/en.yaml` → `error_taxonomy` (file YAML là nguồn chuẩn; bảng này sinh từ đó). Trạng thái: **CHƯA DUYỆT**.
Claude soạn dựa trên các lỗi phổ biến của người Việt; **Claude không tự ghi "đã duyệt"**. Mã `other` là mã dự phòng: mọi mã lỗi do LLM
trả về mà không thuộc danh mục sẽ được chuyển thành `other` (`LanguageConfig.normalize_error_type`, có test).

Kiểm tra tự động (`python scripts/validate_taxonomy_grading.py`): id duy nhất, có `other`, 15–25 loại, mọi `topics` là document_id có trong corpus.

| # | id | Tên | Mô tả | Bài học liên quan | Ví dụ sai → đúng | Duyệt (người duyệt, ngày) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `article` | Mạo từ a/an/the thiếu hoặc thừa | Bỏ mạo từ trước danh từ đếm được số ít, chọn sai a/an, dùng the không cần thiết. | gram-en-a1-articles-003 | She is teacher. → She is a teacher. | CHƯA DUYỆT |
| 2 | `plural_countable` | Số nhiều và danh từ không đếm được | Quên -s/-es số nhiều, thêm -s cho danh từ không đếm được, dùng sai much/many. | gram-en-a1-plurals-004, gram-en-a2-count-noncount-008 | I have two book. → I have two books. | CHƯA DUYỆT |
| 3 | `subject_verb_agreement` | Hòa hợp chủ ngữ – động từ | Quên -s/-es ở ngôi thứ ba số ít, chia be sai với chủ ngữ. | gram-en-a1-present-simple-002, gram-en-a1-be-001 | He work in a bank. → He works in a bank. | CHƯA DUYỆT |
| 4 | `tense_form` | Thì và dạng động từ | Chọn sai thì, dùng sai dạng quá khứ/quá khứ phân từ, sai V-ing. | gram-en-a2-past-simple-006, gram-en-a2-present-continuous-007, gram-en-a2-present-perfect-011, gram-en-b1-present-perfect-past-012, gram-en-a2-past-continuous-023, gram-en-b1-past-perfect-031 | I have seen him yesterday. → I saw him yesterday. | CHƯA DUYỆT |
| 5 | `missing_be_auxiliary` | Thiếu động từ be / trợ động từ | Bỏ be trước tính từ hoặc V-ing, thiếu do/does/did trong câu hỏi và phủ định. | gram-en-a1-be-001, gram-en-a1-present-simple-002 | She very happy. → She is very happy. | CHƯA DUYỆT |
| 6 | `preposition` | Giới từ | Chọn sai in/on/at cho thời gian, nơi chốn; thêm hoặc thiếu giới từ. | gram-en-a1-prepositions-time-016, gram-en-a1-prepositions-place-017 | I was born on 2005. → I was born in 2005. | CHƯA DUYỆT |
| 7 | `word_order` | Trật tự từ | Sai vị trí trạng từ, tính từ, chủ ngữ – trợ động từ trong câu hỏi. | gram-en-a1-frequency-adverbs-021, gram-en-a2-adverbs-manner-026 | I go always to school by bus. → I always go to school by bus. | CHƯA DUYỆT |
| 8 | `comparison` | So sánh hơn / so sánh nhất | Dùng cả more và -er, quên than/the, dạng bất quy tắc sai. | gram-en-a2-comparatives-009, gram-en-a2-superlatives-022 | She is more taller than me. → She is taller than me. | CHƯA DUYỆT |
| 9 | `pronoun_possessive` | Đại từ và sở hữu | Nhầm he/she/his/her, dùng sai 's, nhầm this/these. | gram-en-a1-possessives-018, gram-en-a1-demonstratives-020 | My mother loves his job. → My mother loves her job. | CHƯA DUYỆT |
| 10 | `modal_verb` | Động từ khuyết thiếu | Thêm to hoặc -s sau can/must/should, dùng sai must/have to. | gram-en-b1-modals-013, gram-en-a1-can-ability-019 | She can to swim. → She can swim. | CHƯA DUYỆT |
| 11 | `conditional` | Câu điều kiện | Dùng will trong mệnh đề if, chia sai thì trong câu điều kiện loại 0/1/2. | gram-en-b1-first-conditional-014, gram-en-b1-second-conditional-027, gram-en-b1-zero-conditional-033 | If it will rain, we stay home. → If it rains, we will stay home. | CHƯA DUYỆT |
| 12 | `passive` | Câu bị động | Thiếu be, dùng sai quá khứ phân từ trong câu bị động. | gram-en-b1-passive-voice-028 | The house was build in 1990. → The house was built in 1990. | CHƯA DUYỆT |
| 13 | `verb_pattern` | Dạng động từ theo sau (V-ing / to V) | Chọn sai V-ing hay to V sau một động từ hoặc giới từ. | gram-en-a2-verb-patterns-025 | I enjoy to read. → I enjoy reading. | CHƯA DUYỆT |
| 14 | `linking_clause` | Từ nối, mệnh đề quan hệ, câu tường thuật | Dùng sai who/which/that, thiếu từ nối, sai lùi thì khi tường thuật. | gram-en-b1-relative-clauses-015, gram-en-b1-reported-speech-029 | The man which lives here is my uncle. → The man who lives here is my uncle. | CHƯA DUYỆT |
| 15 | `quantity_degree` | Lượng từ và mức độ (too/enough, there is/are) | Sai vị trí too/enough, chia sai there is/there are. | gram-en-b1-too-enough-032, gram-en-a1-there-be-005 | He is enough old to drive. → He is old enough to drive. | CHƯA DUYỆT |
| 16 | `future_form` | Cách diễn đạt tương lai | Nhầm will / be going to, thêm to sau will. | gram-en-a2-will-future-024, gram-en-a2-going-to-010, gram-en-b1-used-to-030 | I will to call you. → I will call you. | CHƯA DUYỆT |
| 17 | `spelling_capitalization` | Chính tả và viết hoa | Sai chính tả, quên viết hoa đầu câu, tên riêng, I. | — | i live in hanoi. → I live in Hanoi. | CHƯA DUYỆT |
| 18 | `word_choice_literal` | Chọn từ / dịch từng chữ từ tiếng Việt | Dịch sát từng chữ tiếng Việt, collocation sai (ví dụ "open the light"). | — | Please open the light. → Please turn on the light. | CHƯA DUYỆT |
| 19 | `other` | Lỗi khác | Lỗi không thuộc các loại trên (mã dự phòng khi LLM trả loại lạ). | — | - → - | CHƯA DUYỆT |

Người duyệt: ____________ · Ngày: ____________
