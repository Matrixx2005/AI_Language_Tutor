# AI Language Tutor

Hệ thống hỗ trợ học tiếng Anh A1–B1 cho người Việt, dùng Retrieval-Augmented Generation (BM25 + BGE-M3 + RRF), Gemini Flash và cá nhân hóa học tập. Đồ án tốt nghiệp Khoa học máy tính.

**Trạng thái:** Tuần 4 — RAG: chat có ba chế độ `llm_only` / `dense` (BGE-M3 + Qdrant) / `hybrid` (BM25 + dense + RRF), trích dẫn nguồn [n] đã kiểm tra, số đo truy xuất thật trên dev (`experiments/README.md`). Nghiệm thu: [`docs/WEEK4_ACCEPTANCE.md`](docs/WEEK4_ACCEPTANCE.md), [`docs/WEEK3_ACCEPTANCE.md`](docs/WEEK3_ACCEPTANCE.md). Kế hoạch: [`docs/PROJECT_MASTER_PLAN.md`](docs/PROJECT_MASTER_PLAN.md).

Hướng dẫn dưới đây viết cho **Windows + PowerShell**, chạy từ thư mục gốc dự án trừ khi ghi khác. Làm lần lượt từ bước 1 đến bước 7.

## Yêu cầu

| Công cụ | Phiên bản đã kiểm chứng | Kiểm tra |
| --- | --- | --- |
| Python | **3.13** (3.13.11) | `py -0p` |
| Node.js + npm | Node 24 (v24.15.0), npm 11. **`npm test` cần Node ≥ 22.18** (chạy trực tiếp file `.ts` không cần cờ; Node 23.6+ cũng được) | `node --version` |
| Docker Desktop (WSL 2) | Docker 29.9, Compose v5.7 | `docker compose version` |
| Git | 2.x | `git --version` |

Docker Desktop cần WSL 2: chạy `wsl --install` trong PowerShell (Run as Administrator), khởi động lại máy, rồi cài Docker Desktop.

## 1. Môi trường Python

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
```

`requirements.txt` là gói khi chạy app; `requirements-dev.txt` thêm gói kiểm thử. Mọi phiên bản đều được ghim chính xác.

## 2. Biến môi trường (`.env`)

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(24))"   # → dán vào POSTGRES_PASSWORD
python -c "import secrets; print(secrets.token_urlsafe(64))"   # → dán vào JWT_SECRET
```

Mở `.env`, điền hai giá trị trên. `.env` đã nằm trong `.gitignore` — **không bao giờ commit file này**.

| Biến | Bắt buộc | Ý nghĩa / cách đặt |
| --- | --- | --- |
| `ENVIRONMENT` | không (mặc định `development`) | `development` bật CORS cho Vite `localhost:5173`; giá trị khác tắt CORS (trừ khi đặt `CORS_ORIGINS`) |
| `CORS_ORIGINS` | không | Origin được phép gọi API, cách nhau bằng dấu phẩy (ví dụ tên miền thật khi triển khai). Không chấp nhận `*` |
| `POSTGRES_HOST` | không (mặc định `127.0.0.1`) | Dùng `127.0.0.1`, **không** dùng `localhost` (xem Xử lý sự cố) |
| `POSTGRES_PORT` | không (mặc định `5432`) | Đổi nếu cổng 5432 đã bị chiếm |
| `POSTGRES_USER` | có | Tên user DB, ví dụ `tutor` |
| `POSTGRES_PASSWORD` | **có** | Chuỗi ngẫu nhiên (lệnh ở trên) |
| `POSTGRES_DB` | có | DB chính, ví dụ `ai_language_tutor` |
| `POSTGRES_TEST_DB` | có | DB cho pytest, ví dụ `ai_language_tutor_test` (phải khác `POSTGRES_DB`) |
| `POSTGRES_CONNECT_TIMEOUT` | không (mặc định `10`) | Số giây chờ kết nối DB trước khi báo lỗi |
| `JWT_SECRET` | **có** | Chuỗi ngẫu nhiên ≥ 32 ký tự (lệnh ở trên). Thiếu hoặc ngắn hơn → backend không khởi động |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | không (mặc định `60`) | Thời hạn token đăng nhập, 1–1440 phút |
| `DEFAULT_LANGUAGE_CODE` | không (mặc định `en`) | Ngôn ngữ học của tài khoản mới; phải có `languages/<code>.yaml` |
| `LLM_PROVIDER` | không (mặc định `fake`) | `fake` = trả lời giả, không mạng, không tốn hạn mức (lượt `fake` không tính vào giới hạn ngày/toàn hệ thống, lưu `model_id` dạng `fake:...`); `gemini` = gọi Gemini thật (xem mục "Bật LLM thật"). Đổi sang `gemini` thì tạo cuộc trò chuyện mới |
| `LLM_MODEL_ID` | khi `LLM_PROVIDER=gemini` | Model chính. Đã kiểm chứng: `gemini-3.5-flash-lite`. Không dùng alias `*-latest` |
| `LLM_FALLBACK_MODEL_IDS` | không | Model dự phòng khi model chính hết hạn mức/quá tải, cách nhau bằng dấu phẩy (ví dụ `gemini-3.8-flash`) |
| `LLM_TIMEOUT_SECONDS` | không (mặc định `30`) | Thời gian chờ mỗi lần gọi, 1–120 giây |
| `LLM_MAX_RETRIES` | không (mặc định `1`) | Số lần thử lại cho lỗi tạm thời, 0–3 (ít để tiết kiệm hạn mức) |
| `LLM_MAX_OUTPUT_TOKENS` | không (mặc định `1024`) | Giới hạn token trả lời (gồm cả token "suy nghĩ" của Gemini) |
| `GEMINI_THINKING_LEVEL` | không (mặc định `low`) | `minimal` / `low` / `medium` / `high`, để trống = mặc định của model |
| `GEMINI_API_KEY` | khi `LLM_PROVIDER=gemini` | Tạo tại Google AI Studio. **Chỉ đặt trong `.env`**, không bao giờ trong `.env.example` hay mã nguồn |
| `CHAT_HISTORY_TURNS` | không (mặc định `10`) | Số lượt gần nhất gửi cho LLM (1 lượt = câu hỏi + trả lời; lượt lỗi không gửi), 0–50 |
| `CHAT_MAX_MESSAGE_CHARS` | không (mặc định `2000`) | Độ dài tối đa mỗi tin người dùng, 1–10000 ký tự; dài hơn → `422 message_too_long` |
| `CHAT_USER_PER_MINUTE` | không (mặc định `6`) | Tin chat mỗi phút mỗi người; vượt → `429 chat_rate_limited`. `0` = tắt |
| `CHAT_USER_PER_DAY` | không (mặc định `40`) | Tin chat mỗi ngày (theo `USER_TIMEZONE`) mỗi người; vượt → `429 chat_daily_limit_reached`. Lượt hỏng do hệ thống không tính |
| `CHAT_MAX_CONCURRENT_PER_USER` | không (mặc định `1`) | Số tin chờ trả lời cùng lúc mỗi người; vượt → `409 chat_busy` |
| `LLM_GLOBAL_PER_MINUTE` | không (mặc định `10`) | Số **request chat** mỗi phút **toàn hệ thống** (một key chung); vượt → `429 service_busy`. Một request có thể gây tối đa (1 + `LLM_MAX_RETRIES`) × số model lời gọi thật; điểm xuất phát khuyến nghị: 15 ÷ (1 + `LLM_MAX_RETRIES`) |
| `LLM_GLOBAL_PER_DAY` | không (mặc định `0` = tắt) | Lượt gọi LLM mỗi ngày toàn hệ thống. Đặt thấp hơn RPD thật trong AI Studio |
| `LLM_QUOTA_COOLDOWN_SECONDS` | không (mặc định `900`) | Khi nhà cung cấp báo hết hạn mức NGÀY: tạm khóa gọi LLM toàn hệ thống (60–3600 giây; `0` = như giới hạn theo phút, tối đa 60 giây). Trong lúc khóa, chat trả `429 service_busy` kèm Retry-After |
| `AUTH_LOGIN_FAILS_PER_EMAIL`, `AUTH_LOGIN_FAILS_PER_IP` | không (`5`, `20`) | Số lần đăng nhập sai trong cửa sổ; vượt → `429 auth_rate_limited` |
| `AUTH_LOGIN_WINDOW_SECONDS` | không (`900`) | Cửa sổ đếm đăng nhập sai, 60–86400 giây |
| `AUTH_REGISTER_PER_IP_PER_HOUR` | không (`10`) | Số lần đăng ký mỗi giờ mỗi IP |
| `USER_TIMEZONE` | không (`Asia/Ho_Chi_Minh`) | Ranh giới "ngày" cho giới hạn theo ngày |
| `TRUSTED_PROXY_COUNT` | không (`0`) | Số proxy tin cậy; `0` = không đọc `X-Forwarded-For`. Chỉ đổi khi triển khai sau proxy (Tuần 8) |
| `EMBEDDING_MODEL`, `QDRANT_URL` | chưa dùng | Dành cho Tuần 4 |

Frontend (tùy chọn): `frontend/.env.example` có `VITE_API_BASE_URL` (mặc định `http://127.0.0.1:8000/api/v1`). Chỉ cần tạo `frontend/.env.local` khi đổi địa chỉ backend. Biến `VITE_*` bị nhúng vào trang web công khai — không đặt secret ở đó.

## 3. PostgreSQL (Docker)

```powershell
docker compose up -d --wait        # PostgreSQL + Qdrant; lần đầu tải image postgres:18-alpine (~100 MB) và qdrant/qdrant:v1.20.2 (~74 MB)
docker compose ps                  # postgres và qdrant: Up ... (healthy)
```

- Lần khởi tạo đầu tiên tự tạo cả DB chính và DB test (`docker/postgres/init/`).
- Dữ liệu nằm trong volume Docker `pgdata`, còn nguyên khi tắt máy. `docker compose down` dừng DB và **giữ** dữ liệu; `docker compose down -v` **xóa toàn bộ dữ liệu**.
- Mật khẩu chỉ được áp dụng khi volume còn trống. Đổi `POSTGRES_PASSWORD` sau lần chạy đầu sẽ không đổi mật khẩu trong DB (phải đổi bằng SQL, hoặc `down -v` nếu chấp nhận mất dữ liệu).

## 4. Migration

Chạy từ thư mục `backend/`:

```powershell
cd backend
alembic upgrade head               # DB chính
alembic -x db=test upgrade head    # DB test (cần cho pytest)
alembic current                    # → a4c9e2f17b30 (head)
cd ..
```

Xem trước SQL mà không chạm DB: `alembic upgrade head --sql`.

Nạp ngân hàng câu hỏi placement (kiểm tra dữ liệu trước, nạp lại không tạo bản trùng, không sửa file nguồn):

```powershell
python scripts/load_placement.py --target main --dry-run   # xem trước
python scripts/load_placement.py --target main             # DB chính
```

Test tự nạp câu hỏi vào DB test trong transaction rồi rollback, không cần chạy lệnh này cho DB test.

## 5. Backend

```powershell
uvicorn app.main:app --app-dir backend --reload --reload-dir backend
```

- http://127.0.0.1:8000/docs — thử API (có sẵn ví dụ hợp lệ; sau khi đăng nhập bấm **Authorize** và dán `access_token`).
- http://127.0.0.1:8000/health → `{"status":"ok"}`.
- Địa chỉ gốc http://127.0.0.1:8000 tự chuyển sang `/docs` (backend chỉ là API, không có trang riêng).

| API | Mô tả |
| --- | --- |
| `POST /api/v1/auth/register` | Tạo tài khoản + hồ sơ. Mật khẩu 8–128 ký tự, không trùng email |
| `POST /api/v1/auth/login` | Trả `access_token` (Bearer) |
| `GET /api/v1/profile/me` | Xem hồ sơ của mình (cần token) |
| `PATCH /api/v1/profile/me` | Sửa tên hiển thị, mục tiêu, trình độ (A1/A2/B1) |
| `GET /api/v1/languages/{code}` | Danh sách trình độ hợp lệ từ `languages/<code>.yaml` (không cần token) |
| `POST /api/v1/placement/attempts` | Bắt đầu bài kiểm tra đầu vào (30 câu, **không kèm đáp án**); đang có lượt dở → trả lại lượt đó |
| `GET /api/v1/placement/attempts`, `GET .../attempts/{id}` | Lịch sử và chi tiết lượt của mình (đáp án, giải thích chỉ có sau khi nộp) |
| `POST .../attempts/{id}/submit` | Nộp một lần (lần hai → `409`); chấm phía máy chủ, không dùng LLM; trả trình độ **đề xuất**, nhóm yếu, chủ đề cần ôn |
| `POST .../attempts/{id}/apply` | Người dùng xác nhận → cập nhật trình độ trong hồ sơ |

### Bật LLM thật (Gemini)

Mặc định `LLM_PROVIDER=fake`: không gọi mạng. Để dùng Gemini thật:

1. Tạo API key tại Google AI Studio. Đặt vào `.env` (dòng `GEMINI_API_KEY=...`) — **không** dán vào `.env.example`, chat, issue hay mã nguồn.
2. Trong `.env`, đặt `LLM_PROVIDER=gemini`, `LLM_MODEL_ID=gemini-3.5-flash-lite`, `LLM_FALLBACK_MODEL_IDS=gemini-3.8-flash`, `GEMINI_THINKING_LEVEL=low`.
3. Kiểm tra bằng **một** lời gọi thật (smoke test, mặc định bị bỏ qua):

   ```powershell
   $env:RUN_LLM_SMOKE = "1"; $env:LLM_SMOKE_CASE = "text"   # hoặc "structured"
   $env:PYTHONIOENCODING = "utf-8"   # để in được câu trả lời tiếng Việt khi chuyển hướng/ghi ra file
   pytest backend/tests/test_llm_smoke.py -s
   Remove-Item Env:RUN_LLM_SMOKE, Env:LLM_SMOKE_CASE, Env:PYTHONIOENCODING
   ```

Lưu ý gói miễn phí: Google có thể dùng nội dung gửi lên để cải thiện sản phẩm và người đánh giá có thể đọc nội dung đó; không gửi thông tin cá nhân. Chi tiết và nguồn: `docs/ENVIRONMENT_CHECK.md` (mục điều khoản dữ liệu). Hạn mức thật xem trong AI Studio (tài liệu không công bố con số cố định).

### RAG — truy xuất bài ngữ pháp (Tuần 4)

Chạy được trên **CPU** (không cần CUDA). Đã đo trên Core Ultra 7 155H: nhúng 1 truy vấn khoảng 60–110 ms, RAM khoảng 2,1 GB.

1. **Gói Python:** đã có trong `backend/requirements.txt` (torch bản CPU từ index riêng của PyTorch, sentence-transformers, qdrant-client). Bước 1 đã cài; tải khoảng 225 MB.
2. **Qdrant:** service `qdrant` trong `docker-compose.yml`, image ghim `v1.20.2`, chỉ mở `127.0.0.1:6333`, volume `qdrantdata`. Bước 3 đã khởi động; kiểm tra bằng http://127.0.0.1:6333/ (trả về `"version":"1.20.2"`).
3. **Tải model BGE-M3** (khoảng 2,3 GB, ghim revision, bỏ thư mục `onnx/`) vào `models/hf`. Thư mục này đã nằm trong `.gitignore`; đổi chỗ bằng `EMBEDDING_CACHE_DIR`.

   ```powershell
   python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-m3', revision='5617a9f61b028005a4858fdac845db406aefb181', cache_dir='models/hf', ignore_patterns=['onnx/*', 'imgs/*'])"
   ```

4. **Nạp index** (idempotent: chạy lại chỉ nhúng lại bài đã đổi; đổi model thì thêm `--recreate`):

   ```powershell
   python scripts/index_corpus.py                  # theo RAG_INDEX_KEYWORDS_VI; --keywords both để nạp cả hai cấu hình
   ```

5. **Bật RAG:** đặt `RAG_MODE=hybrid` (hoặc `dense`) trong `.env` rồi khởi động lại backend. Không đặt thì mặc định là `llm_only`. Trên giao diện chat vẫn chọn được chế độ cho từng tin.
   - Nếu Qdrant, model hoặc index lỗi, chat **không chết**: câu trả lời chuyển sang `llm_only` và có ghi chú "Không truy xuất được tài liệu".
   - Lần hỏi RAG đầu tiên sau khi khởi động mất khoảng 10–15 giây để tải model.
6. **Đánh giá truy xuất** (chỉ dev split; test split bị từ chối nếu không có cờ riêng):

   ```powershell
   python scripts/eval_retrieval.py --keywords both --note "lý do chạy"   # bộ v1 (30 truy vấn); kết quả vào experiments/
   python scripts/eval_retrieval.py --queries v2 --keywords both --note "…"  # bộ v2 (109 truy vấn) + bootstrap, nhóm expected=none
   python scripts/bench_bge_m3.py --runs 3                               # đo BGE-M3 trên CPU
   ```

7. **Smoke test có tài nguyên thật** (mặc định bỏ qua): `$env:RUN_RAG_SMOKE = "1"` để chạy phần truy xuất thật; thêm `$env:RUN_RAG_SMOKE_LLM = "1"` để gọi Gemini thật (2 lời gọi).

Biến môi trường mới (đều có mặc định): `RAG_MODE`, `RAG_TOP_K`, `RAG_RRF_K`, `RAG_CANDIDATES`, `RAG_INDEX_KEYWORDS_VI`, `RAG_FILTER_LEVEL`, `EMBEDDING_MODEL_REVISION`, `EMBEDDING_CACHE_DIR`, `QDRANT_TIMEOUT_SECONDS`. Ý nghĩa của từng biến xem trong `.env.example`.

## 6. Frontend

Mở terminal thứ hai:

```powershell
cd frontend
npm ci                             # cài đúng phiên bản trong package-lock.json
npm run dev                        # → http://localhost:5173 (hoặc http://127.0.0.1:5173)
```

Giao diện tiếng Việt: đăng ký → đăng nhập → hồ sơ (chọn trình độ từ danh sách) → đăng xuất. Token lưu trong `sessionStorage` (mất khi đóng tab). Vite được ghim cổng 5173: nếu cổng bận, lệnh báo lỗi thay vì tự đổi sang cổng khác (cổng khác sẽ bị CORS chặn).

| Trang | Nội dung |
| --- | --- |
| `/chat` — **Gia sư AI** | Danh sách cuộc trò chuyện, khung chat (Enter gửi, Shift+Enter xuống dòng), đếm ký tự, tin hiện ngay khi gửi, "Thử lại" khi lỗi, đếm ngược khi bị giới hạn tần suất |
| `/placement` — **Kiểm tra đầu vào** | 30 câu trên một trang, tiến độ "Đã trả lời X/30", nộp bài (hỏi lại nếu còn câu trống), kết quả, nhóm yếu, chủ đề cần ôn, xem lại đáp án, nút "Dùng trình độ này" |

**Làm giao diện mà không tốn hạn mức Gemini:** đặt `LLM_PROVIDER=fake` trong `.env` rồi khởi động lại backend. Gia sư trả một câu cố định (`Đây là câu trả lời thử nghiệm từ FakeLLM…`), không gọi mạng; lượt `fake` không tính vào giới hạn ngày (vẫn tính giới hạn 6 tin/phút). Placement không dùng AI nên chạy giống hệt ở cả hai chế độ.

**Bật Gemini thật:** đặt `LLM_PROVIDER=gemini` (cùng các dòng ở mục "Bật LLM thật"), khởi động lại backend, rồi **tạo cuộc trò chuyện mới** (để lịch sử không chứa câu trả lời giả).

**Kiểm thử logic giao diện** (không cần backend, không thêm thư viện — dùng `node:test` có sẵn; Node 24 chạy trực tiếp file `.ts`):

```powershell
cd frontend
npm test                           # = node --test tests/*.test.ts
```

Các test nằm trong `frontend/tests/` và kiểm các hàm thuần ở `src/lib/` (đọc `Retry-After`, định dạng thời gian chờ, mã lỗi, gộp lượt chat đã thử lại, chọn phiên, lượt placement mới nhất…). Giao diện React (bấm, gõ, bố cục) **không** được test tự động — cần thử trên trình duyệt.

## 6b. Streamlit test console (Tuần 5A)

Bảng điều khiển để thử và trình bày, gồm 7 trang:
- Tài khoản;
- Chat (chọn chế độ, xem nguồn, trích dẫn, hạ cấp, độ trễ);
- Kiểm tra đầu vào;
- Retrieval Lab (BM25 | Dense | Hybrid song song, truy vấn mẫu **chỉ từ dev**);
- Thí nghiệm (đọc `experiments/`);
- Corpus;
- Hệ thống.

Đây là lớp mỏng: mọi nghiệp vụ đi qua REST API. Riêng Retrieval Lab import trực tiếp `backend/app/retrieval`. Câu trả lời của AI được hiển thị **nguyên văn**, không render HTML.

### Chạy Streamlit

```powershell
pip install -r streamlit_app/requirements.txt          # streamlit 1.67.0, pandas 3.1.1 (đã cài ở Tuần 5A)
# Backend phải đang chạy (mục 5); Retrieval Lab cần thêm Qdrant + index (mục RAG).
streamlit run streamlit_app/app.py --server.address 127.0.0.1 --server.port 8501
```

Mở http://127.0.0.1:8501. Nếu backend tắt, các trang báo "Không kết nối được backend…" chứ không sập.

Console đọc **biến môi trường của shell**, không đọc `.env`. Có 3 biến (tên đã có trong `.env.example`):

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `STREAMLIT_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | Địa chỉ API mà console gọi |
| `STREAMLIT_ACCESS_CODE` | (trống = tắt) | Bắt nhập mã trước **mọi** trang (so sánh hằng thời gian). Không đặt mã trong mã nguồn hay Git |
| `STREAMLIT_PUBLIC_MODE` | `false` | `true`: chặn chat nếu backend đang dùng Gemini, ẩn cấu hình ở trang Hệ thống |

```powershell
$env:STREAMLIT_ACCESS_CODE = "<mã bạn tự đặt>"; $env:STREAMLIT_PUBLIC_MODE = "true"
streamlit run streamlit_app/app.py --server.address 127.0.0.1 --server.port 8501
```

### Chia sẻ tạm thời (cloudflared, bản miễn phí)

`cloudflared` đã được cài (2026.11.2). Quick tunnel không cần tài khoản.

1. **Chỉ tunnel cổng 8501 (Streamlit). KHÔNG BAO GIỜ tunnel backend (cổng 8000), PostgreSQL hay Qdrant.**
2. Trước khi chia sẻ:
   - đặt `STREAMLIT_ACCESS_CODE`;
   - đặt `STREAMLIT_PUBLIC_MODE=true`;
   - chạy backend với `LLM_PROVIDER=fake`. Ở chế độ công khai, nếu backend dùng Gemini thì chat bị chặn, để người lạ không tiêu hết hạn mức Gemini miễn phí (500 lượt/ngày của cả app).
3. Chạy `cloudflared tunnel --url http://127.0.0.1:8501`, rồi gửi link `https://….trycloudflare.com` kèm mã truy cập (gửi mã riêng, không gửi chung với link).
4. Xong thì nhấn Ctrl+C để tắt tunnel; link hết hiệu lực ngay. Mỗi lần chạy lại sẽ có link mới.
5. Mọi người dùng chung một backend: tài khoản và chat của họ được lưu vào DB chính của bạn. Không chia sẻ khi có dữ liệu thật cần giữ riêng.

### Vì sao không dùng Streamlit Community Cloud cho toàn hệ thống

- Giới hạn bộ nhớ khoảng 1 GB, trong khi BGE-M3 cần khoảng 2,1 GB RAM (đo ở Tuần 4).
- Không chạy được PostgreSQL và Qdrant ở đó; ứng dụng còn cần backend FastAPI chạy liên tục.
- Phải đưa key Gemini và secret lên dịch vụ bên ngoài.

→ Chạy tại máy và chia sẻ tạm thời qua tunnel như trên. Triển khai thật để dành cho Tuần 8.

## 7. Kiểm thử

```powershell
pytest                                     # cần DB đang chạy và DB test đã migrate (bước 3–4)
python scripts/validate_dataset.py         # dataset ngữ pháp
python scripts/validate_evaluation.py      # bộ đánh giá placement/RAG
cd frontend; npm test; npm run build; cd ..   # logic giao diện (Node ≥ 22.18) + TypeScript/build
```

- `backend/tests/test_e2e_week3.py`: luồng đầu-cuối qua HTTP (đăng ký → chat → lịch sử; chặn truy cập phiên/lượt của người khác; giới hạn chat và đăng nhập; placement start → nộp → áp dụng; lỗi LLM giả lập).

- Test API chạy trên **DB test**, mỗi test tự rollback: không đụng dữ liệu thật.
- Nếu PostgreSQL chưa chạy, các test cần DB được **bỏ qua** (skipped) thay vì treo; nếu DB test chưa migrate, pytest báo lỗi kèm lệnh cần chạy.
- Test LLM **không cần mạng và không cần key**: dùng `FakeLLM` và SDK Gemini với HTTP giả. Smoke test gọi API thật luôn bị bỏ qua trừ khi đặt `RUN_LLM_SMOKE=1`.

## Xử lý sự cố

| Hiện tượng | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| Kết nối DB chậm ~8 giây hoặc treo | `localhost` trên Windows thử IPv6 `::1` trước, Docker chỉ mở IPv4 | Đặt `POSTGRES_HOST=127.0.0.1` |
| Backend không khởi động: `JWT_SECRET chưa được đặt` | Thiếu hoặc secret < 32 ký tự | Sinh lại theo bước 2 |
| `422 Unprocessable Content` | Dữ liệu gửi lên chưa hợp lệ | Terminal backend ghi ô bị lỗi (`-> password: value_error`); lý do chi tiết ở Response body trên `/docs` |
| `401` sau một thời gian dùng | Token hết hạn (mặc định 60 phút) | Đăng nhập lại |
| `docker compose up` báo cổng 5432 đã dùng | Có PostgreSQL khác trên máy | Đổi `POSTGRES_PORT` trong `.env` |
| `npm run dev`: `Port 5173 is already in use` | Một Vite khác (hoặc ứng dụng khác) đang dùng cổng | Tắt tiến trình đó; nếu buộc phải đổi cổng, sửa `frontend/vite.config.ts` và thêm origin mới vào `CORS_ORIGINS` |
| Trình duyệt báo lỗi CORS | Frontend không chạy ở `localhost:5173`/`127.0.0.1:5173`, hoặc `ENVIRONMENT` khác `development` | Chạy `npm run dev` mặc định; kiểm tra `ENVIRONMENT`, hoặc thêm origin vào `CORS_ORIGINS` |

## Cấu trúc

| Thư mục | Nội dung |
| --- | --- |
| `backend/app/` | FastAPI: `core/` (cấu hình, bảo mật, lỗi), `db/`, `models/`, `schemas/`, `services/`, `api/` |
| `backend/alembic/` | Migration cơ sở dữ liệu |
| `backend/app/retrieval/` | RAG: tokenizer, BM25, dense (Qdrant), RRF, hybrid, chunker, kiểm tra trích dẫn |
| `backend/tests/` | pytest (API, ràng buộc DB, dataset, luồng đầu-cuối, truy xuất) |
| `experiments/` | Số đo thật: BGE-M3 trên CPU, Recall@K/MRR trên dev (v1, v2 kèm bootstrap) |
| `streamlit_app/` | Streamlit test console (7 trang), client REST `api.py`, hàm thuần `logic.py` |
| `frontend/tests/` | `npm test`: logic thuần của giao diện (`node:test`) |
| `frontend/` | Vite + React + TypeScript + Tailwind |
| `languages/` | Cấu hình ngôn ngữ và trình độ (`en.yaml`) |
| `data/` | Dataset ngữ pháp, bộ đánh giá; `data/archive/` là bản gốc không sửa |
| `docs/` | Kế hoạch, kiến trúc, thiết kế DB, nhật ký kiểm chứng môi trường |
| `scripts/` | Kiểm tra môi trường, validate dữ liệu |
| `docker/` | Script khởi tạo PostgreSQL |
