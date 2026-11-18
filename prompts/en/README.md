# English prompt templates

Đặt template prompt dành riêng cho ngôn ngữ tiếng Anh trong thư mục này. Module dùng chung cần truyền `language_code`, `level_code`, mục tiêu tác vụ và dữ liệu context; không hardcode nội dung tiếng Anh vào luồng dùng chung.

Với RAG, chỉ trích dẫn `document_id` có trong context được cung cấp. Prompt không thay thế validate đầu vào, kiểm tra quyền truy cập, hoặc kiểm chứng đầu ra ở API. Chưa có template runtime trong Tuần 1.
