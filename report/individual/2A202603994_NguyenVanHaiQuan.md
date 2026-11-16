# Báo cáo Day 7 — Nguyễn Văn Hải Quân (2A202603994)

> Số liệu dev/test dưới đây là **proxy tự động + LLM judge** (xem định nghĩa ở mục Đánh giá), dùng để chọn cấu hình.
> Kết quả test chính thức theo `benchmark/fpt_2025/tools.py score` cần **nhãn người chấm**; chưa có tại thời điểm nộp.

## Dữ liệu và benchmark

- **Nguồn:** Báo cáo thường niên FPT 2025, 232 trang PDF, SHA-256 `9449a725…0e6c` ([trang công bố](https://fpt.com/vi/nha-dau-tu/bao-cao-thuong-nien)).
  Tài liệu công khai nhưng không có quyền tái phân phối → `pdf/` không nằm trong repo; `benchmark/fpt_2025/source.json` ghi hash và cách lấy.
- **Index:** 232/232 trang có ledger (229 trang có chunk; 3 trang mở chương chỉ có tên chương/ảnh nền, có lý do);
  337 vùng (bảng 140, ảnh 103, infographic 66, biểu đồ 23, sơ đồ 5), **723 chunk**, trung vị 904 ký tự.
  Mỗi chunk giữ `pdf_page`, `printed_page` (in = PDF − 1), bbox (PDF points) và ảnh crop PNG của vùng gốc.
- **Vector store / embedding:** container PostgreSQL 16 + pgvector 0.8.7 của Day 6; `BAAI/bge-m3` revision `5617a9f61b02`,
  1024 chiều, chuẩn hoá L2, cosine chính xác (không ANN). Bảng mới `mm_*` (documents → pages → regions → chunks → embeddings), có `tsvector` cho lexical.
- **Agent:** `gpt-5.4-mini` (reasoning low, OpenAI Responses API). Lệnh chạy ở [src/README.md](../../src/README.md).
- **Benchmark (tự soạn):** 240 câu + 60 ca hệ thống. Basic: dev 40+10, test 40+10; advanced: dev 56+14, test 56+14
  (có đáp án + thiếu evidence). Gold chỉ nằm ở `gold/` cho evaluator; agent chỉ nhận `queries/` (id + câu hỏi).
- **Có/thiếu evidence:** câu thiếu evidence được kiểm toàn văn theo từ khoá và đọc trang liên quan (`absence_check`).
  Câu có đáp án có `evidence_groups` (OR giữa nhóm, AND trong `all_of`) và `required_facts`.

## Cách xử lý tài liệu đa phương thức

1. PyMuPDF lấy text block, bảng có kẻ, ảnh raster, cụm hình vector kèm bbox. Thanh mục lục bên trái, header lặp và số trang
   được học từ tần suất lặp ở vùng lề và loại bỏ; chương lấy từ mục đang tô màu trên thanh mục lục.
2. Vision model đọc ảnh trang + danh sách block id → gom block thành vùng bảng/biểu đồ/sơ đồ/infographic/ảnh và mô tả hình
   (ghép số với năm/nhãn trong biểu đồ). **Text của chunk lấy nguyên văn từ PDF**; bảng không kẻ được dựng lại hàng theo toạ độ dòng.
3. Bbox vùng = hợp các object PDF mà model tham chiếu (337/337 vùng), không dùng toạ độ model đoán → crop chính xác.
4. Pass cấu trúc riêng cho 71 sơ đồ/infographic từ ảnh crop (quan hệ cha→con, bước→nội dung).
5. Mọi số do model viết được kiểm **nguyên token** với text layer; dòng cấu trúc có số không khớp bị loại (10 dòng).
   Chi phí index: vision trang ≈ $1.69 + cấu trúc ≈ $0.14; embed local ~80 s.

## Retrieval và thử nghiệm (dev, query gốc, proxy)

Proxy evidence: chunk cùng trang gold **và** chứa ≥ 1/2 quote gold hoặc phủ ≥ 1/2 bbox gold. Full@3: một nhóm `all_of` đủ trong top-3.

| Cấu hình | Phương pháp | Split | Hit@1 | Evidence Hit@3 | Full@3 | Thời gian / chi phí |
|---|---|---|---|---|---|---|
| Dense (Day 6) | bge-m3 + pgvector, top-k 10 | basic / adv dev | 26/40 · 36/56 | 38/40 · 43/56 | 32/40 · 37/56 | ~50 ms/câu, $0 |
| BM25 | âm tiết tiếng Việt, số giữ nguyên | basic / adv dev | 35/40 · 37/56 | 39/40 · 48/56 | 32/40 · 42/56 | ~1 ms, $0 |
| BM25 bigram | + bigram âm tiết | basic / adv dev | 32/40 · 40/56 | 37/40 · 48/56 | 31/40 · 41/56 | ~1 ms, $0 |
| **Hybrid RRF** (chọn) | dense + BM25 bigram, pool 50, k=60 | basic / adv dev | 33/40 · 41/56 | 39/40 · 50/56 | 33/40 · 43/56 | ~50 ms, $0 |
| Hybrid + LLM rerank | top-20 chấm 0–3 bằng gpt-5.4-mini | basic / adv dev | 34/40 · 40/56 | 38/40 · 51/56 | 36/40 · 46/56 | ~2,4 s, $0.005/câu |

Rerank tăng Full@3 (+3/+3) nhưng chậm ~50× và tốn phí; không chọn cho agent vì agent đã search nhiều lượt (context đủ evidence 51–52/56 không cần rerank).

## Agent và đánh giá (advanced dev, 70 câu)

Tool: `search` (hybrid, top-5), `open_page`, `view_image` (tuỳ chọn), `final_answer`. Lượt đầu luôn search câu gốc (ranking câu gốc lưu riêng);
tối đa 6 bước, bước cuối bắt buộc `final_answer`. Context khử trùng theo chunk_id, ngân sách 24.000 ký tự (≤ 2.500/chunk).
Citation phải là chunk đã thấy và xuất hiện dạng `[chunk_id]`; sai → 1 lượt sửa → không đạt thì từ chối. Lỗi model/DB ghi `status=error`, không thay bằng kết quả giả.

| Cấu hình (adv dev) | Strict pass proxy | Judge 2/1/0 | Context đủ | Từ chối đúng | Từ chối nhầm | Chi phí | p50 / p95 |
|---|---|---|---|---|---|---|---|
| Baseline lần 1 | 53/70 | 48/5/3 | 52/56 | 13/14 | 0/56 | $0.34 | 3,1 / 10,0 s |
| Baseline lần 2 (đo nhiễu) | 55/70 | 50/–/– | – | 14/14 | 1/56 | $0.24 | 3,4 / 11,7 s |
| C1 prompt v2 (tách vế, đơn vị, không ghép chỉ tiêu) | 53/70 | 48 | 51/56 | 14/14 | 0/56 | $0.37 | 3,0 / 12,0 s |
| C2 = C1 + view_image | 50/70 | 47 | 51/56 | 12/14 | 2/56 | $0.37 | 3,1 / 10,4 s |
| C3 prompt v3 (trích đủ nguồn) | 54/70 | 50 | – | 13/14 | 0/56 | $0.38 | 2,9 / 10,8 s |
| **B1 = baseline + mở rộng citation** (chấm lại 3 bộ trace) | 57 · 58 · 57 /70 | – | – | – | – | +$0 | +0 s |

Basic dev baseline: **43/50** (bảng 10/10, text 27/30, multi-hop 6/10; từ chối đúng 10/10). Tool use 100%; phân bố số lần search (baseline adv): 1 lần 50 câu, 2 lần 13, ≥3 lần 7.

**Strict pass proxy** = trả lời, judge 2/2, context chứa đủ một nhóm evidence gold, citation phủ đủ nhóm đó, không có khẳng định thiếu căn cứ;
câu thiếu evidence: từ chối và judge xác nhận. LLM judge (gpt-5.4-mini) so với đáp án chuẩn; **không thay người chấm**.

### Lỗi dev đã phân tích

1. **Sơ đồ mất cấu trúc khi index** (DEV-039, 042): mô tả liệt kê đủ công ty nhưng không nói công ty nào thuộc nhánh nào → agent đoán sai
   (FPT Online/Telecom thay vì Synnex FPT/FPT Retail; LED ở bước 03 thay vì 04). Thử 1: tool `view_image` (C2) — sửa được khi model gọi,
   nhưng model chỉ gọi 4/70 câu. Thử 2: pass cấu trúc ở bước index (đã áp dụng cho bản index cuối).
   Phát hiện kèm: bộ kiểm số dạng chuỗi con cho qua số bị chép thiếu ("7.750.000.000" ⊂ "7.750.000.000.000") → sửa thành so nguyên token.
2. **Citation nguồn tương đương thay vì nguồn gold** (DEV-012, 013, 017, 028…): đáp án đúng nhưng trích thuyết minh/bảng tóm tắt thay vì
   BCĐKT/KQKD/biểu đồ được hỏi, trong khi chunk gold đã ở trong context. Prompt (C3) không đổi hành vi (vẫn 1,5 citation/câu).
   Sửa bằng code: trích thêm mọi chunk trong context chứa nguyên văn số ≥ 4 chữ số của câu trả lời → +3/+4/+3 câu trên 3 bộ trace.
3. **Multi-hop thiếu vế / ghép sai chỉ tiêu** (DEV-048 dùng nhân sự bình quân thay vì tổng; DEV-069 tự nhân hai chỉ tiêu khác tập):
   prompt v2 sửa được các câu này nhưng làm hỏng câu khác; tổng không vượt nhiễu.

**Nhiễu:** hai lần chạy cùng cấu hình lệch 12/70 câu → chênh ±3 câu không có ý nghĩa; chỉ B1 (đánh giá trên cùng trace) là cải thiện đo được.

**Chọn cấu hình:** tiêu chí ghi trước ([selection_criteria.md](../selection_criteria.md), commit trước khi xem kết quả). Vòng 120 câu dev
(B0–B3, gồm tách câu hỏi) bị dừng vì hết thời gian; chốt **B1** dựa trên bằng chứng đã có. Manifest đóng băng trước test: `starter/results/runs/`.

## Thử thách nâng cao

- Tài liệu: như trên (232 trang ≥ 100, có bảng, biểu đồ vector, sơ đồ, ảnh).
- Phần chưa xử lý: 3 trang mở chương (không có nội dung riêng); 12 ảnh trang trí bị bỏ có ghi log; mô tả do model viết vẫn có thể sai ở phần
  không có số (đã giảm bằng pass cấu trúc, cần người chấm kiểm).
- Ca hệ thống: 14/60 ca chạy tự động không cần model (`src/system_checks.py`): 13 pass, SYS-012 partial (cần người xem crop).

### Kết quả test

| Cấu hình / suite test | Strict pass proxy | Hit@1 / Hit@3 câu gốc | Context đủ | Judge 2/1/0 | Citation trên gold | Từ chối đúng | Từ chối nhầm | Lỗi | Chi phí | p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline / basic | **43/50 (86.0%)** | 31/40 (77.5%) / 40/40 (100.0%) | 38/40 (95.0%) | 37/2/1 | 44/68 (64.7%) | 9/10 (90.0%) | 1/40 (2.5%) | 0 | $0.25 | 2.7 / 12.0 s |
| baseline / advanced | **46/70 (65.7%)** | 42/56 (75.0%) / 49/56 (87.5%) | 52/56 (92.9%) | 40/12/4 | 60/113 (53.1%) | 11/14 (78.6%) | 2/56 (3.6%) | 0 | $0.47 | 4.4 / 27.1 s |
| chosen_B1 / basic | **44/50 (88.0%)** | 31/40 (77.5%) / 40/40 (100.0%) | 38/40 (95.0%) | 37/2/1 | 46/72 (63.9%) | 9/10 (90.0%) | 1/40 (2.5%) | 0 | $0.25 | 2.7 / 12.0 s |
| chosen_B1 / advanced | **47/70 (67.1%)** | 42/56 (75.0%) / 49/56 (87.5%) | 52/56 (92.9%) | 40/12/4 | 61/124 (49.2%) | 11/14 (78.6%) | 2/56 (3.6%) | 0 | $0.47 | 4.4 / 27.1 s |

Advanced test theo nhóm (cấu hình đã chọn B1, proxy; nhóm thiếu evidence tách riêng):

| Nhóm | Đạt / tổng |
|---|---|
| table | 8/16 |
| image | 6/8 |
| chart | 8/10 |
| multi_hop | 4/12 |
| text | 10/10 |
| thiếu bằng chứng | 11/14 |
| **toàn bộ** | **47/70 (67.1%)** (ngưỡng bonus ≥ 63/70, cần nhãn người chấm) |

B1 trên test được dựng từ trace baseline test bằng bước mở rộng citation xác định (không chạy lại model): cùng câu trả lời, so sánh theo cặp. Nhãn là proxy + LLM judge; điểm chính thức cần người chấm (`python3 benchmark/fpt_2025/tools.py review-template ...` rồi `score`).

## Giới hạn

- **Advanced test theo proxy là 47/70 (67,1%) < 63/70: không đạt ngưỡng 90% của thử thách nâng cao.** Yếu nhất: bảng 8/16 (chủ yếu citation nguồn tương đương/thiếu một ô), multi-hop 4/12 (thiếu vế thứ hai). Dev advanced (~76–83%) cao hơn test → dev chưa đại diện đủ; hướng tiếp: tách câu hỏi (B2, đã cài nhưng chưa đo), rerank cho câu bảng.

- Nhãn proxy và LLM judge chỉ để chọn cấu hình; điểm test chính thức cần người chấm theo `tools.py score`, chưa thực hiện.
- Mở rộng citation có thể thêm nguồn tương đương ở trang khác; người chấm cần xác nhận từng citation hỗ trợ đáp án.
- Một lần chạy test; với mức nhiễu quan sát được, tỷ lệ test có sai số cỡ ±5–8 điểm phần trăm.
- B2/B3 (tách câu hỏi, prompt v2 + mở rộng citation) chưa được đo đầy đủ.
