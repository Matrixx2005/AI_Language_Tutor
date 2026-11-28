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

### Đo lại sau khi duyệt corpus (`retrieval_dev_20261128T142006Z.json`)

Người dùng duyệt corpus; 4 bài đổi chính tả sang Anh–Mỹ. Không đổi tham số nào.

- **Mọi chỉ số Recall@K và MRR giống hệt** bảng ở trên, ở cả 6 cấu hình.
- **Độ trễ thấp hơn đáng kể** dù code và cấu hình không đổi:

  | Phương pháp | p50 | p95 | p95 lần trước |
  |---|---|---|---|
  | Dense | 81,5 ms | 115,1 ms | 316 ms |
  | Hybrid | 67,0 ms | 79,5 ms | 359 ms |

  Kết luận: độ trễ trên máy phát triển **dao động giữa các lần chạy**, nhiều khả năng do tải máy (các ứng dụng khác, chế độ nguồn điện). Vì vậy độ trễ chỉ nên đọc như một khoảng, khoảng 70–360 ms cho mỗi truy vấn. Cả hai lần đều được giữ trong `retrieval_runs.jsonl`.

## 3. Bộ đánh giá v2 — DEV (Tuần 5A, `retrieval_dev_20261128T144004Z.json`)

Bộ v2 (`data/evaluation/rag_queries_v2.json`) có 109 truy vấn; dev split gồm 78 truy vấn: **71 có đáp án** và 7 `expected=none`.
- Split được gán bằng băm cố định **trước** khi đánh giá.
- Cấu hình **giữ nguyên** như Tuần 4: không chỉnh tham số, không chọn lại cấu hình theo kết quả này.
- Khoảng tin cậy: bootstrap 1000 lần, seed 20261128.
- Test split không chạy.

| Cấu hình | R@1 | R@3 [CI 95%] | R@5 | MRR@10 [CI 95%] | p50 / p95 (ms) |
| --- | --- | --- | --- | --- | --- |
| BM25 | 0,58 | 0,66 [0,55; 0,76] | 0,70 | 0,629 [0,528; 0,728] | 0,1 / 0,1 |
| **Dense** | 0,75 | **0,92** [0,85; 0,97] | 0,99 | **0,843** [0,781; 0,905] | 64 / 96 |
| **Hybrid** | 0,73 | 0,90 [0,82; 0,96] | 0,94 | 0,821 [0,751; 0,892] | 66 / 81 |
| BM25 + keywords_vi | 0,65 | 0,80 [0,70; 0,89] | 0,86 | 0,736 [0,639; 0,819] | 0,1 / 0,1 |
| Dense + keywords_vi | 0,79 | 0,93 [0,86; 0,99] | 0,99 | 0,868 [0,809; 0,925] | 61 / 74 |
| Hybrid + keywords_vi | 0,82 | 0,90 [0,83; 0,96] | 0,93 | 0,868 [0,793; 0,934] | 64 / 85 |

**So sánh cặp Hybrid − Dense** (cùng truy vấn, paired bootstrap):

| index_text | Δ R@3 [CI 95%] | p | Δ MRR [CI 95%] | p |
| --- | --- | --- | --- | --- |
| gốc | −0,014 [−0,070; 0,042] | 0,79 | −0,022 [−0,089; 0,046] | 0,51 |
| + keywords_vi | −0,028 [−0,085; 0,028] | 0,44 | −0,000 [−0,054; 0,051] | 0,95 |

**Kết luận trung thực:**
- Trên bộ dev lớn hơn, **Hybrid không hơn Dense**; về số điểm, Hybrid còn thấp hơn một chút.
- Mọi khác biệt đều **không có ý nghĩa thống kê** (p ≥ 0,44, khoảng tin cậy chứa 0).
- Đề xuất `RAG_MODE=hybrid` ở Tuần 4 dựa trên 20 truy vấn dev (R@3 1,00 so với 0,95). Đề xuất đó **không được bộ v2 xác nhận**: hai phương pháp tương đương trong phạm vi sai số.
- Theo yêu cầu, cấu hình không bị chọn lại dựa trên kết quả này; quyết định để người dùng đưa ra.

**Theo loại truy vấn (gốc, R@3 / MRR):**

| Phương pháp | Thuật ngữ | Theo nghĩa | Tiếng Anh | Tiếng Việt |
|---|---|---|---|---|
| Dense | 0,94 / 0,90 | 0,89 / 0,78 | 0,97 / 0,87 | 0,86 / 0,81 |
| Hybrid | 0,97 / 0,93 | 0,83 / 0,71 | 0,91 / 0,89 | 0,89 / 0,76 |

Xu hướng giống Tuần 4: hybrid nhỉnh hơn ở truy vấn thuật ngữ, kém hơn ở truy vấn theo nghĩa.

**Truy vấn trượt top-3 (gốc):**
- Dense trượt 6 truy vấn:
  - `rag-q-013` (have to; hạng 4);
  - `rag-q2-021` ("ngày tệ nhất", superlatives; hạng 4);
  - `rag-q2-037` (bị động hiện tại đơn; hạng 4);
  - `rag-q2-047` ("phim đã bắt đầu", past perfect; hạng 4);
  - `rag-q2-056` ("My father work…", present simple; hạng 7);
  - `rag-q2-059` (there is; hạng 5).
- Hybrid trượt 7 truy vấn, chủ yếu là câu **sửa lỗi** và câu tình huống mà BM25 kéo bài sai lên:
  - `rag-q2-032` ("sings beautiful", hạng 8);
  - `rag-q2-018` ("goes usually", hạng 5);
  - `rag-q2-068` (câu điều kiện loại 1 viết bằng tiếng Việt, hạng 4);
  - và các truy vấn 037, 047, 056, 059 giống dense.

**Nhóm `expected=none`** (7 truy vấn dev; chỉ đo, chưa đặt ngưỡng từ chối):

| Phương pháp | Trung vị điểm top-1 (none) | Trung vị điểm top-1 (có đáp án) | Tỷ lệ none ≥ trung vị nhóm có đáp án | Tỷ lệ none ≥ p25 |
|---|---|---|---|---|
| Dense | 0,513 | 0,578 | 0% | 43% |
| Hybrid | 0,0325 | 0,0325 | **57%** | 71% |
| BM25 (6/7 truy vấn có kết quả) | 4,25 | 7,17 | 0% | 100% |

Nhận xét:
- Điểm RRF của hybrid chỉ phản ánh thứ hạng, nên **không phân biệt được** truy vấn không có đáp án.
- Điểm cosine của dense tách nhóm tốt hơn, nhưng vẫn chồng lấn.
- Muốn có ngưỡng từ chối thì nên dựa vào điểm dense; đây là việc của tuần sau. Hiện việc từ chối dựa vào prompt (AI nói "bài học chưa có"), như smoke test đã cho thấy.

### Đề xuất cấu hình

- **`RAG_MODE=hybrid`**, keywords_vi **tắt**. Với `RAG_TOP_K=3`, chỉ số quan trọng nhất là R@3, và hybrid đạt R@3 = 1,00 trên dev.
- Mặc định trong code vẫn là `llm_only`, để một bản sao mới chạy được khi chưa có Qdrant hoặc model. Người dùng tự đặt `RAG_MODE` trong `.env`, hoặc chọn chế độ ngay trên giao diện.
