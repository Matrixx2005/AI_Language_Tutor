# Duyệt dữ liệu Tuần 1

Ngày: 2026-11-18

## Quyết định của người quản lý dự án

| Mục | Quyết định |
| --- | --- |
| ERD logic (`docs/DATABASE_DESIGN.md`) | Đã duyệt. Migration vẫn chờ chốt các quyết định mở trong tài liệu đó. |
| License 15 bài ngữ pháp | Chốt **CC BY 4.0**. Trường `license` của cả 15 bài ghi: `CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); approved by project maintainer 2026-11-18.` |
| Duyệt chất lượng bộ đánh giá | Người dùng giao cho Claude rà soát và sửa; kết quả ở dưới. |

## Phương pháp rà soát

Rà soát bởi Claude theo yêu cầu người dùng; **không phải** đánh giá của giáo viên bản ngữ, và chưa thử trên người học thật.

- Placement: đáp án đúng duy nhất, distractor sai rõ ràng, nhãn cấp độ khớp với bài học cùng cấp, phân bố vị trí đáp án.
- Truy vấn RAG: câu trả lời có trong tài liệu được gán, mỗi truy vấn chỉ có một tài liệu liên quan rõ ràng, không có hai truy vấn hỏi cùng một ý (đặc biệt giữa dev và test), phân bố truy vấn theo tài liệu.
- Bài ngữ pháp: độ chính xác của quy tắc (vì là tài liệu truy xuất cho RAG).

## Vấn đề phát hiện và cách sửa

### Placement (`data/evaluation/placement_v1.json`)

| Vấn đề | Mức độ | Sửa |
| --- | --- | --- |
| 20/30 câu có đáp án đúng ở lựa chọn đầu tiên, không câu nào ở lựa chọn thứ tư. Chọn toàn đáp án đầu đạt 67%, gần ngưỡng B1 (70%). | Nghiêm trọng | Xếp lại vị trí đáp án bằng seed cố định `20261118`: 8/7/7/8. Validator thêm kiểm tra tối đa 10/30 đáp án cùng vị trí, có test. |
| `place-en-b1-grammar-021` ("Have you ever ___ to Singapore?") là present perfect chỉ kinh nghiệm, thuộc bài A2 (`gram-en-a2-present-perfect-011`) nhưng gán B1. | Trung bình | Thay bằng câu B1 về for/since: "She has worked at this company ___ 2024." → `since`. |
| `place-en-b1-vocabulary-028`: distractor "Because" tạo câu vẫn đúng ngữ pháp ("Because it was cold, we walked…"). | Nhẹ | Thay bằng "Despite" (lỗi phổ biến, sai ngữ pháp trước mệnh đề). |

Các câu còn lại: đáp án đúng và duy nhất, giải thích khớp. Placement giữ 10 A1 / 10 A2 / 10 B1, 15 ngữ pháp / 15 từ vựng; không có nhãn dev/test (Prompt Tuần 1 chỉ yêu cầu dev/test cho truy vấn RAG).

### Truy vấn RAG (`data/evaluation/rag_queries_v1.json`)

Bài `gram-en-b1-present-perfect-past-012` có 5/30 truy vấn, trong đó 3 truy vấn cùng hỏi "thời điểm đã kết thúc → past simple" (017 dev, 023 dev, 027 test) và 2 truy vấn test cùng hỏi for/since (012, 018). Nhiều cặp dev–test trùng ý, khiến tối ưu trên dev rò rỉ sang test.

Đã viết lại 10 truy vấn; **giữ nguyên** ID, split, ngôn ngữ, loại truy vấn và tỷ lệ 20 dev / 10 test đã khóa:

| ID | Split | Trước (trùng với) | Sau (tài liệu → ý hỏi) |
| --- | --- | --- | --- |
| rag-q-010 | dev | 020 (going to cho kế hoạch) | going-to-010 → dự đoán dựa trên dấu hiệu |
| rag-q-013 | dev | 024 test (mustn't) | modals-013 → have to theo chủ ngữ/quá khứ |
| rag-q-017 | dev | 027 test (yesterday → past simple) | present-simple-002 → đuôi -s/-es với he/she/it |
| rag-q-018 | test | 012 test (for/since) | be-001 → vị trí be trong câu hỏi, không dùng do/does |
| rag-q-019 | dev | 009, 030 test (-er / more) | articles-003 → dùng the khi nhắc lại |
| rag-q-022 | dev | 005 (there is/are trước danh từ) | there-be-005 → cách đặt câu hỏi |
| rag-q-023 | dev | 027 test (tối qua → past simple) | past-simple-006 → go/went (bất quy tắc) |
| rag-q-025 | dev | 007 (be + V-ing) | present-continuous-007 → động từ trạng thái |
| rag-q-028 | dev | 015 test (mẫu câu điều kiện loại 1) | first-conditional-014 → không dùng will sau if |
| rag-q-029 | dev | 008 (how much sugar) | count-noncount-008 → a bottle of |

Sau sửa: 13 bài có 2 truy vấn, `modals-013` có 3, `present-perfect-011` có 1. Việc sửa được ghi trong `split_manifest.json` (`revisions`) và thực hiện **trước khi chạy bất kỳ thí nghiệm nào**.

### Bài ngữ pháp (`data/processed/grammar_lessons_v1.json`)

| Bài | Vấn đề | Sửa |
| --- | --- | --- |
| `gram-en-a1-plurals-004` | "For many nouns ending in z, double the z" — sai: phần lớn chỉ thêm -es (buzz/buzzes). | Sửa quy tắc; `version` → `v1.1-draft`. |
| `gram-en-b1-relative-clauses-015` | Mục "Common mistake" thiếu câu đúng, khó hiểu. | Thêm câu "Correct:"; `version` → `v1.1-draft`. |

## Bản gốc

Bản trước khi sửa được lưu nguyên trạng (kèm SHA-256) tại `data/archive/pre-review-2026-11-18/`.

## Hạn chế còn lại

- Độ khó và nhãn cấp độ chưa được hiệu chuẩn trên người học; ngưỡng 40%/70% trong `languages/en.yaml` vẫn là tạm thời.
- Mỗi tài liệu chỉ có 1–3 truy vấn; với 10 truy vấn test, chênh lệch 1 truy vấn = 10 điểm Recall. Kết quả thí nghiệm cần báo cáo kèm cỡ mẫu.
- Nội dung bài vẫn ở mức `draft`; nên có người dạy tiếng Anh đọc lại trước khi phát hành.

## Kiểm chứng

- `.venv\Scripts\pytest.exe -q` → `9 passed`
- `scripts/validate_dataset.py` → `15 records, 0 errors`
- `scripts/validate_evaluation.py` → `30 placement questions, 30 RAG queries, 20 dev / 10 test`
- Validator mới chạy trên bản placement cũ báo đúng lỗi: `correct answers are concentrated in one option position (20/30)`.
