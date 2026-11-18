# Phác thảo mở rộng đa ngôn ngữ

## Mục tiêu và giới hạn

Thiết kế để có thể bổ sung cấu hình ngôn ngữ mà không viết lại luồng học tập dùng chung. MVP hiện chỉ nhắm tới tiếng Anh (`en`); tài liệu này không triển khai ngôn ngữ hoặc tính năng mới. Không đưa dữ liệu tiếng Trung, Nhật hay Hàn vào phạm vi 8 tuần.

## Nguyên tắc thiết kế

1. **Mã ngôn ngữ là dữ liệu, không phải nhánh code.** Dùng `language_code` dạng chuỗi trên nội dung, kết quả học, hội thoại và chỉ mục retrieval. Giá trị mặc định hiện tại là `en`; không dùng enum DB để đóng danh sách ngôn ngữ.
2. **Cấp độ là cấu hình mở.** `level_code` là chuỗi; ứng dụng đọc danh sách level từ `languages/<code>.yaml`. A1/A2/B1 hiện là cấu hình tiếng Anh, không phải enum CEFR dùng chung cho mọi ngôn ngữ.
3. **Tách dữ liệu theo ngôn ngữ.** Mỗi tài liệu phải có `language_code`; retrieval lọc theo `language_code` và `level_code` trước khi xếp hạng. Không trộn tài liệu của các ngôn ngữ trong cùng kết quả nếu chưa có chế độ cross-lingual được yêu cầu rõ ràng.
4. **Tách prompt theo ngôn ngữ.** Template riêng đặt tại `prompts/<code>/`. Prompt chung chỉ giữ chính sách, cấu trúc đầu vào/đầu ra và biến; câu chữ hướng dẫn người học thuộc về template tương ứng.
5. **Đăng ký loại bài tập thay vì rẽ nhánh theo ngôn ngữ.** API dùng registry/key cấu hình để chọn factory hoặc validator; loại không hỗ trợ phải báo lỗi rõ, không âm thầm rơi về bài tập tiếng Anh.
6. **Không hardcode tiếng Anh trong module dùng chung.** Thông báo, nhãn, ví dụ, luật xử lý chính tả/ngữ pháp và ngưỡng placement phải lấy từ cấu hình hoặc handler đã đăng ký.

## Hợp đồng cấu hình

Mỗi `languages/<code>.yaml` nên cung cấp:

- mã ngôn ngữ và tên hiển thị;
- danh sách level với `code` dạng chuỗi và tên hiển thị;
- ngưỡng/chiến lược placement riêng theo ngôn ngữ, có trạng thái kiểm định;
- quy tắc định dạng văn bản cần thiết (nếu có), không dùng để thay thế kiểm tra đầu vào.

`languages/en.yaml` hiện có A1/A2/B1 và ngưỡng 40%/70% ở trạng thái provisional. Các ngưỡng này chưa được hiệu chuẩn trên pilot và không đại diện cho kết quả nghiên cứu.

## Luồng dữ liệu đa ngôn ngữ

1. Client gửi `language_code` và `level_code`; API xác thực chúng với cấu hình đã nạp.
2. Dịch vụ học tập truyền hai mã này xuyên suốt truy vấn, persistence, nội dung, chat và kết quả đánh giá.
3. Bộ nạp tài liệu kiểm tra metadata và license; Qdrant/BM25 lập chỉ mục tách biệt hoặc gắn filter theo language/level.
4. Query dùng prompt và bộ tokenizer/normalizer phù hợp đã đăng ký; retrieval chỉ trả tài liệu được phép của ngôn ngữ đó.
5. Nếu code hoặc tài nguyên ngôn ngữ không tồn tại, API trả lỗi “unsupported language” có cấu trúc; không fallback im lặng sang `en`.
6. Kết quả được đánh giá trên bộ dev/test riêng theo ngôn ngữ; không so sánh chất lượng giữa ngôn ngữ khi chưa có dữ liệu đánh giá tương đương.

## Registry bài tập

Registry dùng một khóa ổn định (ví dụ `multiple_choice`) và ánh xạ tới thành phần có hợp đồng chung:

- tạo/đọc cấu hình bài tập;
- validate cấu trúc câu hỏi và đáp án;
- chấm câu trả lời;
- cung cấp giải thích theo `language_code`/`level_code`.

Ngôn ngữ được truyền dưới dạng cấu hình hoặc dependency; tránh `if language_code == "en"` rải rác trong logic dùng chung. Hành vi đặc thù chữ viết/ngữ pháp nên nằm trong handler ngôn ngữ có kiểm thử riêng.

## Quy trình thêm một ngôn ngữ trong tương lai

1. Duyệt mã, tên hiển thị, level và chính sách placement của ngôn ngữ mới.
2. Thêm `languages/<code>.yaml` và schema validation cho cấu hình.
3. Thêm prompt template cùng bài kiểm tra placeholder, giới hạn và citation.
4. Soạn corpus có nguồn/license, metadata ngôn ngữ/cấp độ và kiểm tra trùng lặp.
5. Tạo bộ dev/test bản địa hóa, gắn nhãn nguồn tài liệu liên quan và khóa phân chia.
6. Đăng ký handler/loại bài tập cần thiết; viết test dùng chung và test đặc thù ngôn ngữ.
7. Đo chất lượng truy xuất, đúng ngữ pháp, citations và latency trước khi bật cho người học.

## Kiểm tra chống hardcode

- Unit test chạy cùng nghiệp vụ với ít nhất hai cấu hình giả lập có level_code khác nhau; không dùng mạng hoặc model tải về.
- Test truy vấn bảo đảm `language_code`/`level_code` được truyền tới cả retriever và persistence.
- Test unsupported code bảo đảm lỗi hiển thị rõ và không sử dụng prompt/tài liệu `en`.
- Lint/code review tìm chuỗi câu trả lời, ngưỡng placement, danh sách level và điều kiện ngôn ngữ được viết trực tiếp trong module dùng chung.
- Kiểm tra thủ công tính phù hợp với chuyên gia/người bản ngữ trước khi phát hành nội dung.

Hiện chưa có module học tập dùng chung để kiểm tra hardcode; các điều trên là tiêu chí thiết kế cho những tuần triển khai sau, không phải kết quả kiểm thử code hiện tại.
