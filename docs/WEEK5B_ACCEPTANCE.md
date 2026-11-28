# Nghiệm thu Tuần 5 (Phần A + Phần B)

Ngày lập: 2026-11-28. Phần A: `docs/WEEK5A_ACCEPTANCE.md`. Số đo: `experiments/README.md` (mục 4–5). Nhật ký: `docs/ENVIRONMENT_CHECK.md` (mục "Tuần 5B").

Ý nghĩa trạng thái:
- **ĐẠT**: Claude đã chạy và có bằng chứng.
- **CHƯA ĐẠT**: đã kiểm và không đạt.
- **CHƯA KIỂM CHỨNG**: chưa có bằng chứng.

## Tóm tắt

**9/9 tiêu chí ĐẠT** về mặt kỹ thuật. Có 3 điểm cần lưu ý:
1. Hai cải tiến B1 **không được bật**, vì không thỏa quy tắc đã ghi trước. Đây là kết quả đúng quy trình, không phải tiêu chí chưa đạt.
2. Nội dung do AI soạn **chưa được người duyệt**: 119 bài tập, taxonomy, nhãn `grading_v1`, 79 truy vấn v2.
3. Thao tác trên trình duyệt (4 trang Streamlit mới) **CHƯA KIỂM CHỨNG**.

| # | Tiêu chí | Trạng thái | Bằng chứng |
| --- | --- | --- | --- |
| 1 | Quy tắc quyết định B1 ghi trước; ablation + AUC có số thật và khoảng tin cậy; cải tiến chỉ bật khi thỏa quy tắc; mọi lần thử đều được ghi | **ĐẠT** | Quy tắc ghi ở `experiments/README.md` mục 4 trước khi chạy. `b1_dev_20261128T154030Z.json`: rewrite cải thiện có ý nghĩa (ví dụ hybrid ΔMRR +0,158 [0,083; 0,233]) nhưng p95 tăng khoảng 2,4 s > 2 s → **không bật**. AUC điểm dense hạng 1 = 0,745; ngưỡng chọn bằng CV từ chối nhầm 51% → **không bật**. Hai lần chạy, kể cả lần đo độ trễ sai, đều có trong `retrieval_runs.jsonl` |
| 2 | Taxonomy hợp lệ, có tham chiếu chủ đề, trạng thái duyệt trung thực | **ĐẠT** | `languages/en.yaml`: 19 loại, gắn đủ 33/33 bài học; `validate_taxonomy_grading.py` đạt; `docs/ERROR_TAXONOMY.md` ghi **CHƯA DUYỆT**; mã ngoài danh mục → `other` (có test, có lần làm hỏng code) |
| 3 | Bank ≥ 100 bài validated, đủ 5 dạng, mọi bài đều qua bộ kiểm tra; bài bị loại được lưu kèm lý do | **ĐẠT** | **119 validated** / 160; đủ 5 dạng (mcq 31, cloze 21, sửa lỗi 24, sắp xếp câu 10, dịch 33); 33/33 bài học có ≥ 3 bài; 41 bài rejected lưu `reject_reasons`; kiểm tra độc lập khớp 89,6% |
| 4 | Chấm: bộ quy tắc chính xác tuyệt đối trên test tất định; LLM grader có schema chặt, chống injection, lỗi LLM không làm mất bài làm | **ĐẠT** | `test_taxonomy_grading.py`: 48/48 nhãn khớp. Kết quả LLM: verdict, điểm bị kẹp theo verdict, loại lỗi lạ → `other`, JSON hỏng bị từ chối (test). Injection: khối phân cách + cắt độ dài (test + lần làm hỏng code); thật: 2/2. Lỗi LLM → `pending` + `details.attempt_id`, regrade idempotent (test) |
| 5 | Không lộ answer_key trước khi nộp; owner check đúng; giới hạn tần suất hoạt động | **ĐẠT** | Test quét đệ quy mọi phản hồi GET/next (không có answer_key, accepted, reference, explanation…); bài rejected → 404; regrade bài của người khác → 404; nộp lần thứ 3 khi giới hạn 2/phút → 429. Làm hỏng có chủ đích (lộ đáp án, bỏ owner check) → test đỏ |
| 6 | `error_events` ghi đúng; tổng hợp + gợi ý bài tiếp theo có test | **ĐẠT** | Test API: lượt sai ghi đúng loại lỗi, bài học và attempt_id; LLM trả loại lạ → `other`. `summarize` và `choose_next` có test (ưu tiên, tránh lặp, tất định theo seed) |
| 7 | Streamlit có đủ 4 trang mới; chế độ công khai vẫn an toàn | **ĐẠT** (trình duyệt **CHƯA KIỂM CHỨNG**) | Thêm các trang 8 Bài tập, 9 Lỗi của tôi, 10 Duyệt bài tập, 11 Chất lượng bài tập. `AppTest`: không sập khi backend tắt; trang duyệt ẩn khi chưa có mã truy cập. Chế độ công khai + Gemini → chỉ dạng chấm bằng quy tắc (test) |
| 8 | Có số đo chất lượng bài tập và bộ chấm (kèm cảnh báo mẫu nhỏ, nhãn chưa duyệt) | **ĐẠT** | `experiments/README.md` mục 5. Bộ chấm: chính xác hai mức 0,974 [0,92; 1,00]; chấp nhận nhầm 0/26; từ chối nhầm 1/12; 3 mức 0,737. Ghi rõ: mẫu nhỏ, nhãn do Claude soạn, chưa duyệt bởi người. `docs/EXERCISE_REVIEW.md`: 40 bài chờ người duyệt |
| 9 | Test mặc định không cần mạng/key; không secret trong mã/log/Git; ngân sách Gemini không vượt mức | **ĐẠT** | `pytest` (không mạng, không key): **517 passed, 7 skipped** (đều là smoke). Quét secret sạch. Gemini: **119/250** lời gọi (bảng dưới) |

## Số lời gọi Gemini thật (Tuần 5B)

| Việc | Ngân sách | Thực tế | Ghi chú |
| --- | --- | --- | --- |
| Viết lại truy vấn | ≤ 20 | 16 | 2 lần × 8 (lần 1 có độ trễ đo sai → xóa cache, chạy lại) |
| Sinh bài tập | ≤ 90 | 42 | 33 vòng 1 (1 lời gọi lỗi schema, đã gọi lại) + 7 vòng bù (1 lỗi) + 1 bài 017 |
| Kiểm tra độc lập | ≤ 40 | 21 | Gộp 5 bài/lời gọi |
| Đánh giá bộ chấm | ≤ 40 | 38 | |
| Smoke | ≤ 10 | 2 | `RUN_EXERCISE_SMOKE=1` |
| **Tổng** | **≤ 250** | **119** | Theo `data/cache/llm/ledger.jsonl` (117) + 2 smoke test |

## Người dùng cần làm
1. Duyệt `docs/EXERCISE_REVIEW.md` (40 bài), `docs/ERROR_TAXONOMY.md`, nhãn `data/evaluation/grading_v1.json`.
2. Viết ≥ 30 truy vấn của riêng bạn trong `docs/EVAL_REVIEW_V2.md`.
3. Thử 4 trang Streamlit mới trên trình duyệt.
