# Lumina — chat với backend Lab 07

Next.js / React / TypeScript, dùng logo và Lottie người dùng cung cấp. Chat gọi **agent Python thật**, truy xuất PostgreSQL/pgvector Day 6 và dùng cấu hình model hiện có trong `.env` gốc. Không có đáp án mẫu hoặc gold trong luồng chat.

## Chạy local

Chuẩn bị Python, PostgreSQL và index theo [src/README.md](../src/README.md). Dùng lại `.env` gốc; không sao chép khóa vào frontend.

Trong hai terminal:

```bash
# Terminal 1, từ thư mục web:
npm run backend       # Python API: 127.0.0.1:8007

# Terminal 2, từ thư mục web:
npm ci
npm run dev           # Next.js: 127.0.0.1:3007
```

Mở http://127.0.0.1:3007. Có thể dùng lại Next dev server đang chạy. Backend nạp bge-m3 ở câu hỏi đầu tiên, sau đó giữ model trong bộ nhớ; khi index cập nhật, nạp lại chunk/BM25 và dùng lại embedding model; chỉ nhận một lượt chat tại một thời điểm để phù hợp máy 16 GB. Nếu đang chạy benchmark/index riêng, tránh đồng thời nạp thêm model embedding.

Python chỉ bind loopback. Next proxy mặc định đến `http://127.0.0.1:8007`; có thể đổi bằng `LUMINA_BACKEND_URL` phía server. Đây là ứng dụng local, chưa có đăng nhập để triển khai công khai.

## Các chức năng đã nối

- Chat câu hỏi bất kỳ với streaming tiến trình tool thực: tìm nguồn, đọc trang, chuẩn bị context, gọi model. Câu trả lời xuất hiện khi tool `final_answer` hoàn tất; không giả lập token streaming.
- Theo dõi tối đa sáu tin nhắn trước (tổng tối đa 10.000 ký tự) để hiểu câu hỏi tiếp nối. Lịch sử không được coi là evidence; citation vẫn phải thuộc context lượt hiện tại.
- Dense, lexical (BM25 bigram), hybrid; top-k; context budget **ký tự**; số **bước model**; hybrid + LLM rerank; cho phép mở thêm chunk cùng trang. Advanced cho phép model xem ảnh crop gốc; basic dùng text index.
- Context hiển thị đúng phần text gửi model, kể cả chunk cuối bị cắt theo ngân sách. Ngân sách này không gồm prompt, lịch sử, metadata hay ảnh.
- Citation mở đúng trang PDF. Bảng Nguồn hiển thị crop gốc từ DB, loại nội dung, trang in và bbox. Luồng xử lý có query gốc, query bổ sung, rank và score.
- Mặc định trả lời bằng chữ, ảnh ở bảng Nguồn bên phải; nút “Xem ảnh nguồn” mở bảng này. Hỏi “Ông Trương Gia Bình giữ chức vụ gì?” không tự gửi ảnh. Nếu yêu cầu “Cho xem ảnh chân dung ông Trương Gia Bình”, model có thể chọn đúng crop PDF 37 (trang in 36) để đính kèm, ưu tiên 1 ảnh, tối đa 2. Bấm ảnh để mở PDF gốc.
- Chi phí, thời gian, token usage, điều kiện dừng và tải trace JSON theo từng hội thoại.
- Thư viện đọc ledger, số chunk và số embedding từ PostgreSQL; ô trang mở được PDF gốc.
- Lỗi backend được hiển thị, không trả đáp án mẫu. Nút Dừng gửi yêu cầu hủy, ngắt stream và chặn các bước tiếp theo; không thu hồi được lời gọi model đã gửi. Backend có thể cần chờ lời gọi đó kết thúc trước khi nhận câu mới.

UI sử dụng adapter riêng `src/web_api.py`, không chỉnh cấu hình benchmark đã đóng băng. Citation expansion không được bật trong chat. Hộp Context của adapter giữ đúng text đã cắt; điều này không tự sửa/chấm lại các kết quả CLI trước đó.

## API

| Next.js | Python | Vai trò |
|---|---|---|
| `POST /api/agent/chat` | `/chat` | JSON question/config/history → stream NDJSON |
| `POST /api/agent/cancel` | `/cancel` | Hủy theo run ID |
| `GET /api/agent/health` | `/health` | Trạng thái backend và index/ledger thật |
| `GET /api/agent/asset?chunk=...` | `/asset` | Crop tra bằng chunk ID; không nhận đường dẫn file |
| `GET /api/document` | — | Một PDF cố định, hỗ trợ byte-range và 416 |
| `GET /api/benchmark` | — | 240 câu chỉ gồm id/question/suite/split/category |

POST được kiểm tra origin, kiểu và kích thước JSON. Backend whitelist source/config, không nhận tool/system message qua lịch sử. API key và đường dẫn file nội bộ không được trả về trình duyệt. Markdown không render HTML thô hay ảnh từ model.

Tool `final_answer` của web có `image_selection` (trích yêu cầu hiện tại và chunk ID). Model hiểu nhu cầu xem ảnh trong cùng lượt trả lời; không thêm một lời gọi LLM để phân loại. Mặc định chọn rỗng; hỏi số liệu/tiểu sử hoặc phân tích biểu đồ không tự bật ảnh. Yêu cầu ảnh ở lượt trước không tự kéo sang lượt sau. `view_image` để model đọc ảnh, không phải gửi ảnh cho người dùng. Schema benchmark CLI giữ nguyên.

Backend kiểm tra lựa chọn và tách `trace.source_images` (tối đa 3 ảnh liên quan cho bảng Nguồn), `trace.answer_images` (tối đa 2 ảnh được chọn để đính kèm) và `trace.image_presentation` (quyết định hiển thị). Chân dung cần tên đầy đủ khớp giữa câu trả lời, context đã trích dẫn, tiêu đề vùng ảnh và văn bản gốc của cùng trang; không nhận diện bằng khuôn mặt hay tự lấy ảnh đầu tiên. Ảnh trong chat còn phải thuộc context model đã thấy. Caption nhiều người/thiếu tên, crop bị thiếu hoặc agent abstain đều không được đính kèm. Tính năng dùng được ở Basic và Advanced. Ảnh tải lỗi vẫn có nút mở trang gốc. Hội thoại cũ chưa có quyết định hiển thị được chuyển ảnh sang bảng Nguồn, không tự chèn lại vào chat.

Các ảnh bổ sung có nguồn riêng và được lưu/xuất cùng trace; không tự thêm vào `context`, `citations`, ngân sách context hay điểm benchmark. Không phải mọi ảnh chân dung trong PDF đều có metadata tên đủ rõ để tự ghép.

## Benchmark và bằng chứng lab

Phòng thử nghiệm vẫn nhập `summary.json` do evaluator tạo sau khi có nhãn người chấm:

```bash
# Từ thư mục gốc repo:
python3 benchmark/fpt_2025/tools.py score --suite advanced --split test \
  --traces /path/to/traces.json --reviews /path/to/reviews.json --output /path/to/summary.json
```

Chọn đúng suite/split và baseline/selected trước khi nhập. UI kiểm tra đủ ID, metric, tổng pass và nhãn review. Summary do người dùng cung cấp không phải xác minh độc lập.

Nút thử câu benchmark **gọi model thật**, nhưng không ghi điểm hoặc sửa gold. Không dùng test để tuning. Transcript chat có `purpose: interactive`, `demo: false`, `human_reviewed: false`, `not_for_benchmark_scoring: true`; chỉ dùng để demo/debug cho đến khi được đánh giá theo quy trình lab.

Hội thoại và trace lưu trong localStorage của trình duyệt. Dữ liệu demo cũ ở key v1 được giữ nguyên, không trộn vào chat thật v2. Các summary nhập chỉ giữ trong bộ nhớ màn hình.

## Kiểm tra

```bash
# Từ web; không mở trình duyệt:
npm run typecheck
npm test
npm run check:api     # cần Next dev server; không gọi model
npm run build

# Từ gốc repo; không gọi API model:
.venv/bin/python -m unittest discover -s tests -v
```

Smoke test có model được chạy riêng qua HTTP, không tự động nằm trong `npm test`. Người dùng tự kiểm tra giao diện.

PDF tại `pdf/BCTN_2025_ad403f779b.pdf`; preview sáu trang có thể tái tạo bằng `.venv/bin/python web/scripts/prepare_previews.py` từ gốc repo. Crop của index được tạo bởi pipeline multimodal. PDF và ảnh dẫn xuất giữ local.

Logo cũng dùng làm favicon. `predev/prebuild` trích animation từ `public/animations/animation.lottie` qua Python stdlib; player tôn trọng `prefers-reduced-motion`. Xem [credits](public/animations/CREDITS.md).
