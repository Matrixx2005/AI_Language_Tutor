# Thí nghiệm (Tuần 4)

Mọi số liệu ở đây là số chạy thật trên máy phát triển (Intel Core Ultra 7 155H, 16 nhân / 22 luồng, 31,6 GB RAM, Windows 11, **chỉ CPU**). File gốc nằm cùng thư mục; không chỉnh tay.

| File | Nội dung |
| --- | --- |
| `bge_m3_cpu_benchmark.json` | Bước 1: cổng kiểm tra BGE-M3 trên CPU (3 lần đo) |
| `retrieval_dev_*.json` | Mỗi lần chạy `scripts/eval_retrieval.py`: cấu hình, phiên bản model, git commit, kết quả từng truy vấn |
| `retrieval_runs.jsonl` | Nhật ký tóm tắt **mọi** lần chạy đánh giá (kể cả lần sai), một dòng mỗi lần |

## 1. BGE-M3 trên CPU (cổng Bước 1)

Lệnh: `python scripts/bench_bge_m3.py --runs 3`. Mỗi lần đo chạy trong một tiến trình riêng. Model `BAAI/bge-m3@5617a9f`, torch 2.15.0+cpu, sentence-transformers 6.3.0, 16 luồng torch.

| Chỉ số | Lần 1 | Lần 2 | Lần 3 | Ngưỡng dừng |
| --- | --- | --- | --- | --- |
| Tải model (s), từ cache cục bộ | 12,32 | 14,08 | 10,04 | — |
| RAM đỉnh của tiến trình (GB) | 2,07 | 2,08 | 2,07 | > 6 GB → dừng |
| Nhúng 45 văn bản, batch 16 (s) | 12,31 | 10,87 | 10,54 | — |
| Nhúng 1 truy vấn p50 (ms) | 82,1 | 60,7 | 59,1 | — |
| Nhúng 1 truy vấn p95 (ms) | 109,8 | 66,4 | 63,8 | > 2000 ms → dừng |
| Kích thước vector | 1024 | 1024 | 1024 | — |

**Kết luận: cổng ĐẠT.** p95 tệ nhất là 110 ms, so với ngưỡng 2000 ms. RAM đỉnh là 2,08 GB, so với ngưỡng 6 GB. Không cần đổi model.

Lưu ý:
- 45 văn bản là 15 bài có trước khi mở rộng, lặp lại 3 lần, vì cổng này đo trước khi mở rộng corpus.
- Bộ dev chỉ có **20** truy vấn, không phải 30, nên p50/p95 tính trên 20 truy vấn dev; không dùng test split.
- Lần đo đầu tiên báo RAM = 0,0 GB do lỗi khai báo kiểu handle 64-bit khi gọi `GetProcessMemoryInfo`. Đã sửa script và đo lại cả 3 lần; bảng trên là lần đo lại.

## 2. Đánh giá truy xuất trên DEV split

Lệnh: `python scripts/eval_retrieval.py --keywords both`. Cài đặt:
- 20 truy vấn dev: 10 tiếng Việt, 10 tiếng Anh; 10 truy vấn thuật ngữ (terminology), 10 truy vấn theo nghĩa (semantic).
- Corpus 33 bài, 1 bài = 1 chunk. Mỗi truy vấn có đúng 1 tài liệu đúng.
- Không lọc trình độ. BM25 dùng k1 = 1,5, b = 0,75. RRF dùng k = 60, mỗi nhánh lấy 20 ứng viên.
- MRR tính trên 10 kết quả đầu.

Độ trễ là thời gian một lần gọi `search` (gồm nhúng truy vấn và truy vấn Qdrant qua REST), đo sau một lần khởi động.

**Test split không được chạy.** Script từ chối chạy test split nếu không có cờ riêng.

### Kết quả (`retrieval_dev_20261127T145143Z.json`)

| Phương pháp | index_text | R@1 | R@3 | R@5 | MRR@10 | p50 (ms) | p95 (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BM25 (phân tích) | title + topic + content | 0,55 | 0,75 | 0,80 | 0,666 | 0,1 | 0,1 |
| **Dense** (BGE-M3 + Qdrant) | title + topic + content | 0,75 | 0,95 | 1,00 | 0,863 | 238,8 | 316,3 |
| **Hybrid** (BM25 + dense, RRF) | title + topic + content | 0,80 | **1,00** | 1,00 | 0,883 | 262,8 | 359,1 |
| BM25 | + keywords_vi | 0,60 | 0,85 | 0,90 | 0,732 | 0,1 | 0,1 |
| Dense | + keywords_vi | **0,90** | 0,95 | 1,00 | **0,938** | 286,8 | 338,3 |
| Hybrid | + keywords_vi | 0,85 | 0,90 | 0,90 | 0,888 | 260,9 | 336,3 |

Tách theo loại truy vấn và ngôn ngữ (index_text không có keywords_vi), dạng R@1 / MRR@10:

| | Thuật ngữ | Theo nghĩa | Tiếng Anh | Tiếng Việt |
| --- | --- | --- | --- | --- |
| BM25 | 0,70 / 0,850 | 0,40 / 0,481 | 0,70 / 0,820 | 0,40 / 0,511 |
| Dense | 0,70 / 0,825 | **0,80 / 0,900** | 0,90 / 0,950 | 0,60 / 0,775 |
| Hybrid | **1,00 / 1,000** | 0,60 / 0,767 | **1,00 / 1,000** | 0,60 / 0,767 |

### Nhận xét trung thực

- **Hybrid hơn Dense trên toàn bộ dev**, nhưng chỉ một chút: R@1 0,80 so với 0,75, R@3 1,00 so với 0,95, MRR 0,883 so với 0,863. Chênh lệch tương ứng 1 truy vấn trên 20, không đủ để kết luận có ý nghĩa thống kê.
- Ưu thế không đồng đều:
  - Hybrid thắng ở **truy vấn thuật ngữ**: R@1 = 1,00, trong khi dense chỉ 0,70.
  - Hybrid **thua dense ở truy vấn theo nghĩa**: MRR 0,767 so với 0,900. Lý do là nhánh BM25 kéo tài liệu nhiễu lên.
- Không chỉnh siêu tham số nào để Hybrid thắng: k, số ứng viên, k1, b đều giữ mặc định từ đầu.
- Chạy 2 lần với cùng cấu hình (xem `retrieval_runs.jsonl`):
  - Lần 1 có độ trễ dense/hybrid sai, khoảng 2,2 giây. Nguyên nhân là `.env` đặt `QDRANT_URL=http://localhost:6333`: Windows thử IPv6 trước nên mỗi lời gọi Qdrant mất khoảng 2 giây. Code đã đổi `localhost` thành `127.0.0.1`.
  - Lần 2 cho chỉ số truy xuất giống hệt lần 1; chỉ độ trễ thay đổi.

### Loại truy vấn mỗi phương pháp thất bại (ví dụ thật, index_text gốc)

- **BM25: truy vấn tiếng Việt diễn đạt theo tình huống, không có thuật ngữ.** Corpus viết bằng tiếng Anh, nên hai bên không có từ chung.
  - `rag-q-007` "Nam đang nấu ăn ngay lúc này. Cấu trúc nào diễn tả hành động đang xảy ra?" → bài present continuous **không nằm trong 10 kết quả đầu**.
  - `rag-q-011` "…chưa từng đi máy bay, không nêu thời điểm…" → bài present perfect không có trong top 10.
  - `rag-q-029` "…'hai chai nước'…" → bài countable/uncountable không có trong top 10.
  - BM25 tiếng Việt chỉ đạt R@1 = 0,40.
- **Dense: truy vấn nhắm vào một thuật ngữ cụ thể, khi có bài khác gần nghĩa.**
  - `rag-q-013` "Động từ have to thay đổi thế nào theo chủ ngữ và ở thì quá khứ?" → bài modal verbs ở hạng 4. Dense xếp *used to*, *past perfect*, *past simple* lên trước vì cụm "thì quá khứ".
  - `rag-q-014` "Which modal verb is commonly used to give advice…" → hạng 2, sau bài *will*.
  - `rag-q-017` "Ở thì hiện tại đơn, khi chủ ngữ là he/she/it…" → hạng 2, sau bài *present continuous*.
- **Hybrid: truy vấn tiếng Việt theo nghĩa**, vì BM25 đưa nhiễu vào.
  - `rag-q-007`: hạng 2, sau bài *this/that/these/those*.
  - `rag-q-011`: hạng 3.
  - `rag-q-029`: hạng 3.

### Trường `keywords_vi` (mở rộng phía tài liệu): đã đo, KHÔNG bật mặc định

- **Tác dụng đo được:** cải thiện **dense** (MRR từ 0,863 lên 0,938; R@1 từ 0,75 lên 0,90) và **BM25** (MRR từ 0,666 lên 0,732). Áp dụng giống hệt cho cả hai nhánh.
- **Nhưng hybrid giảm R@3 từ 1,00 xuống 0,90:**
  - `rag-q-011` tụt xuống hạng 8;
  - `rag-q-013` tụt xuống hạng 7, vì từ khóa "quá khứ" của các bài thì quá khứ cạnh tranh.
- **Rủi ro rò rỉ:** từ khóa do Claude soạn, và Claude cũng là người viết 30 truy vấn đánh giá ở Tuần 1. Dù đã viết từ khóa theo chủ đề và không chép câu truy vấn, vẫn có thể vô tình khớp cách diễn đạt của dev split. Mức cải thiện vì vậy có thể bị thổi phồng.
- **Quyết định:** giữ `RAG_INDEX_KEYWORDS_VI=false` (mặc định). File `data/processed/keywords_vi_v1.json` tách riêng và có trạng thái CHƯA DUYỆT; 15 bài gốc không bị sửa. Chỉ nên bật khi có người duyệt từ khóa và đánh giá lại.

### Đề xuất cấu hình

- **`RAG_MODE=hybrid`**, keywords_vi **tắt**. Với `RAG_TOP_K=3`, chỉ số quan trọng nhất là R@3, và hybrid đạt R@3 = 1,00 trên dev.
- Mặc định trong code vẫn là `llm_only`, để một bản sao mới chạy được khi chưa có Qdrant hoặc model. Người dùng tự đặt `RAG_MODE` trong `.env`, hoặc chọn chế độ ngay trên giao diện.
