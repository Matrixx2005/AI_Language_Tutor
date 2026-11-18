# Kiến trúc hệ thống

## Mục tiêu và phạm vi

AI Language Tutor là monorepo cho ứng dụng học tiếng Anh A1–B1, ưu tiên giao diện tiếng Việt. Tuần 1 chỉ chốt kiến trúc logic; tài liệu này không đồng nghĩa các dịch vụ hay ứng dụng đã được triển khai.

## Thành phần

| Thành phần | Công nghệ dự kiến | Trách nhiệm |
| --- | --- | --- |
| Web client | React, TypeScript, Vite, Tailwind CSS | Giao diện người học, placement, bài học, bài tập, chat và dashboard |
| API | FastAPI, Pydantic | API nghiệp vụ, xác thực đầu vào/đầu ra, điều phối học tập và RAG |
| Cơ sở dữ liệu quan hệ | PostgreSQL, SQLAlchemy, Alembic | Người dùng, hồ sơ học tập, nội dung, kết quả, lịch ôn và lịch sử chat |
| Vector store | Qdrant | Lưu và truy vấn vector tài liệu, có lọc metadata theo ngôn ngữ/cấp độ |
| Sparse retrieval | BM25 (thư viện `rank_bm25` dự kiến) | Tìm khớp từ khóa và thuật ngữ |
| Dense retrieval | BGE-M3 qua sentence-transformers/FlagEmbedding | Tìm tương đồng ngữ nghĩa đa ngôn ngữ |
| LLM | Gemini Flash qua API | Trả lời dựa trên ngữ cảnh được truy xuất và tạo giải thích |
| Dịch vụ phát triển | Docker Compose | Chạy PostgreSQL và Qdrant local khi triển khai các tuần sau |

Các phiên bản, model ID, giới hạn dịch vụ và khả năng vận hành chưa được chốt ở đây. Không có API key trong mã nguồn; cấu hình bí mật lấy từ biến môi trường hoặc `.env` không đưa vào Git.

## Luồng RAG

1. API nhận câu hỏi, `language_code`, `level_code` và chế độ truy xuất. Giá trị ngôn ngữ/cấp độ phải được kiểm tra với cấu hình và dữ liệu được phép dùng.
2. Tách truy vấn thành các dạng phù hợp cho truy vấn từ khóa và truy vấn ngữ nghĩa; giữ nguyên nội dung gốc để trả lời.
3. Chạy BM25 và dense retrieval độc lập theo cấu hình. Mỗi nhánh lọc tài liệu theo `language_code`, `level_code` và metadata phù hợp.
4. Hợp nhất thứ hạng bằng Reciprocal Rank Fusion (RRF); chọn tập ngữ cảnh trong giới hạn token.
5. Tạo prompt từ template của ngôn ngữ đích, câu hỏi, cấp độ và các đoạn trích có ID tài liệu.
6. Gọi Gemini Flash; câu trả lời chỉ được dẫn nguồn từ các tài liệu thực sự được đưa vào ngữ cảnh.
7. Trả lời cùng citations, lưu phiên chat/tin nhắn và thông tin truy xuất cần thiết để đánh giá. Khi không có ngữ cảnh đáng tin cậy, hệ thống cần nói rõ giới hạn thay vì bịa citation.

### Các chế độ đánh giá

- **LLM-only:** không truy xuất, làm baseline.
- **Dense RAG:** chỉ dense retrieval.
- **Hybrid RAG:** BM25 và dense retrieval, sau đó RRF.

Hai retriever có thể bật/tắt độc lập để chạy ablation. Cấu hình, model ID, top-k, phiên bản corpus và thời gian chạy cần được lưu cùng kết quả thực nghiệm. Tập dev dùng để điều chỉnh; test chỉ dùng cho báo cáo cuối, không dùng lặp để tối ưu.

## Quyết định kỹ thuật và lý do

| Quyết định | Lý do / đánh đổi |
| --- | --- |
| Tách web, API, PostgreSQL và Qdrant thành thành phần riêng | Ranh giới rõ, có thể kiểm thử từng tầng; đổi lại cần phối hợp cấu hình và vận hành nhiều dịch vụ |
| Dùng PostgreSQL cho dữ liệu nghiệp vụ và Qdrant cho vector | Tránh trộn giao dịch/quan hệ với truy vấn vector; metadata phải được đồng bộ có chủ đích |
| Dùng BM25 + dense + RRF | So sánh sparse/dense/hybrid theo câu hỏi nghiên cứu; RRF không cần hiệu chỉnh thang điểm giữa hai retriever |
| Giữ `language_code` và `level_code` là chuỗi mở | Cho phép mở rộng cấu hình, không khóa ngôn ngữ hay cấp độ vào enum CEFR trong schema |
| Tách cấu hình ngôn ngữ và prompt theo mã ngôn ngữ | Nội dung/messaging không bị buộc vào tiếng Anh; phần dùng chung nhận ngôn ngữ từ cấu hình |
| Lưu citation theo ID tài liệu | Có thể kiểm tra nguồn và đo citation accuracy; không chấp nhận nguồn do LLM tự tạo |
| Chạy model embedding trên CPU trước | Phù hợp môi trường dự kiến và tránh giả định có CUDA; phải đo latency/RAM trước khi quyết định thay đổi |

## Rủi ro và kiểm soát

- BGE-M3/PyTorch có thể tốn dung lượng, RAM và thời gian trên CPU; dry-run tương thích không chứng minh hiệu năng.
- Chất lượng truy vấn tiếng Việt trên corpus tiếng Anh cần được đo riêng; không xem hỗ trợ đa ngôn ngữ của model là bảo đảm chất lượng.
- LLM có thể trả lời sai hoặc dựng nguồn; ràng buộc context/citation và đánh giá faithfulness, correctness, citation accuracy.
- Quyền sử dụng tài liệu phải được ghi theo từng tài liệu; ưu tiên nội dung tự biên soạn được duyệt.
- Gemini có thay đổi model ID, quota hoặc điều khoản; cô lập qua adapter và cấu hình môi trường.
- Dữ liệu đánh giá nhỏ có thể lệch; cố định phân chia dev/test trước khi tối ưu và không tuyên bố kết quả trước khi đo.

## Ranh giới Tuần 1

Không có API nghiệp vụ, migration, tích hợp Gemini, tải model/dataset hoặc dịch vụ chạy thật trong phạm vi tài liệu kiến trúc này.
