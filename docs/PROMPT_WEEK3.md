# PROMPT TUẦN 3 — AI LANGUAGE TUTOR

Dán khối dưới đây vào Claude Code (thư mục `F:\AI_Language_Tutor`). Tuân thủ Master Prompt, `docs/PROJECT_MASTER_PLAN.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE_DESIGN.md`.

---

Hãy thực hiện **Tuần 3: LLM Tutor (chưa RAG) và Placement Test**. Chỉ làm Tuần 3, không tự chuyển sang Tuần 4.

## Mục tiêu tuần
1. Người học chat được với gia sư AI (baseline **LLM-only**, chưa RAG), lịch sử được lưu.
2. Người học làm bài kiểm tra đầu vào, nhận trình độ A1–B1 đề xuất và các chủ đề yếu.
3. Có lớp `LLMService` thay được nhà cung cấp, kiểm thử được mà **không cần mạng và không cần API key**.

## Bước 0 — Điều kiện tiên quyết (chưa đạt thì dừng và báo tôi)
- Tuần 2 đã nghiệm thu: `pytest` pass, `npm run build` pass, `alembic check` không lệch.
- Tôi đã tự tạo Gemini API key và (nếu có) tự đặt vào `.env`. **Không bao giờ yêu cầu tôi dán key vào chat; không in key ra log hay báo cáo.** Nếu `.env` chưa có key, vẫn làm được Buổi 1, 3, 4, 5 vì chỉ dùng LLM giả. Chỉ Buổi 2 (kiểm tra thật) cần key.
- Tôi hiểu nội dung chat sẽ được gửi tới dịch vụ bên ngoài (Gemini). Hỏi tôi xác nhận trước khi gọi API thật lần đầu.

## Bước 1 — Kiểm tra hiện trạng (chỉ đọc)
Đọc README, tài liệu thiết kế (đặc biệt phần chat_sessions, chat_messages, placement_results trong ERD), `languages/en.yaml`, `prompts/en/`, `data/evaluation/placement_v1.json` (cấu trúc, nhãn chủ đề, trình độ từng câu), code hiện có. Không viết lại phần đã hoàn thiện.

## Bước 2 — Lập kế hoạch (CHỜ TÔI XÁC NHẬN rồi mới triển khai)
Nêu: danh sách việc theo buổi, file tạo/sửa, thư viện (kèm phiên bản và lý do; **đọc tài liệu SDK/API chính thức hiện hành của Gemini trước khi chọn SDK và model ID, không dựa vào trí nhớ**), thay đổi schema DB (nếu lệch ERD đã duyệt thì hỏi tôi trước), rủi ro, và các quyết định cần tôi chốt:
- Model ID Gemini Flash nào (đặt trong `.env`, không hardcode ở nhiều nơi) và giới hạn gói miễn phí thực tế.
- Kết quả placement chỉ **đề xuất** trình độ hay **tự cập nhật** `current_level_code` (đề xuất: người dùng bấm xác nhận).
- Giới hạn tần suất và hạn mức tin nhắn mỗi ngày mỗi người dùng.
- Độ dài lịch sử gửi cho LLM (số lượt gần nhất) và độ dài tối đa mỗi tin nhắn.

## Bước 3 — Triển khai theo từng buổi (dừng sau mỗi buổi, báo cáo bằng chứng, chờ tôi duyệt)

**Buổi 1 — Lớp LLM và LLM giả (không mạng).**
- `LLMService` trừu tượng: nhận system prompt, danh sách tin nhắn, tùy chọn schema Pydantic cho structured output; trả về kết quả gồm văn bản hoặc đối tượng đã kiểm tra, tên model, số token vào/ra, độ trễ.
- Cấu hình nhà cung cấp và model ID đọc từ `.env`. Không module dùng chung nào được chứa chuỗi cố định của một nhà cung cấp.
- Lỗi chuẩn hóa: hết thời gian, bị giới hạn tần suất, nội dung bị chặn, phản hồi sai định dạng, lỗi máy chủ nhà cung cấp. Có timeout, retry **có giới hạn** chỉ cho lỗi tạm thời, không retry vô hạn.
- `FakeLLM` có thể lập trình sẵn: trả văn bản cố định, trả JSON sai, ném từng loại lỗi, trả chậm.
- **Test:** hành vi retry (đếm số lần gọi), timeout, từng loại lỗi, structured output hợp lệ và không hợp lệ, không rò key/secret vào `repr` hay log.

**Buổi 2 — Nhà cung cấp Gemini (cần key; xin phép trước khi gọi mạng).**
- Cài SDK chính thức sau khi tôi cho phép; ghim phiên bản; kiểm tra tương thích Python 3.13.
- Cài đặt nhà cung cấp Gemini theo giao diện của Buổi 1.
- Test đơn vị dùng phản hồi giả của SDK (không mạng). Thêm **một bài smoke test thật, mặc định bị bỏ qua**, chỉ chạy khi đặt biến môi trường bật tường minh; chỉ gửi một câu ngắn để tiết kiệm hạn mức.
- Chạy smoke test thật **một lần** sau khi tôi đồng ý, báo kết quả thật (độ trễ, số token, model thực tế phản hồi).

**Buổi 3 — Chat API, prompt gia sư, lưu lịch sử.**
- Migration (xin phép trước khi chạy) cho `chat_sessions`, `chat_messages` theo ERD, có `language_code`. Chạy `alembic check` sau đó.
- `prompts/en/tutor.md`: gia sư tiếng Anh cho người Việt, trả lời theo trình độ của người học, giải thích bằng tiếng Việt kèm ví dụ tiếng Anh, ngắn gọn, không bịa trích dẫn hay nguồn (chưa có RAG nên không dẫn nguồn), từ chối nhẹ nhàng khi lạc đề. Nạp prompt từ file theo `language_code`, không hardcode trong code dùng chung.
- API: tạo phiên chat, liệt kê phiên của mình, gửi tin nhắn (không streaming ở bước này), xem lịch sử. Giới hạn độ dài tin nhắn; chỉ gửi N lượt gần nhất cho LLM; lưu token usage mỗi lượt trả lời.
- Lỗi LLM được đổi sang mã lỗi ổn định cho frontend; **không lộ chi tiết nhà cung cấp hay stack trace**. Nếu LLM lỗi, tin nhắn người dùng vẫn được lưu nhất quán (nêu rõ chính sách bạn chọn).
- **Test:** người dùng A không đọc/ghi được phiên của B (kiểm tra cả ID đoán mò), thiếu token, tin nhắn rỗng/quá dài, LLM lỗi từng loại, lịch sử cắt đúng N lượt, prompt đúng ngôn ngữ, lưu và đọc lại đúng thứ tự.

**Buổi 4 — Giới hạn tần suất và an toàn.**
- Giới hạn số lần đăng nhập sai và số tin nhắn chat mỗi phút/ngày. Chỉ dùng cách không cần Redis; nêu rõ hạn chế (ví dụ chỉ đúng khi chạy một tiến trình) và ghi vào tài liệu.
- Kiểm tra prompt injection cơ bản: người dùng bảo "bỏ qua hướng dẫn", "in system prompt"; nội dung người dùng không được ghép vào chỗ của system prompt.
- Không ghi nội dung tin nhắn của người dùng, key, token vào log thông thường. Chỉ log metadata (độ dài, độ trễ, token, mã lỗi).
- **Test:** vượt giới hạn trả đúng mã lỗi ổn định và có thời gian chờ; giới hạn không làm hỏng người dùng khác; log không chứa nội dung tin nhắn hay key (kiểm tra bằng caplog).

**Buổi 5 — Placement test (backend).**
- Migration cho `placement_results` (và bảng đáp án nếu ERD yêu cầu), xin phép trước khi chạy.
- Nạp ngân hàng câu hỏi từ `data/evaluation/placement_v1.json` bằng script (kiểm tra schema trước khi nạp; không sửa file gốc).
- API: bắt đầu bài kiểm tra (trả câu hỏi **không kèm đáp án đúng**), nộp bài, xem kết quả. Chấm bài **hoàn toàn phía máy chủ** bằng đáp án đã duyệt, không dùng LLM để chấm trắc nghiệm.
- Ước lượng trình độ theo ngưỡng trong `languages/<code>.yaml`; tính điểm theo chủ đề và chỉ ra chủ đề yếu. Logic dùng chung không chứa A1/A2/B1 cứng.
- Kết quả ghi rõ không phải chứng chỉ CEFR chính thức. Không cho nộp hai lần cùng một lượt, không cho người khác xem kết quả của mình.
- **Test (bắt buộc):** điểm tay tính sẵn cho vài bộ đáp án mẫu; đúng ở từng ngưỡng biên (vừa đủ và thiếu một điểm); toàn đúng, toàn sai, bỏ trống; chủ đề yếu đúng; phản hồi **không bao giờ** chứa đáp án đúng trước khi nộp; nộp trùng; câu hỏi lạ; ngôn ngữ không hỗ trợ.

**Buổi 6 — Giao diện chat và placement.**
- Trang chat: danh sách phiên, khung chat, trạng thái đang trả lời, xử lý lỗi và giới hạn tần suất, hiển thị rõ khi AI không dẫn nguồn (chưa RAG).
- Khi trả lời có `truncated: true`: hiển thị cho người học dòng "Câu trả lời có thể bị cắt, hãy hỏi tiếp để xem phần còn lại".
- Hiển thị đúng các mã lỗi giới hạn (Buổi 4) bằng thông điệp tiếng Việt và **đếm ngược theo header `Retry-After`** (khóa nút gửi đến khi hết giờ): `chat_rate_limited` (429), `chat_daily_limit_reached` (429, chờ đến nửa đêm giờ Việt Nam), `chat_busy` (409, tin trước chưa xong), `service_busy` (429, hệ thống bận), `auth_rate_limited` (429, trang đăng nhập/đăng ký). Phân biệt với các mã `llm_*`.
- Thông báo trên trang chat: nội dung chat được gửi tới Google Gemini; với gói miễn phí, Google có thể dùng nội dung để cải thiện sản phẩm và người đánh giá có thể đọc — không nhập thông tin cá nhân (căn cứ: mục điều khoản dữ liệu trong `docs/ENVIRONMENT_CHECK.md`).
- Trang placement: làm bài từng câu hoặc cả trang, nộp bài, xem kết quả, chủ đề yếu, nút xác nhận cập nhật trình độ theo quyết định ở Bước 2. Có dòng lưu ý không phải chứng chỉ CEFR.
- Dùng lớp client API duy nhất hiện có; giao diện tiếng Việt; không để lộ đáp án trong mã hay mạng.
- Kiểm chứng `npm run build`. Phần thao tác trên trình duyệt: nếu bạn không tự quan sát được thì **ghi rõ chưa kiểm chứng**, tôi sẽ tự thử và báo kết quả.

**Buổi 7 — Kiểm thử toàn tuyến và nghiệm thu.**
- Chạy toàn bộ `pytest`, `npm run build`, `alembic check`, hai script validate dữ liệu, quét secret (thư mục làm việc và lịch sử Git).
- Thử trên bản sao sạch theo README (như Tuần 2) nếu README thay đổi.
- Cập nhật README, `.env.example` (chỉ tên biến, không giá trị thật), `docs/ARCHITECTURE.md`, `docs/ENVIRONMENT_CHECK.md`.
- Lập bảng ĐẠT / CHƯA ĐẠT / CHƯA KIỂM CHỨNG kèm bằng chứng cho từng tiêu chí.

## Cổng chất lượng — áp dụng cho MỌI buổi (chưa qua thì chưa được báo hoàn thành)
1. Viết test **trước hoặc cùng lúc** với code cho logic thuần (chấm điểm, cắt lịch sử, giới hạn tần suất, ánh xạ lỗi).
2. Chạy toàn bộ `pytest` sau mỗi buổi; không để lỗi cũ hay cảnh báo mới không được giải thích.
3. **Kiểm tra độ chặt của test bằng cách cố ý làm hỏng code** ở ít nhất 2–3 chỗ quan trọng mỗi buổi (ví dụ bỏ kiểm tra chủ sở hữu phiên chat, đổi ngưỡng chấm điểm, để lộ đáp án), xác nhận test đỏ, rồi trả lại code. Nếu test không bắt được thì bổ sung test.
4. Mọi thay đổi schema DB: `alembic upgrade`, `alembic check`, thử `downgrade` rồi `upgrade` lại trên DB test; xin phép trước khi chạy trên DB chính.
5. Không gọi API thật trong test thông thường. Test không phụ thuộc thứ tự, không phụ thuộc mạng, không để lại dữ liệu trong DB.
6. Quét secret trước khi báo cáo: không key, token hay mật khẩu trong mã, log, báo cáo, hay Git.
7. Ghi bằng chứng vào `docs/ENVIRONMENT_CHECK.md` theo từng buổi: lệnh đã chạy, kết quả thật, phần **chưa kiểm chứng**. Phân biệt rõ "Claude đã chạy" với "người dùng tự báo".
8. Nếu một lệnh có nguy cơ mất dữ liệu, tốn tiền hoặc gửi dữ liệu ra ngoài: dừng và hỏi tôi.

## Quy tắc bắt buộc
- Python 3.13 trong `.venv`.
- Xin phép trước khi: cài dependencies, gọi API thật, sửa `.env`, chạy migration lên DB chính, xóa hoặc ghi đè file, dùng dịch vụ trả phí, commit, push.
- Không làm tính năng của tuần sau: **không RAG, không embedding, không Qdrant, không sinh bài tập, không dashboard**. Chỉ để lại điểm nối sạch (ví dụ chỗ chèn ngữ cảnh vào prompt) mà không cài đặt gì thêm.
- Module dùng chung không hardcode tiếng Anh hay CEFR; trình độ và prompt lấy theo `language_code`.
- Không hardcode credentials. Không tạo số liệu giả rồi trình bày như số liệu thật. Không nói đã hoàn thành nếu chưa kiểm chứng.

## Tiêu chí nghiệm thu Tuần 3
- Chat với AI trả lời bằng đúng ngôn ngữ và theo trình độ, lịch sử được lưu; người dùng không truy cập được phiên của người khác.
- Khi LLM lỗi, hết thời gian hoặc bị giới hạn: frontend nhận mã lỗi ổn định, không lộ chi tiết nội bộ, không treo.
- Placement chấm đúng theo đáp án đã duyệt, không bao giờ lộ đáp án trước khi nộp, ra trình độ đề xuất và chủ đề yếu.
- Giới hạn đăng nhập sai và giới hạn chat hoạt động, có test.
- Toàn bộ test chạy được **không cần mạng và không cần API key**; smoke test thật tách riêng, mặc định tắt, và đã chạy ít nhất một lần có báo cáo.
- Không có secret trong mã, log hay lịch sử Git; log không chứa nội dung tin nhắn.
- README và tài liệu thiết kế đã cập nhật; bản sao sạch chạy được theo README.

## Báo cáo cuối mỗi buổi
1. Việc đã hoàn thành. 2. File đã tạo hoặc sửa. 3. Lệnh chạy. 4. Kết quả kiểm thử thực tế (số test, kết quả thử làm hỏng code). 5. Phần chưa hoàn thiện hoặc chưa kiểm chứng. 6. Quyết định cần tôi đưa ra. 7. Việc tiếp theo.
