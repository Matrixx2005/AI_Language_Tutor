# Nghiệm thu Tuần 4 — RAG

Ngày lập: 2026-11-28. Nhật ký chi tiết: `docs/ENVIRONMENT_CHECK.md`, mục "Tuần 4". Số đo: `experiments/README.md`.

Ý nghĩa trạng thái:
- **ĐẠT**: Claude đã chạy và có bằng chứng.
- **CHƯA ĐẠT**: đã kiểm và không đạt.
- **CHƯA KIỂM CHỨNG**: chưa có bằng chứng.

## Tóm tắt

**6 tiêu chí ĐẠT. 1 tiêu chí ĐẠT phía API nhưng phần giao diện CHƯA KIỂM CHỨNG trên trình duyệt.** Không tiêu chí nào CHƯA ĐẠT.

Riêng phần duyệt nội dung corpus là việc của người, đang **CHƯA DUYỆT** (tiêu chí 5 chỉ yêu cầu trạng thái duyệt được ghi trung thực).

| # | Tiêu chí | Trạng thái | Bằng chứng |
| --- | --- | --- | --- |
| 1 | Ba chế độ chạy được qua API và giao diện; chế độ RAG trả nguồn; lỗi hạ tầng không làm chat chết | **ĐẠT (API)** · **CHƯA KIỂM CHỨNG (giao diện trên trình duyệt)** | `test_chat_rag.py` (9 test): `dense`/`hybrid` trả 3 nguồn kèm `rag_mode`; `llm_only` không có nguồn; giá trị chế độ lạ → 422; retriever lỗi → 200, `rag_mode=llm_only`, `rag_fallback=true`. Smoke thật (`RUN_RAG_SMOKE_LLM=1`, Gemini thật, Qdrant v1.20.2 thật, BGE-M3 thật): hybrid và dense đều 200, nguồn [1] đúng bài, `has_citations=true`. Giao diện: `npm run build` đạt, `npm test` 17/17; **chưa thao tác trên trình duyệt** |
| 2 | Trích dẫn chỉ trỏ đến tài liệu thực sự đã truy xuất; có test và đã làm hỏng thử | **ĐẠT** | `check_citations` + test: `[9]`, `[2, 7]` bị loại khi chỉ có 3 nguồn; DB lưu `{"valid":[1,2],"invalid":[7,9]}`. Làm hỏng có chủ đích (không loại trích dẫn ngoài tập) → 4 failed; khôi phục, `cmp` khớp |
| 3 | Số đo thật Recall@K/MRR/độ trễ trên dev cho dense và hybrid, lưu trong `experiments/`, kèm phân tích loại truy vấn thất bại | **ĐẠT** | `experiments/retrieval_dev_20261127T145143Z.json`. Dense: R@1 0,75 / R@3 0,95 / R@5 1,00 / MRR 0,863 / p95 316 ms. Hybrid: 0,80 / 1,00 / 1,00 / MRR 0,883 / p95 359 ms. BM25: MRR 0,666. Phân tích theo loại truy vấn, ngôn ngữ, kèm ví dụ thất bại: `experiments/README.md`. Test split không chạy (script từ chối, đã thử) |
| 4 | Số đo hiệu năng BGE-M3 trên CPU thật; ngưỡng quyết định ghi rõ | **ĐẠT** | `experiments/bge_m3_cpu_benchmark.json`, 3 lần đo. p95 nhúng truy vấn tệ nhất 110 ms (ngưỡng 2000 ms); RAM đỉnh 2,08 GB (ngưỡng 6 GB); nhúng 45 văn bản khoảng 11 giây; vector 1024 chiều → cổng đạt |
| 5 | Corpus ≥ 30 bài hợp lệ, trạng thái duyệt trung thực (**người dùng đã duyệt đạt 18 bài mới ngày 2026-11-28, chọn Anh–Mỹ; 4 bài sửa chính tả**); test split và 30 truy vấn cũ không bị chạm | **ĐẠT** | 33 bài (11/11/11); `validate_dataset.py`: 33 bài, 0 lỗi; `git diff`: chỉ thêm dòng, 15 bài cũ không đổi; `docs/CORPUS_REVIEW.md`: 18 bài mới "CHƯA DUYỆT — cần người kiểm ngữ pháp". `git diff data/evaluation` rỗng; `validate_evaluation.py`: 20 dev / 10 test |
| 6 | Test mặc định không cần mạng/key; smoke test có tài nguyên thật đã chạy một lần có báo cáo | **ĐẠT** | `pytest` với `GEMINI_API_KEY=""`, `LLM_PROVIDER=fake`, proxy trỏ cổng chết: **398 passed, 5 skipped** (đều là smoke, mặc định tắt). Test dùng `HashingEmbedder` + `QdrantClient(":memory:")`; conftest ép `RAG_MODE=llm_only`. Smoke RAG đã chạy: truy xuất thật 2/2, chat thật 2/2 (2 lời gọi Gemini) |
| 7 | Không có secret trong mã, log, Git; log không chứa nội dung tin/ngữ cảnh; README cập nhật | **ĐẠT** | Quét secret: key Gemini, JWT secret, mật khẩu DB đều 0 lần trong file sẽ commit, `dist` và lịch sử Git; 0 chuỗi `AIza…`. Test `caplog` ở chế độ RAG không thấy câu hỏi, câu trả lời hay ngữ cảnh. README: Qdrant, tải model, biến mới, nạp index, đánh giá, smoke |

## Kiểm tra bắt buộc

| Kiểm tra | Kết quả |
| --- | --- |
| pytest (không mạng, không key) | 398 passed, 5 skipped (`test_llm_smoke` 1; `test_rag_smoke` 4 — mặc định tắt) |
| `npm test` / `npm run build` | 17/17 / đạt |
| Alembic trên DB test: upgrade → check → downgrade → upgrade → check | Đạt (`dfd85f565969` ↔ `a4c9e2f17b30`) |
| Alembic trên DB chính (người dùng đã cho phép) | `upgrade` lên `a4c9e2f17b30`, `check` không lệch |
| Làm hỏng có chủ đích (6 chỗ) | RRF `k+rank` → `k*rank`: 3 failed · BM25 bỏ lọc ngôn ngữ: 1 · dense bỏ lọc ngôn ngữ: 1 · không loại trích dẫn ngoài tập: 4 · đảo dấu IDF: 5 · chat không hạ cấp khi truy xuất lỗi: 1. Khôi phục, `cmp` đều khớp |

## Người dùng tự báo (2026-11-28)

- Đã thử giao diện RAG trên trình duyệt theo hướng dẫn (vòng A với fake, vòng B với Gemini): **đạt**.
- Hỏi câu không có trong tài liệu: AI trả lời là bài học chưa có chủ đề này, **không bịa**.
- Phản hồi cần sửa:
  1. Câu trả lời còn sơ sài.
  2. Nhiều dấu `*` (Markdown) hiện nguyên văn.

  → Đã xử lý ở mục "Hoàn thiện sau phản hồi" bên dưới.

## Hoàn thiện sau phản hồi (Claude đã chạy, 2026-11-28)

- **Prompt** `tutor.md` và `tutor_rag.md`:
  - Cấm Markdown, chỉ viết văn bản thuần; danh sách dùng "- ".
  - Câu trả lời ngữ pháp theo khung: Quy tắc → Cấu trúc → Ví dụ (vẫn **tối đa 3**, giữ quyết định của Tuần 3, có bản dịch trong ngoặc tròn) → Lỗi thường gặp → Tự kiểm tra. Độ sâu điều chỉnh theo trình độ.
  - Ở chế độ RAG: Quy tắc, Cấu trúc và Lỗi thường gặp phải lấy từ tài liệu và có trích dẫn; câu ví dụ do AI tự đặt thì không cần trích dẫn.
- **Giao diện:** `lib/richText.ts` là hàm thuần, dựng phần tử React, **không dùng HTML** và không thêm thư viện.
  - `**đậm**` thành chữ đậm; dấu `*` và `` ` `` lẻ bị bỏ.
  - Đầu dòng `-`, `*`, `•`, `1.` thành danh sách; nhãn như "Quy tắc:" được in đậm.
  - Áp dụng cả cho tin nhắn cũ đã lưu.
  - Có 4 test mới; `npm test` 21/21; build đạt.
- **Gemini thật** (2 lời gọi, tổng tuần 4/10): `RUN_RAG_SMOKE_LLM=1`, trước khi đổi chữ "ngoặc vuông" thành "ngoặc tròn":

  | Chế độ | Số ký tự | Dấu `*` | Nhãn | Trích dẫn |
  |---|---|---|---|---|
  | hybrid | 742 | **0** | đủ 5 | [1] đúng bài articles |
  | dense | 568 | **0** | đủ 5 | [1] đúng bài passive |

  Trước đó, câu trả lời có `**...**`.
- Bản dịch ví dụ từng nằm trong `[...]`, dễ nhầm với trích dẫn. Prompt đã đổi sang ngoặc tròn; **chưa gọi lại Gemini sau thay đổi chữ này**.
- `pytest` 400 passed, 5 skipped (có thêm 2 test prompt).

## Thử trên trình duyệt (người dùng tự thử)

Chuẩn bị:
- Đặt `RAG_MODE=hybrid` trong `.env` (hoặc để mặc định rồi chọn chế độ trên giao diện).
- Chạy `LLM_PROVIDER=gemini` để có câu trả lời thật. Mỗi tin tốn 1 lời gọi Gemini.

1. Chọn từng chế độ trong ô "Chế độ trả lời" và gửi câu hỏi.
   - Ở dense/hybrid: dưới câu trả lời có khung "Nguồn"; bấm vào một nguồn thì thấy đoạn bài đã dùng.
   - Lưu ý "không dẫn nguồn" chỉ hiện ở chế độ "Chỉ AI".
2. Dừng Qdrant (`docker compose stop qdrant`), gửi một tin ở chế độ hybrid.
   - Kết quả đúng: vẫn có câu trả lời, kèm ghi chú "Không truy xuất được tài liệu…".
   - Sau đó chạy `docker compose start qdrant`.
3. Màn hình rộng 360px: ô chọn chế độ và khung nguồn không làm tràn ngang.
