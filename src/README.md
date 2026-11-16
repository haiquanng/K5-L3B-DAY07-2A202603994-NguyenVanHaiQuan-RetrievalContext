# Code Day 7 — Agentic RAG đa phương thức trên báo cáo thường niên FPT 2025

Toàn bộ chạy từ thư mục gốc repo với Python 3.12. Vector store là container PostgreSQL + pgvector của Day 6;
embedding là model Day 6 (`BAAI/bge-m3`, revision `5617a9f61b02`, 1024 chiều) nên vector query tương thích index.

| File | Vai trò |
| --- | --- |
| `mm/layout.py` | PyMuPDF: text block, bảng/ảnh/cụm vector kèm bbox; lọc thanh mục lục, header lặp, số trang; lưu `pdf_page` và `printed_page`; render trang, crop PNG |
| `mm/vision.py` | Vision model gom block id thành vùng bảng/biểu đồ/sơ đồ/infographic/ảnh và mô tả hình; cache theo trang |
| `mm/index.py` | Dựng chunk (text nguyên văn từ PDF), bbox từ object PDF, kiểm số liệu mô tả với text layer, embed, ghi DB |
| `mm/schema.sql`, `mm/store.py` | Bảng `mm_documents → mm_pages → mm_regions → mm_chunks → mm_embeddings` (+ `tsvector`) |
| `embeddings.py` | bge-m3 của Day 6 |
| `retrieval.py` | `dense` (pgvector), `bm25`, `bm25_bigram`, `hybrid` (RRF), `rerank` (hybrid top-20 chấm lại bằng LLM) |
| `eval_retrieval.py` | So sánh retrieval trên dev bằng nhãn proxy tự động |
| `agent.py` | Agent tool-calling (search, open_page, view_image, final_answer), kiểm tra citation, trace |
| `run_agent.py` | Chạy agent trên một split, xuất trace theo định dạng `benchmark/fpt_2025/tools.py score` + tóm tắt proxy |

## 1. Chuẩn bị

```bash
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -r requirements.txt   # hoặc python -m venv + pip
cp .env.example .env                       # điền OPENAI_API_KEY; DATABASE_URL trỏ container Day 6
# trong repo Day 6, thư mục starter/:
docker compose -p day6_student_starter up -d --wait
```

PDF nguồn không nằm trong repo (`pdf/` bị ignore vì không có quyền tái phân phối). Tải từ
[trang báo cáo thường niên FPT](https://fpt.com/vi/nha-dau-tu/bao-cao-thuong-nien), đặt tại
`pdf/BCTN_2025_ad403f779b.pdf` và kiểm tra SHA-256 trong `benchmark/fpt_2025/source.json`.

Máy 16 GB: chỉ chạy **một** tiến trình có model local tại một thời điểm; agent dùng 3 luồng.

## 2. Index (một lần, ~$1.7 vision + ~2 phút embed local)

```bash
.venv/bin/python -m src.mm.index index --pdf pdf/BCTN_2025_ad403f779b.pdf \
    --doc-id fpt-ar2025 --title "Báo cáo thường niên FPT 2025"
.venv/bin/python -m src.mm.index show --doc-id fpt-ar2025 --page 10      # xem chunk + log một trang
.venv/bin/python -m src.mm.index search --doc-id fpt-ar2025 "Doanh thu năm 2023"
```

Kết quả: `starter/results/mm/fpt-ar2025/` (`index_stats.json`, `pages|regions|chunks.jsonl`);
ảnh trang/crop và cache vision ở `starter/data/mm/fpt-ar2025/`. Chạy lại dùng cache vision và chỉ embed
chunk có nội dung đổi.

## 3. Retrieval trên dev

```bash
.venv/bin/python -m src.eval_retrieval --suite advanced --split dev --methods dense bm25 bm25_bigram hybrid rerank
```

Retrieval chỉ nhận câu hỏi gốc. Nhãn trong file này là **proxy tự động** (cùng trang gold và khớp ≥1/2 quote
hoặc phủ ≥1/2 bbox gold), chỉ dùng để chọn cấu hình trên dev.

## 4. Agent

```bash
.venv/bin/python -m src.run_agent --suite advanced --split dev --name baseline --method hybrid --top-k 5
.venv/bin/python -m src.run_agent --suite advanced --split dev --name c2 --prompt v2 --view-image
```

Agent chỉ nhận `queries/*.json` (id + câu hỏi). Gold chỉ được đọc sau khi agent xong, để tính proxy và
LLM judge hỗ trợ. Kết quả: `starter/results/agent/<suite>.<split>.<name>/traces.json` và `auto.json`.
`--split test` bị chặn trừ khi thêm `--allow-test`, chỉ dùng sau khi đã chốt cấu hình trên dev.

## 5. Chấm test (người chấm)

```bash
python3 benchmark/fpt_2025/tools.py review-template --suite advanced --split test --output reviews.json
python3 benchmark/fpt_2025/tools.py score --suite advanced --split test \
    --traces starter/results/agent/advanced.test.<name>/traces.json --reviews reviews.json --output summary.json
```

## 6. Kiểm thử

```bash
.venv/bin/python -m unittest discover -s tests -v      # không cần model, DB hay API
```
