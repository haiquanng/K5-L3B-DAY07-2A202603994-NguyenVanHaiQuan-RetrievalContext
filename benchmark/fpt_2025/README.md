# Bộ kiểm thử Lab 7 — FPT, Báo cáo thường niên 2025

**Đề xuất và đã soạn: 300 ca = 240 câu hỏi benchmark + 60 ca kiểm thử hệ thống.** Dùng duy nhất `pdf/BCTN_2025_ad403f779b.pdf` cho corpus indexing của phần cơ bản và advanced. Không dùng báo cáo VNZ.

Đây là bộ đánh giá v1 theo phạm vi Lab 7, không phải lời khẳng định đã liệt kê mọi tình huống có thể xảy ra. 300 không phải mẫu số để tính điểm advanced. Các ca hệ thống là đặc tả cần thực thi khi có pipeline; chúng chưa được chạy.

## Đọc và sử dụng ngay

- [240 câu hỏi, đáp án, trang và tiêu chí chấm](QUESTION_CASEBOOK.md).
- [60 ca hệ thống: chuẩn bị, thao tác và điều kiện đạt](SYSTEM_CASEBOOK.md).
- [Dữ liệu đầy đủ, có gold](cases.json) và [đặc tả hệ thống JSON](system_cases.json).
- [Nguồn, hash PDF, quy ước trang](source.json); [bản đóng băng và hash các file](manifest.json).
- `queries/`: chỉ `id` và `question`, dành cho chương trình chạy agent.
- `gold/`: nhãn dev/test theo từng suite, chỉ dành cho evaluator/người chấm.
- [Công cụ kiểm tra và tổng hợp điểm offline](tools.py).

**Không index thư mục benchmark, casebook, gold hoặc review vào RAG.** Chỉ index nội dung tài liệu nguồn. Không gửi `answerable`, đáp án, nhóm câu, trang gold, bbox gold hay kết quả rà thiếu evidence cho agent, kể cả khi tạo query rewrite hoặc filter.

## Vì sao chọn 300

25–30 câu chỉ cho rất ít ví dụ trong mỗi kiểu lỗi. Bộ này dành số lượng riêng cho truy xuất văn bản, đọc bảng, hình/sơ đồ, biểu đồ, nhiều trang và từ chối. 60 ca hệ thống kiểm tra những lỗi mà thêm câu hỏi nội dung không tự phát hiện được: thiếu trang khi index, trộn phiên bản, mất dấu âm, lọt gold, sai mẫu số hoặc citation chỉ đúng ID.

| Phần | Dev có đáp án | Dev thiếu evidence | Test có đáp án | Test thiếu evidence | Tổng |
|---|---:|---:|---:|---:|---:|
| Cơ bản | 40 | 10 | 40 | 10 | 100 |
| Advanced | 56 | 14 | 56 | 14 | 140 |
| **Benchmark** | **96** | **24** | **96** | **24** | **240** |
| Đặc tả hệ thống, không chia dev/test | | | | | **60** |

Mỗi split cơ bản có 24 text, 8 table, 8 multi-hop **có đáp án**. Mỗi split advanced có:

| Nhóm chính có đáp án | Dev | Test | Tối thiểu advanced test của lab |
|---|---:|---:|---:|
| Text | 10 | 10 | 4 |
| Bảng | 16 | 16 | 6 |
| Biểu đồ | 10 | 10 | 5 |
| Ảnh/sơ đồ chứa thông tin | 8 | 8 | 5 |
| Multi-hop | 12 | 12 | 4 |
| **Tổng có đáp án** | **56** | **56** | **24** |
| Thiếu bằng chứng | 14 | 14 | 6 |
| **Tổng advanced** | **70** | **70** | **30** |

Mỗi câu có một `primary_category`; không đếm một câu vào nhiều nhóm. Nhãn bổ sung nằm trong `tags`. Các câu thiếu bằng chứng cũng có category để phân tích, nhưng **không được dùng để đáp ứng số lượng câu có đáp án** của từng nhóm.

Đây là một bộ có chủ đích theo lỗi và yêu cầu, không phải mẫu ngẫu nhiên độc lập của mọi câu hỏi người dùng. Các câu có thể dùng chung trang/số liệu thành phần; không coi 240 câu là 240 sự kiện độc lập. Không gộp điểm basic và advanced thành một tỷ lệ để xin bonus. Nếu cần độ tin cậy cao cho vận hành thực tế, phải thêm câu từ traffic thật, câu độc lập và tài liệu khác. Cách chia tập và chấm relevance tham khảo [Stanford IR — evaluation](https://nlp.stanford.edu/IR-book/html/htmledition/information-retrieval-system-evaluation-1.html); đánh giá khoảng tin cậy cho tỷ lệ có thể dùng [NIST — confidence intervals for proportions](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), với điều kiện lấy mẫu phù hợp.

## Phạm vi nguồn và kiểm tra đáp án

PDF FPT có **232 trang vật lý**, SHA-256 `9449a7251d126b635988974dbc72c2773c7fff39f4e5e858b5f7d3928b4e0e6c`. Năm báo cáo là 2025; ngày tạo/phát hành file có thể thuộc 2026. Tham chiếu công bố: [trang báo cáo thường niên FPT](https://fpt.com/vi/nha-dau-tu/bao-cao-thuong-nien). File đang dùng là bản người dùng cung cấp; chưa khẳng định byte/hash trùng với một bản tải từ website. Không mặc nhiên suy ra quyền tái phân phối PDF từ việc tài liệu được công khai.

192 câu có đáp án có **234 mục evidence trên 98 trang nguồn khác nhau**. Các câu phủ thông tin doanh nghiệp, AI/chiến lược, hoạt động kinh doanh, quản trị, nhân sự, môi trường/xã hội và báo cáo tài chính/thuyết minh. Index vẫn phải xử lý **toàn bộ nội dung hữu ích của 232 trang**, kể cả 134 trang không được chọn làm gold. Ghi ledger trang thành công/lỗi/bỏ có lý do; không dùng danh sách gold làm whitelist indexing.

- `pdf_page`: trang PDF vật lý, đếm từ 1. `printed_page`: số in trên trang. Ví dụ PDF 169 là trang in 168.
- `quotes`: đoạn/nhãn/số nguyên văn dùng để định vị. Khớp chuỗi chỉ kiểm tra sự tồn tại, không chứng minh đã ghép đúng hàng/cột hoặc trả lời đúng.
- `bbox_pt`: vùng điều hướng theo PDF points, gốc trên trái. Bảng/biểu đồ dùng vùng nội dung rộng để giữ header, chú thích và đơn vị; **không coi bbox này là nhãn segmentation chính xác**. `locator` chỉ rõ hàng/cột/nhánh cần đọc.
- Câu ảnh có `visual_description`, dùng sơ đồ/quan hệ/thứ tự chứa thông tin; không hỏi từ ảnh trang trí.
- `required_facts`: các ý phải đủ. `calculations` ghi phép tính và sai số cho 45 ca số học; các điều kiện còn lại nằm trong đáp án chuẩn.
- `evidence_groups`: OR giữa các nhóm; **AND trong `all_of`**. Multi-hop cần đủ các vế, không chỉ một đoạn giống đáp án. Evidence khác tương đương được người chấm kiểm chứng thì ghi ngoại lệ/phiên bản nhãn, không thay chuẩn âm thầm sau khi xem điểm.
- 48 câu thiếu evidence có trường dữ liệu còn thiếu, trang liên quan, từ khóa và vị trí từ khóa xuất hiện trong toàn văn. Search hit không chứng minh có câu trả lời; top-k rỗng không chứng minh tài liệu thiếu thông tin. Cho phép nêu ngữ cảnh có nguồn, nhưng phải từ chối phần không đủ bằng chứng.

Đã kiểm tra hash/số trang, toàn bộ text anchor và phép tính đã khai báo; đã xem trực tiếp các sơ đồ và những bảng cần đối chiếu layout. Ví dụ đã sửa nhầm hàng ESG: LED thực tế 2025 là **88%**, không lấy **95%** của đào tạo môi trường. `gold_review_status` vẫn ghi **independent_reviewer_pending**: đây là bản do người biên soạn đối chiếu, chưa phải một vòng xác nhận độc lập của giảng viên/người chấm.

## Đối chiếu yêu cầu toàn lab

| Yêu cầu | Ca/tài liệu kiểm tra |
|---|---|
| PDF thực tế ≥100 trang, toàn bộ nội dung hữu ích, provenance | SYS-001–006; `source.json` |
| Text, bảng, ảnh, biểu đồ và lỗi extraction | SYS-007–012; các nhóm advanced |
| Ít nhất 3 retrieval, có dense tương thích Day 6 | SYS-013–018 |
| Query gốc/rewrite, fusion, rerank, multi-hop | SYS-019–024 |
| Budget, dedup, mở rộng, nén, đủ context | SYS-025–030 |
| Agent thật, vòng lặp, model/tool lỗi/timeout | SYS-031–036 |
| Citation có trong context và hỗ trợ nội dung | SYS-037–042 |
| Abstention đúng và false abstention | 48 câu thiếu evidence; SYS-043–048 |
| Hit@1/3, đủ context, nhãn 0–2, mẫu số và 90% | SYS-049–054; `tools.py score` |
| Không lộ gold, freeze, ≥2 cải tiến dev, baseline/chosen test, chi phí và nộp | SYS-055–060 |

Đối chiếu [BENCHMARK](../../BENCHMARK.md), [ADVANCED](../../ADVANCED.md), [GUIDE](../../GUIDE.md), [RULES](../../RULES.md), [RUBRIC](../../RUBRIC.md), [SUBMISSION](../../SUBMISSION.md), [CHECKPOINTS](../../CHECKPOINTS.md), [AGENT_SETUP](../../AGENT_SETUP.md), [PSEUDOCODE](../../PSEUDOCODE.md) và [starter](../../starter/README.md). Bộ ca không thay việc triển khai, chạy thật, phân tích lỗi và nộp báo cáo của lab.

## Chạy kiểm tra bộ dữ liệu

Chạy tại gốc repo, không cần API key:

```bash
python3 benchmark/fpt_2025/tools.py validate
python3 -m unittest discover -s tests -v
```

Kiểm tra thêm bản PDF gốc cần môi trường có PyMuPDF. Môi trường Day 6 hiện có sẵn:

```bash
../K5-L3B-DAY06-2A202603994-DataIngestion/starter/.venv/bin/python \
  benchmark/fpt_2025/tools.py validate --pdf pdf/BCTN_2025_ad403f779b.pdf
```

`build` là lệnh **biên tập** để xuất lại casebook/query/gold và manifest. Không chạy để che thay đổi bộ test đã công bố. Nếu sửa benchmark sau một lần chạy, tăng phiên bản, ghi thay đổi, giữ bản cũ và đánh giá ảnh hưởng tới kết quả. Manifest đóng băng nội dung câu; cấu hình/model/index/code phải được lưu riêng trước chạy test.

## Chạy agent và chấm

1. Chỉ dùng `queries/basic.dev.json` hoặc `queries/advanced.dev.json` để thử hệ thống. Chạy ≥3 retrieval và ít nhất hai cải tiến có giả thuyết trên dev. Không gộp hai suite để vô tình dùng câu test của suite kia làm dữ liệu chỉnh.
2. Chốt code, model, index/version/hash, embedding, filter, top-k, reranker, context budget, giới hạn search, tiêu chí lựa chọn và hash manifest. Sau đó chạy baseline và cấu hình chọn trên **cùng toàn bộ test** của suite tương ứng; lưu hai bộ trace riêng.
3. Người chấm mở PDF, đọc từng output và từng citation. Chấm cả 70 câu advanced test; bản này cũng khuyến nghị chấm đủ 50 câu basic test. Nếu test đã dùng để sửa pipeline, tạo test mới trước khi tuyên bố độc lập.
4. Ghi 60 ca hệ thống đạt/không đạt/không áp dụng kèm bằng chứng khi thực thi. Không đổi trạng thái của bộ đặc tả gốc; lưu kết quả ở file/run riêng.

Tạo mẫu review trống:

```bash
python3 benchmark/fpt_2025/tools.py review-template \
  --suite advanced --split test --output /tmp/fpt-advanced-test-reviews.json
```

Mỗi trace cần `query_id`, `status` (`answered`, `abstain`, `error`, `timeout`), `answer`, `citations` (danh sách chunk ID), `context_ids`, `events` (event `search` cho từng lần retrieval), `elapsed_ms`, `cost_usd`. Lưu thêm ranking câu gốc, ranking từng query viết lại, nội dung context, metadata nguồn/vùng, tool call và usage để kiểm tra. Cost/elapsed chưa biết để `null`, không ghi giả bằng 0. Mọi câu trả lời nêu rõ không đủ evidence cần chuẩn hóa `status=abstain`.

Mỗi review cần:

- `reviewer`, `human_confirmed=true`, `reason` sau khi thực sự được người chấm xác nhận.
- `answer_grade` 0/1/2 và `context_grade` 0/1/2 cho câu có đáp án; `abstention_correct` cho câu thiếu evidence; `unsupported_claims` cho tất cả câu.
- `retrieval_evidence_at_1`, `retrieval_evidence_at_3`: ID evidence gold mà người chấm xác nhận các chunk top-1/top-3 của **query gốc** thực sự hỗ trợ. Một chunk có thể hỗ trợ nhiều evidence. Không điền theo điểm similarity hoặc chỉ vì cùng trang.
- `context_evidence`: evidence thực sự có trong context cuối. Có thể bổ sung từ nhiều lượt search/neighbor.
- `citations`: đúng thứ tự danh sách citation của trace. Mỗi phần tử có `id`, `supports_answer` (bool), `source_locatable` (bool) và `evidence_ids` được citation đó hỗ trợ. `source_locatable=true` chỉ khi tìm được trang/vùng gốc.

Các ID evidence ở review chỉ được gán **sau khi chạy**, trong evaluator, không chuyển ngược vào retrieval/agent. Script tổng hợp nhãn, không tự suy ra semantic correctness từ chuỗi hoặc từ một LLM judge.

```bash
python3 benchmark/fpt_2025/tools.py score \
  --suite advanced --split test \
  --traces /tmp/fpt-advanced-test-traces.json \
  --reviews /tmp/fpt-advanced-test-reviews.json \
  --output /tmp/fpt-advanced-test-summary.json
```

### Quy tắc điểm

- Advanced: đủ **70/70** case trong mẫu số. Cần **≥63/70**, không làm tròn 62/70 lên 90%. Missing, timeout, error, đúng một phần, sai citation hoặc thiếu human review đều không pass.
- Câu có đáp án pass khi đáp án đúng/đủ, context đủ, mọi citation hợp lệ và hợp các citation phủ đủ một nhóm `all_of`; không có khẳng định thiếu căn cứ. Sai đơn vị, thời kỳ, điều kiện hoặc phép tính phải hạ `answer_grade`.
- Câu thiếu bằng chứng pass khi thực sự từ chối phần được hỏi, có lời giải thích và không bịa thêm. Không áp một câu chữ từ chối cố định.
- Hit@1/3 là tìm được **ít nhất một evidence hợp lệ**. `full_evidence_at_3` và Context Evidence Rate yêu cầu đủ một nhóm ALL-of. Mẫu số chỉ có câu answerable; báo thêm chỉ số đầy đủ để không che mất hop thứ hai.
- Script dùng mẫu số toàn bộ câu đã công bố cho chất lượng, kể cả lỗi/unreviewed, và báo riêng status. Đây là cách thận trọng, **khác starter `agent_metrics.py` loại lỗi khỏi chất lượng**; không so hai tỷ lệ có mẫu số khác nhau mà không ghi rõ. Tool use dùng số lần chạy thành công như lab.
- Citation rate báo `n/N`; `0/0` có `rate=null`, không tự chuyển thành 100%. Không có citation không thể pass câu answerable. Thời gian dùng median/p95 nearest-rank trên giá trị biết, báo số thiếu. Chi phí là tổng phần biết, có số case unknown; tách chi phí indexing ở báo cáo run.

`meets_90_percent_numeric_threshold` chỉ là ngưỡng số học, **không phải kết luận được bonus**. Vẫn cần hoàn thành điều kiện index, agent thật, audit và hồ sơ nộp.

## Trạng thái bàn giao

Đã viết đủ 240 câu + 60 đặc tả; đã kiểm tra schema, split, nguồn, anchor, phép tính, hash và 18 unit test mới của bộ tổng hợp điểm. Cả suite hiện có 33 unit test chạy qua. **Chưa chạy benchmark với agent thật; chưa thực thi 60 ca hệ thống; chưa có điểm chất lượng hoặc tuyên bố đạt 90%.** Các unit test dùng fixture tổng hợp chỉ kiểm tra bộ chấm, không được tính là kết quả của agent.
