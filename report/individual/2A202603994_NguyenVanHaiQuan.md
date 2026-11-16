# Báo cáo Day 7 — Nguyễn Văn Hải Quân (2A202603994)

> Cập nhật ngày **16/11/2026**: E2 trên **advanced test2 đạt 27/30 (90%)** theo bộ nhãn AI hỗ trợ, được Nguyễn Văn Hải Quân chấp nhận.
> Các bảng dev/test cũ ghi **proxy tự động + LLM judge**; mẫu chấm thủ công 7 câu của test cũ được báo riêng. Phương pháp xác nhận test2 và giới hạn nằm ở mục Test2 bên dưới.

## Giao diện demo

![Giao diện Lumina: chat với tài liệu FPT, citation theo trang PDF và bảng kiểm chứng luồng truy xuất](../../assets/report.png)

*Giao diện web Next.js kết nối agent: câu trả lời kèm citation và thời gian xử lý; bảng bên phải cho phép xem nguồn, luồng truy xuất và context.*

## Dữ liệu và benchmark

- **Nguồn:** Báo cáo thường niên FPT 2025, 232 trang PDF, SHA-256 `9449a725…0e6c` ([trang công bố](https://fpt.com/vi/nha-dau-tu/bao-cao-thuong-nien)).
  Tài liệu công khai nhưng không có quyền tái phân phối → `pdf/` không nằm trong repo; `benchmark/fpt_2025/source.json` ghi hash và cách lấy.
- **Index:** 232/232 trang có ledger (229 trang có chunk; 3 trang mở chương chỉ có tên chương/ảnh nền, có lý do);
  337 vùng (bảng 140, ảnh 103, infographic 66, biểu đồ 23, sơ đồ 5), **723 chunk**, trung vị 904 ký tự.
  Mỗi chunk giữ `pdf_page`, `printed_page` (in = PDF − 1), bbox (PDF points) và ảnh crop PNG của vùng gốc.
- **Vector store / embedding:** container PostgreSQL 16 + pgvector 0.8.7 của Day 6; `BAAI/bge-m3` revision `5617a9f61b02`,
  1024 chiều, chuẩn hoá L2, cosine chính xác (không ANN). Bảng mới `mm_*` (documents → pages → regions → chunks → embeddings), có `tsvector` cho lexical.
- **Agent:** baseline/B1 dùng `gpt-5.4-mini`; E2 dùng `gpt-5.4` (reasoning low, OpenAI Responses API). Lệnh chạy ở [src/README.md](../../src/README.md).
- **Benchmark (tự soạn):** 240 câu + 60 ca hệ thống. Basic: dev 40+10, test 40+10; advanced: dev 56+14, test 56+14
  (có đáp án + thiếu evidence). Gold chỉ nằm ở `gold/` cho evaluator; agent chỉ nhận `queries/` (id + câu hỏi).
- **Test2 bổ sung:** 30 câu advanced mới (24 có đáp án, 6 thiếu evidence), tạo sau khi chốt E2 để đánh giá sau vòng sửa lỗi.
  Tổng cộng 270 câu QA và 60 ca hệ thống; giữ riêng mẫu số của từng bộ, không gộp thành một tỷ lệ accuracy.
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
- **Ca hệ thống: 60/60 đã chạy** (`src/system_checks.py`, `src/system_checks_agent.py`; kết quả `starter/results/system/system_results_all.json`):
  **44 pass, 14 partial, 1 fail, 1 không áp dụng.** Agent lỗi được kiểm bằng model client giả (vòng lặp, lỗi DB, timeout, tool sai schema,
  độc lập giữa câu, citation ngoài context); bộ chấm kiểm bằng nhãn tổng hợp (mẫu số 70, 62/70 không đạt / 63/70 đạt, ALL-of vs OR, ID trùng);
  prompt injection trong chunk dùng model thật (không làm theo chỉ dẫn). **Fail:** SYS-025 ngân sách context chưa tính dòng header.
  **Partial đáng chú ý:** SYS-028 có 64 chunk > 2.500 ký tự bị cắt đuôi khi đưa vào context; SYS-029 ngân sách theo thứ tự đến trước
  (11 chunk bị bỏ trên E2 test); SYS-033 lỗi DB báo `error` nhưng chưa retry; các ca từ chối theo từng loại và vùng ảnh cần người chấm.

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

### Chấm thủ công (mẫu tối thiểu, có người chấm)

Theo BENCHMARK.md, đọc tối thiểu 5 câu test có đáp án + 2 câu thiếu evidence. Mẫu 7 câu advanced test chọn ngẫu nhiên
**seed cố định**, trải đều nhóm (004 text, 011 bảng, 031 biểu đồ, 042 sơ đồ, 056 multi-hop; 063, 069 thiếu evidence),
chấm bằng trang review local (`src/review_page.py --sample-only`); nhãn: [report/reviews/](../reviews/), chấm bằng `tools.py score`.

| Cấu hình (7 câu có người chấm) | Strict pass | Hit@1 / Hit@3 | Context đủ | Grounded 2/1/0 (TB /2) | Citation hợp lệ | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| Baseline | 3/7 | 4/5 · 5/5 | 5/5 | 2/3/0 (0,70) | 7/10 | 1/2 | 0/5 |
| B1 (đã chọn) | 3/7 | 4/5 · 5/5 | 5/5 | 2/3/0 (0,70) | 7/10 | 1/2 | 0/5 |
| E2 (post-hoc) | **5/7** | 4/5 · 5/5 | 5/5 | 5/0/0 (1,00) | 7/10 | 1/2 | 0/5 |

Người chấm: B1 — Nguyễn Văn Hải Quân; E2 — Nguyễn Bình An (khác người chấm nên so sánh B1/E2 có thể lẫn sai lệch giữa hai người).
Trên mẫu, E2 sửa đúng 3 câu B1 sai (004 đủ ý; 042 đúng cấp ĐHĐCĐ của Ban Kiểm soát; 056 tính đúng −1.488.699.675.718 VNĐ bằng tool `calculate`).
E2 còn trượt 031 (đáp án đúng nhưng thêm một citation trang 58 không hỗ trợ — một citation sai là trượt) và 069 (đã `abstain` nhưng vẫn nêu
"dự phòng hoàn nguyên đã ghi nhận = 0 VNĐ" → khẳng định thiếu căn cứ). Nhãn: [E2](../reviews/advanced.test.E2_gpt54_v4.sample.reviews.json).

- Baseline và B1 trùng nhau trên mẫu vì 7 câu này không có citation do bước mở rộng thêm vào.
- **Proxy khớp người chấm 6/7**; câu lệch (004) proxy cho đạt nhưng người chấm cho đáp án 1 (thiếu ý "chưa ghi nhận ≠ bằng 0")
  → proxy có xu hướng **dễ hơn** người chấm; 47/70 proxy nên xem là cận trên.
- Lỗi thấy trên mẫu: 042 đọc sai cấp của Ban Kiểm soát trên sơ đồ + 1 citation không hỗ trợ; 056 tính chênh lệch sai số liệu;
  069 khẳng định "0 đồng" cho thông tin báo cáo không công bố (từ chối sai). Đây đúng các nhóm lỗi đã sửa ở vòng E2.
- 63/70 câu advanced test cũ còn lại **chưa có người chấm**; mẫu này không xác nhận điểm của toàn bộ test cũ hay của test2.

**Ví dụ từng câu (advanced test, cấu hình B1, nhãn người chấm; trace: `starter/results/agent/advanced.test.chosen_B1/traces.json`)**

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| TEST-011 | bảng, có bằng chứng | 1 search (câu gốc) → top-1 `p036:table01` (lịch sử vốn điều lệ) | "05/2025 14.813.301.220.000 → 07/2025 17.035.071.210.000; tăng 2.221.769.990.000 VNĐ" [p036:table01] | **Đạt**: đáp án 2, context 2, citation đúng bảng gốc |
| TEST-063 | biểu đồ, thiếu bằng chứng | 4 search (câu gốc, "2035", "phân khúc 2035…") → chỉ có biểu đồ chi tiêu CNTT 2026 (PDF 46) | `abstain`: báo cáo chỉ có số 2026, không có chi tiêu thực tế 2035 theo phân khúc; nêu số 2026 có nguồn [p046:chart01][p046:text01-1] | **Đạt**: từ chối đúng, không bịa số 2035 |
| TEST-069 | multi-hop, thiếu bằng chứng | 1 search → chính sách dự phòng (PDF 184) + thuyết minh hoàn nguyên đất (PDF 217) | trả lời nghĩa vụ hoàn nguyên "0 đồng" [p184][p217] | **Lỗi**: báo cáo không công bố số này → khẳng định thiếu căn cứ, citation không hỗ trợ; đã thêm kiểm status từ chối ở prompt v4 |
| TEST-056 | multi-hop, lỗi tính | 4 search (mã 20 LCTT…) → BCLCTT PDF 172 | "Không" đúng, nhưng tự suy dòng tiền HĐKD = 10.242.001.818.617 thay vì đọc mã 20 = 10.136.043.915.911 | **Lỗi**: đáp án 1; nguyên nhân đọc sai hàng + tính tay → thêm tool `calculate` và bước tự kiểm hàng/cột ở v4 |

### Vòng cải thiện sau chẩn đoán (E2) — post-hoc, test KHÔNG độc lập

Sau khi chốt B1 và chạy test, đã đọc 23 câu advanced test trượt để chẩn đoán: 14 câu context đủ nhưng model đọc/tính sai,
4 câu thiếu vế multi-hop, 3 câu từ chối sai status, 2 câu citation; phát hiện lỗi index **hai bảng cạnh nhau bị gom nhầm cột**
(17 cặp vùng chồng lấn trên 12 trang BCTC). Sửa lỗi hệ thống (không chỉnh theo câu cụ thể):

1. Index: khối cột số được gán lại theo nhãn hàng cùng y gần nhất bên trái (26 khối, embed lại 21 chunk).
2. Agent prompt v4: tool `calculate` (Decimal, số định dạng báo cáo), tự kiểm bảng/hàng/cột năm/đơn vị, kiểm status khi câu trả lời nói "không công bố";
   tách câu hỏi thành ≤ 4 truy vấn con; mở rộng citation.
3. Model trả lời: so E1 `gpt-5.4-mini` với E2 `gpt-5.4` trên advanced dev (tiêu chí ghi trước: chọn E2 nếu hơn ≥ 4 câu).

| Cấu hình | Split | Strict pass proxy | Bảng | Ảnh/sơ đồ | Biểu đồ | Multi-hop | Text | Thiếu evidence | Chi phí | p50 / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 mini + sửa lỗi | adv dev | 57/70 | | | | | | 14/14 | $0.63 | 6,8 / 11,7 s |
| **E2 gpt-5.4 + sửa lỗi** | adv dev | **62/70** | | | | | | 14/14 | $1.68 | 8,3 / 13,2 s |
| E2 | **adv test** | **64/70 (91,4%)** | 15/16 | 7/8 | 9/10 | 10/12 | 10/10 | 13/14 | $1.87 | 9,4 / 20,9 s |
| E2 | basic test | 47/50 (94%) | | | | | | 9/10 | $1.07 | 6,7 / 18,0 s |

**Diễn giải:** E2 vượt ngưỡng 63/70 theo proxy, nhưng (a) chỉ 7/70 câu có nhãn người chấm như mục trên; (b) test đã được
dùng để chẩn đoán trước khi sửa nên kết quả **không độc lập** — theo RULES cần bộ test mới; test2 được trình bày bên dưới.
Kết quả proxy của lần chốt trước test vẫn là B1: advanced 47/70, basic 44/50. Đánh đổi của E2: chi phí ~4×
($0,027/câu so với $0,007/câu), p50 chậm ~2× (≈ 9 s/câu).

### Test2 — E2 đã chốt, kết quả theo bộ nhãn được xác nhận

**Thiết kế:** 30 câu mới, gồm 24 câu có đáp án (6 bảng, 5 ảnh/sơ đồ, 5 biểu đồ, 4 multi-hop, 4 text) và 6 câu thiếu evidence.
Trang được chọn với seed cố định từ các trang chưa nằm trong gold/absence_check của 240 câu cũ; soạn trước khi chạy E2 trên test2.
E2 giữ `gpt-5.4`, prompt v4, hybrid, decomposition và mở rộng citation; lần chạy này không bật `view_image`.
Người soạn đã biết các điểm mạnh/yếu của hệ thống, nên bộ mới vẫn có giới hạn về thiên lệch thiết kế.
Chi tiết: [thiết kế test2](../../benchmark/fpt_2025/TEST2.md), [trace 30 câu](../../starter/results/agent/advanced.test2.E2_gpt54_v4/traces.json).

**Phương pháp xác nhận:** AI hỗ trợ đối chiếu đáp án, context thực tế và citation với PDF, ghi nhãn cùng lý do cho cả 30 câu.
ở 30/30 câu, nên scorer trả `unreviewed=0`;
Nguồn nhãn: [JSON review](../reviews/advanced.test2.E2_gpt54_v4.NguyenVanHaiQuan.ai-assisted.reviews.json).

Chạy lại scorer offline trên JSON đã cập nhật, giữ nguyên quy tắc strict pass và mẫu số **toàn bộ 30 câu**:

| Chỉ số test2 | Kết quả theo nhãn đã xác nhận |
|---|---:|
| **Strict pass toàn bộ** | **27/30 — 90%** |
| Strict pass câu có đáp án | 21/24 — 87,5% |
| Từ chối đúng / từ chối nhầm | 6/6 / 0/24 |
| Evidence Hit@1 / Hit@3 câu gốc | 24/24 / 24/24 |
| Đủ nhóm evidence trong top-3 | 23/24 — 95,8% |
| Context đủ evidence | 21/24 — 87,5% |
| Grounded answer mức 2 / 1 / 0 | 22 / 2 / 0; điểm chuẩn hoá 46/48 — 95,8% |
| Context mức 2 / 1 / 0 | 21 / 3 / 0 |
| Citation hợp lệ | 52/53 — 98,1% |
| Tool use / lỗi chạy | 30/30 / 0 |
| Thời gian p50 / p95 | 9,7 / 23,8 giây |
| Chi phí agent / LLM judge ban đầu | $0,6929 / $0,0270; chưa gồm index |

Hit chỉ ghi nhận có evidence liên quan trong kết quả retrieval; không đồng nghĩa context giữ đủ nội dung sau khi cắt chunk,
hay câu trả lời đạt strict. Điểm grounded chuẩn hoá cũng không thay thế tỷ lệ strict pass.

| Nhóm test2 | Có đáp án: đạt/tổng | Thiếu evidence: đạt/tổng | Tổng nhóm |
|---|---:|---:|---:|
| Bảng | 5/6 | 2/2 | 7/8 |
| Ảnh/sơ đồ | 3/5 | — (không có ca) | 3/5 |
| Biểu đồ | 5/5 | 2/2 | 7/7 |
| Multi-hop | 4/4 | 1/1 | 5/5 |
| Text | 4/4 | 1/1 | 5/5 |
| **Toàn bộ** | **21/24** | **6/6** | **27/30** |

**Ba câu chưa đạt** (ID rút gọn từ `FPT-ADVANCED-TEST2-…`, số trang PDF vật lý):

- **002 — bảng, PDF 35:** context bị cắt giữa số vốn tháng 05/2022. Agent suy ngược từ tỷ lệ cổ tức và tính chênh lệch
  1.828.377.620.000 VNĐ, trong khi số đúng từ bảng là **1.828.306.580.000 VNĐ**. Đáp án 1, context 1, citation không hỗ trợ phép suy ngược.
- **007 — ảnh/sơ đồ, PDF 113:** đáp án đúng, nhưng context bị cắt trước quan hệ giữa GRI 300 và cột môi trường;
  không có lượt xem ảnh để bổ sung. Context 1 nên chưa đạt strict dù đáp án được 2.
- **008 — ảnh/sơ đồ, PDF 113:** chỉ nêu GRI 400, thiếu **GRI 200** ở cột môi trường làm việc; context cũng mất liên kết theo cột.
  Đáp án 1, context 1. Các citation ở trang 118 hỗ trợ chi tiết bổ sung nên vẫn được tính hợp lệ.

[Chấm tự động ban đầu](../../starter/results/agent/advanced.test2.E2_gpt54_v4/auto.json) cũng cho 27/30 nhưng trượt **002, 008, 019**.
Sau đối chiếu, **019 đạt** vì hai nguồn PDF 48 và 50 hỗ trợ phép trừ 11,5 − 5,1 = 6,4 tỷ USD; **007 trượt** vì thiếu quan hệ trong context.
Tổng điểm bằng nhau không có nghĩa hai bộ nhãn đồng ý ở mọi câu. Citation hợp lệ theo nội dung (52/53) cũng khác metric proxy
“citation trên gold” (31/53), vốn có thể bỏ sót nguồn tương đương.

Kết quả tái lập: [summary cập nhật](../reviews/advanced.test2.E2_gpt54_v4.official.summary.json). Chạy từ thư mục gốc repo:

```bash
.venv/bin/python benchmark/fpt_2025/score_test2.py \
  --traces starter/results/agent/advanced.test2.E2_gpt54_v4/traces.json \
  --reviews report/reviews/advanced.test2.E2_gpt54_v4.NguyenVanHaiQuan.ai-assisted.reviews.json \
  --output report/reviews/advanced.test2.E2_gpt54_v4.official.summary.json
```

**Kết luận test2:** đạt đúng ngưỡng số học **27/30**, không làm tròn. Scorer ghi `meets_90_percent_numeric_threshold=true`
và `bonus_awarded=null`. Xác nhận theo mẫu 10 câu chưa hoàn tất yêu cầu đọc, đối chiếu từng câu test của
[ADVANCED.md §3](../../ADVANCED.md); báo cáo chưa khẳng định đủ điều kiện nhận bonus.

## Giới hạn

- **B1 trên test gốc: 47/70 (67,1%) theo proxy; E2 trên test2: 27/30 (90%) theo nhãn được chấp nhận qua mẫu.**
  Khác cấu hình, bộ câu hỏi và cách xác nhận nhãn; không lấy chênh lệch hai tỷ lệ làm mức cải thiện trên cùng một test.

- Test cũ mới có mẫu 7 câu chấm thủ công; test2 có nhãn AI hỗ trợ cho 30 câu, được chấp nhận dựa trên mẫu 10 câu như mô tả ở trên.
- Cắt mỗi chunk ở 2.500 ký tự có thể làm mất số hoặc quan hệ theo cột dù retrieval tìm đúng vùng; ba lỗi test2 cho thấy cần bảo toàn hàng/cột khi dựng context.
- Mở rộng citation có thể thêm nguồn tương đương ở trang khác; người chấm cần xác nhận từng citation hỗ trợ đáp án.
- Test2 mới chạy một lần và có 30 câu; mỗi câu làm thay đổi tỷ lệ khoảng 3,33 điểm phần trăm. Chưa đo độ ổn định qua nhiều lần chạy test2.
- Vòng B2/B3 ban đầu chưa được đo đầy đủ; E2 đã dùng tách câu hỏi nhưng chưa tách riêng tác động của từng thay đổi index, prompt, tool và model.
