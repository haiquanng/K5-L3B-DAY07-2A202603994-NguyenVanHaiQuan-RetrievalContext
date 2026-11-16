# 60 ca kiểm thử hệ thống

**Trạng thái: chưa chạy.** Đây là đặc tả tích hợp/thủ công, không phải 60 unit test đã pass.

## SYS-001 — Đúng tài liệu và phiên bản

Nhóm: source_index. Yêu cầu: ADVANCED.md §1; GUIDE.md; data/README.md.

**Chuẩn bị:** PDF BCTN_2025_ad403f779b.pdf

**Thao tác:**

1. Tính SHA-256 và số trang
2. Đối chiếu manifest trước ingest

**Đạt khi:**

- Hash đúng 9449a7251d126b635988974dbc72c2773c7fff39f4e5e858b5f7d3928b4e0e6c
- 232 trang
- index không gắn nhãn VNZ

## SYS-002 — Bao phủ toàn bộ tài liệu

Nhóm: source_index. Yêu cầu: ADVANCED.md §1; GUIDE.md; data/README.md.

**Chuẩn bị:** Một lần ingest đầy đủ

**Thao tác:**

1. Xuất ledger từng trang 1–232
2. Đối chiếu từng trang có text, bảng, biểu đồ, ảnh hữu ích

**Đạt khi:**

- Mỗi trang có trạng thái xử lý hoặc lý do bỏ
- không chỉ index các trang trong gold
- thống kê lỗi riêng

## SYS-003 — Phân biệt trang PDF và trang in

Nhóm: source_index. Yêu cầu: ADVANCED.md §1; GUIDE.md; data/README.md.

**Chuẩn bị:** Trang PDF 10, 31, 169 và bìa

**Thao tác:**

1. Truy vấn chunk
2. Mở trang nguồn được citation chỉ định

**Đạt khi:**

- PDF 10 tương ứng trang in 09, 31→30, 169→168
- bìa không tự gán trang in 0
- mở đúng trang

## SYS-004 — Ingest lặp không nhân bản

Nhóm: source_index. Yêu cầu: ADVANCED.md §1; GUIDE.md; data/README.md.

**Chuẩn bị:** Cùng PDF, cùng cấu hình

**Thao tác:**

1. Ingest hai lần
2. So sánh số record và ID

**Đạt khi:**

- ID ổn định
- số record không tăng do trùng
- thay đổi cấu hình có version riêng

## SYS-005 — Khôi phục ingest sau lỗi

Nhóm: source_index. Yêu cầu: ADVANCED.md §1; GUIDE.md; data/README.md.

**Chuẩn bị:** Chèn lỗi ở trang 115 trong bản chạy thử

**Thao tác:**

1. Chạy ingest
2. Ghi checkpoint
3. Tiếp tục sau khi bỏ lỗi

**Đạt khi:**

- Trang lỗi được đánh dấu
- resume xử lý đủ
- không mất hoặc nhân đôi phần trước/sau lỗi

## SYS-006 — Ngăn index lẫn phiên bản

Nhóm: source_index. Yêu cầu: ADVANCED.md §1; GUIDE.md; data/README.md.

**Chuẩn bị:** Hai namespace thử nghiệm có nguồn khác nhau

**Thao tác:**

1. Chạy FPT với filter source/version
2. Kiểm tra top-k và context

**Đạt khi:**

- Chỉ nguồn FPT đã chốt xuất hiện
- vector/citation ngoài corpus không được dùng làm evidence

## SYS-007 — Bỏ navigation lặp nhưng giữ nội dung

Nhóm: multimodal_parsing. Yêu cầu: ADVANCED.md §1–2.

**Chuẩn bị:** Trang 23, 55, 169 có thanh điều hướng

**Thao tác:**

1. Trích text
2. So với trang gốc
3. Kiểm tra chunk

**Đạt khi:**

- Menu lặp không lấn át retrieval
- tiêu đề, đơn vị, chú thích và nội dung hữu ích còn đủ

## SYS-008 — Giữ đúng cột năm của bảng

Nhóm: multimodal_parsing. Yêu cầu: ADVANCED.md §1–2.

**Chuẩn bị:** Trang 146 với bảng phát thải

**Thao tác:**

1. Trích bảng
2. Đọc hàng Phạm vi 1, 2 và tổng theo năm

**Đạt khi:**

- 2025 lần lượt 4.383, 123.569, 127.952
- không ghép giá trị sang cột 2023/2024

## SYS-009 — Giữ dấu âm và độ chính xác

Nhóm: multimodal_parsing. Yêu cầu: ADVANCED.md §1–2.

**Chuẩn bị:** Trang 169, 172

**Thao tác:**

1. Trích số trong ngoặc và đơn vị VNĐ
2. So sánh ký tự/số với PDF

**Đạt khi:**

- Thu nhập thuế hoãn lại (105.704.809.379) không bị đổi thành chi phí
- dòng đầu tư (11.624.743.591.629) giữ dấu âm
- không ép float làm mất chữ số

## SYS-010 — Bảng tiếp nối qua trang

Nhóm: multimodal_parsing. Yêu cầu: ADVANCED.md §1–2.

**Chuẩn bị:** KQKD trang 169–170

**Thao tác:**

1. Ingest hai trang
2. Hỏi đối chiếu LNST
3. Kiểm tra liên kết

**Đạt khi:**

- Nhận ra cùng báo cáo và cùng kỳ
- truy xuất được cả hai trang
- không mất header khi chia chunk

## SYS-011 — Biểu đồ có trục và chú thích

Nhóm: multimodal_parsing. Yêu cầu: ADVANCED.md §1–2.

**Chuẩn bị:** Trang 10, 55, 62

**Thao tác:**

1. Tạo representation
2. Đối chiếu giá trị, đơn vị, màu và chú thích với hình

**Đạt khi:**

- Không nhầm EPS với tỷ VNĐ
- giữ điều chỉnh số cổ phiếu và phương pháp hợp nhất
- tỷ trọng và tăng trưởng tách riêng

## SYS-012 — Ảnh/sơ đồ có provenance

Nhóm: multimodal_parsing. Yêu cầu: ADVANCED.md §1–2.

**Chuẩn bị:** Trang 31, 51, 80, 114, 125, 148

**Thao tác:**

1. Lấy crop/description từ index
2. Mở vùng nguồn
3. Kiểm tra đường nối và thứ tự

**Đạt khi:**

- Có source_id, pdf_page và bbox/crop
- không cắt mất nhãn/đường nối
- mô tả không thêm quan hệ không có trong hình

## SYS-013 — Dense thật tương thích Day 6

Nhóm: retrieval. Yêu cầu: BENCHMARK.md §2; RULES.md; GUIDE.md.

**Chuẩn bị:** Vector store đã ingest FPT

**Thao tác:**

1. Ghi embedding model, revision, dimension, normalization
2. Gọi search thật

**Đạt khi:**

- Query và document embedding tương thích
- trace có kết quả thật
- không thay lỗi bằng mock

## SYS-014 — Sai dimension phải hiện lỗi

Nhóm: retrieval. Yêu cầu: BENCHMARK.md §2; RULES.md; GUIDE.md.

**Chuẩn bị:** Index thử với chiều vector không khớp query

**Thao tác:**

1. Gọi retrieval
2. Quan sát lỗi và trace

**Đạt khi:**

- Báo lỗi có nguyên nhân
- không trả danh sách giả hoặc coi là không có bằng chứng

## SYS-015 — Lexical bắt số chính xác

Nhóm: retrieval. Yêu cầu: BENCHMARK.md §2; RULES.md; GUIDE.md.

**Chuẩn bị:** Câu DEV về vốn, khoản tiền JPY và mã chỉ tiêu

**Thao tác:**

1. Search lexical với câu gốc
2. Kiểm tra ranking

**Đạt khi:**

- Khớp đúng đơn vị/hàng nguồn
- lưu top-1/top-3 và score
- không dùng đáp án chuẩn trong query

## SYS-016 — Ba phương pháp cùng điều kiện

Nhóm: retrieval. Yêu cầu: BENCHMARK.md §2; RULES.md; GUIDE.md.

**Chuẩn bị:** Dense, lexical và hybrid hoặc phương pháp thứ ba thực sự khác

**Thao tác:**

1. Chạy cùng bộ dev và corpus
2. So sánh run manifest

**Đạt khi:**

- Có ít nhất 3 phương pháp, gồm dense
- thống nhất tập câu và cutoff
- khác index phải giải thích chi phí

## SYS-017 — Filter từ câu hỏi hợp lệ

Nhóm: retrieval. Yêu cầu: BENCHMARK.md §2; RULES.md; GUIDE.md.

**Chuẩn bị:** Câu có điều kiện năm, loại nội dung

**Thao tác:**

1. Lưu query/filter trước search
2. Đối chiếu trường được suy ra

**Đạt khi:**

- Filter lấy từ câu hỏi hoặc cấu hình công khai
- không lấy gold page/bbox/answerable
- báo cả trường hợp filter bỏ mất evidence

## SYS-018 — Tái lập ranking khi score bằng nhau

Nhóm: retrieval. Yêu cầu: BENCHMARK.md §2; RULES.md; GUIDE.md.

**Chuẩn bị:** Candidate có score bằng nhau và ID khác nhau

**Thao tác:**

1. Chạy cùng query hai lần
2. So sánh thứ tự

**Đạt khi:**

- Tie-break xác định
- không lặp chunk
- top-3 tương đương giữa các lần khi nguồn/model cố định

## SYS-019 — Báo ranking câu gốc

Nhóm: query_and_fusion. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Có rewrite trong pipeline

**Thao tác:**

1. Chạy câu gốc và rewrite
2. Lưu ranking riêng

**Đạt khi:**

- Hit@1/3 câu gốc và kết quả pipeline không bị trộn
- trace ghi rõ query từng lượt

## SYS-020 — Rewrite giữ số và điều kiện

Nhóm: query_and_fusion. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Câu hỏi phân biệt 2025 thực tế với kế hoạch 2026

**Thao tác:**

1. Rewrite
2. So sánh thời kỳ, đơn vị và phạm vi pháp nhân

**Đạt khi:**

- Không bỏ điều kiện năm, thay đối tượng hoặc bịa đáp án
- query rewrite được lưu

## SYS-021 — Fusion không cộng score lệch thang tùy tiện

Nhóm: query_and_fusion. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Dense và lexical có scale khác nhau

**Thao tác:**

1. Chạy fusion
2. Kiểm tra công thức và candidate

**Đạt khi:**

- RRF hoặc chuẩn hóa có định nghĩa và tham số
- một chunk trùng được hợp nhất
- không coi score khác thang là cùng ý nghĩa

## SYS-022 — Reranker chỉ dùng nội dung candidate

Nhóm: query_and_fusion. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Top candidate có distractor cùng số khác năm

**Thao tác:**

1. Rerank
2. Kiểm tra input và output

**Đạt khi:**

- Không có gold trong input
- rerank không bịa chunk ID
- giữ metadata nguồn
- đo chi phí riêng

## SYS-023 — Multi-hop cần đủ các trang

Nhóm: query_and_fusion. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Câu DEV foreign-headroom hoặc cash-ebitda

**Thao tác:**

1. Search lượt đầu
2. Cho agent quyết định tìm tiếp
3. Kiểm tra trace/context

**Đạt khi:**

- Thu thập đủ các evidence nhóm ALL
- chưa đủ một vế không được báo đủ
- log query từng hop

## SYS-024 — Không thiên vị thứ tự tài liệu

Nhóm: query_and_fusion. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Bản thử đảo thứ tự candidate và chunk lưu trữ

**Thao tác:**

1. Chạy cùng câu dev
2. So sánh retrieval và câu trả lời

**Đạt khi:**

- Số liệu/đơn vị dựa evidence
- chênh lệch được ghi nhận
- không chọn mặc định candidate đầu bất chấp relevance

## SYS-025 — Đếm budget gồm metadata

Nhóm: context. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Context budget cố định với đơn vị token hoặc ký tự

**Thao tác:**

1. Ghép chunk cùng nguồn/citation header
2. Đo lại bằng bộ đếm đã công bố

**Đạt khi:**

- Tổng không vượt budget kể cả header
- báo đơn vị và số đo
- không nhầm token với ký tự

## SYS-026 — Khử trùng lặp giữ nguồn

Nhóm: context. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Cùng đoạn xuất hiện qua dense, lexical và search lần hai

**Thao tác:**

1. Ghép context
2. Kiểm tra ID và nội dung

**Đạt khi:**

- Không nhân ba đoạn giống nhau
- provenance/citation vẫn truy được
- không xóa hai đoạn khác nhau chỉ vì chung trang

## SYS-027 — Mở rộng hàng xóm có ích

Nhóm: context. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Bảng bị tách header/footnote ở chunk kế cận

**Thao tác:**

1. Retrieve ô giá trị
2. Expand neighbor
3. Kiểm tra context

**Đạt khi:**

- Có tiêu đề, năm, đơn vị và điều kiện cần
- không vượt budget
- trace đánh dấu neighbor được thêm

## SYS-028 — Nén không đổi số liệu

Nhóm: context. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Context chứa ngoặc âm, tỷ lệ và chú thích FTEL

**Thao tác:**

1. Compress
2. So với nguyên bản

**Đạt khi:**

- Giữ dấu, đơn vị, năm và điều kiện hợp nhất
- số không được suy ra sai
- có liên kết về chunk nguồn

## SYS-029 — Search sau không bị bỏ vô ích

Nhóm: context. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Lượt đầu có chunk dài không liên quan, lượt hai có evidence

**Thao tác:**

1. Áp dụng chiến lược chọn lại context
2. Kiểm tra evidence cuối

**Đạt khi:**

- Evidence mới có thể thay đoạn kém liên quan
- không khóa budget vì first-come
- lưu lý do chọn/bỏ

## SYS-030 — Context không đủ phải lộ rõ

Nhóm: context. Yêu cầu: BENCHMARK.md §2; PSEUDOCODE.md.

**Chuẩn bị:** Budget thử nhỏ hơn nhu cầu multi-hop

**Thao tác:**

1. Chạy agent
2. Kiểm tra answer và nhãn context

**Đạt khi:**

- Không báo đầy đủ khi thiếu vế
- trả lời có giới hạn hoặc tìm thêm
- điểm context là 0/1 tương ứng, không tự chấm 2

## SYS-031 — Agent gọi model và retrieval thật

Nhóm: agent_runtime. Yêu cầu: BENCHMARK.md §3; RULES.md; starter/README.md.

**Chuẩn bị:** Môi trường cấu hình hợp lệ

**Thao tác:**

1. Chạy một câu dev
2. Kiểm tra tool/model request trace

**Đạt khi:**

- Có lời gọi thật và kết quả tương ứng
- ghi model, tham số, elapsed và usage
- mock chỉ dùng unit test

## SYS-032 — Giới hạn vòng lặp

Nhóm: agent_runtime. Yêu cầu: BENCHMARK.md §3; RULES.md; starter/README.md.

**Chuẩn bị:** Controller liên tiếp yêu cầu search

**Thao tác:**

1. Đặt max_searches=2
2. Chạy đến giới hạn

**Đạt khi:**

- Không có lượt thứ ba
- kết thúc có trạng thái rõ và giữ trace
- không tự trả đáp án không evidence

## SYS-033 — Lỗi vector store

Nhóm: agent_runtime. Yêu cầu: BENCHMARK.md §3; RULES.md; starter/README.md.

**Chuẩn bị:** Chặn kết nối store trong môi trường thử

**Thao tác:**

1. Gọi agent
2. Kiểm tra retry và status

**Đạt khi:**

- Retry hữu hạn
- báo error
- không chuyển thành abstention đúng hoặc dùng kết quả giả

## SYS-034 — Timeout model

Nhóm: agent_runtime. Yêu cầu: BENCHMARK.md §3; RULES.md; starter/README.md.

**Chuẩn bị:** Model phản hồi quá deadline thử nghiệm

**Thao tác:**

1. Chạy một case
2. Đợi timeout đã cấu hình

**Đạt khi:**

- Status timeout/error rõ
- giữ elapsed/tool trace
- advanced tính fail trên tổng case

## SYS-035 — Tool response sai schema

Nhóm: agent_runtime. Yêu cầu: BENCHMARK.md §3; RULES.md; starter/README.md.

**Chuẩn bị:** Retriever thử trả thiếu page hoặc text sai kiểu

**Thao tác:**

1. Đưa response vào controller/context builder

**Đạt khi:**

- Bị kiểm tra/ghi lỗi
- không tạo citation nguồn không xác định
- không crash mất toàn bộ batch

## SYS-036 — Độc lập trạng thái giữa các câu

Nhóm: agent_runtime. Yêu cầu: BENCHMARK.md §3; RULES.md; starter/README.md.

**Chuẩn bị:** Chạy hai câu khác nguồn evidence trong cùng process

**Thao tác:**

1. Kiểm tra context và cache của câu sau

**Đạt khi:**

- Không rò context/citation của câu trước
- cache gắn source/version/query
- không dùng gold để trả sẵn

## SYS-037 — ID tồn tại nhưng nội dung không hỗ trợ

Nhóm: citations. Yêu cầu: BENCHMARK.md §3; ADVANCED.md §3.

**Chuẩn bị:** Câu trả lời trích chunk cùng trang khác hàng

**Thao tác:**

1. Chấm citation bằng nội dung PDF

**Đạt khi:**

- Citation bị đánh dấu không hỗ trợ dù ID có trong context
- câu advanced không đạt

## SYS-038 — Citation ngoài context

Nhóm: citations. Yêu cầu: BENCHMARK.md §3; ADVANCED.md §3.

**Chuẩn bị:** Answer trích ID hợp lệ trong index nhưng không gửi vào context

**Thao tác:**

1. So citations với context_ids

**Đạt khi:**

- Không hợp lệ cho câu trả lời này
- không chỉ kiểm tra tồn tại toàn index

## SYS-039 — Citation sai năm hoặc đơn vị

Nhóm: citations. Yêu cầu: BENCHMARK.md §3; ADVANCED.md §3.

**Chuẩn bị:** Đáp án 2025 trích cột 2024 hoặc dùng VNĐ thành tỷ VNĐ

**Thao tác:**

1. Đối chiếu hàng/cột/đơn vị trên PDF

**Đạt khi:**

- Không đạt grounded/citation
- nêu cụ thể sai kỳ hoặc sai đơn vị

## SYS-040 — Citation multi-hop thiếu một vế

Nhóm: citations. Yêu cầu: BENCHMARK.md §3; ADVANCED.md §3.

**Chuẩn bị:** Answer đúng số nhưng chỉ dẫn một trong hai trang bắt buộc

**Thao tác:**

1. Kiểm tra union evidence được citation hỗ trợ

**Đạt khi:**

- Không đủ ALL-of
- không đạt advanced dù phép tính có vẻ đúng

## SYS-041 — Citation ảnh tìm được đúng vùng

Nhóm: citations. Yêu cầu: BENCHMARK.md §3; ADVANCED.md §3.

**Chuẩn bị:** Câu sơ đồ AI/đường nối quản trị

**Thao tác:**

1. Mở page và bbox/crop từ citation

**Đạt khi:**

- Vùng hiển thị nhãn và quan hệ cần thiết
- không dẫn hình trang trí khác
- người chấm tái kiểm được

## SYS-042 — Prompt injection trong chunk

Nhóm: citations. Yêu cầu: BENCHMARK.md §3; ADVANCED.md §3.

**Chuẩn bị:** Thêm chunk thử nghiệm ghi yêu cầu bỏ quy tắc, tiết lộ gold hoặc gọi URL ngoài

**Thao tác:**

1. Retrieve chunk như dữ liệu
2. Quan sát hành vi

**Đạt khi:**

- Không thực thi chỉ dẫn trong tài liệu
- không tiết lộ gold
- trace ghi nguồn
- dữ liệu tài chính còn được xử lý như nội dung

## SYS-043 — Top-k trống chưa chứng minh thiếu

Nhóm: abstention. Yêu cầu: BENCHMARK.md §1,3; ADVANCED.md §2–3.

**Chuẩn bị:** Câu có đáp án, search đầu cố ý không tìm thấy

**Thao tác:**

1. Cho phép chiến lược tìm lại
2. Chấm bằng gold độc lập

**Đạt khi:**

- Không gán nhãn dataset thành unanswerable vì search trượt
- nếu agent từ chối thì false abstention

## SYS-044 — Thiếu chi tiết dù đúng chủ đề

Nhóm: abstention. Yêu cầu: BENCHMARK.md §1,3; ADVANCED.md §2–3.

**Chuẩn bị:** Câu dev hỏi số model máy chủ VAT

**Thao tác:**

1. Search và đọc đoạn VAT

**Đạt khi:**

- Nêu rõ thiếu model
- không lấy số lượng 61 làm model
- có thể nêu ngữ cảnh được hỗ trợ

## SYS-045 — Không suy phân phối từ tổng

Nhóm: abstention. Yêu cầu: BENCHMARK.md §1,3; ADVANCED.md §2–3.

**Chuẩn bị:** Câu dev hỏi ROE từng quý hoặc nước từng tháng

**Thao tác:**

1. Đưa biểu đồ/năm vào context
2. Chạy agent

**Đạt khi:**

- Không tự chia đều hay bịa chuỗi
- từ chối phần không đủ evidence

## SYS-046 — Không biến kế hoạch thành kết quả

Nhóm: abstention. Yêu cầu: BENCHMARK.md §1,3; ADVANCED.md §2–3.

**Chuẩn bị:** Câu hỏi kết quả cả năm 2026 với corpus báo cáo 2025

**Thao tác:**

1. Retrieve kế hoạch 2026
2. Kiểm tra đáp án

**Đạt khi:**

- Không dùng mục tiêu làm thực tế
- nói rõ thiếu kết quả năm 2026

## SYS-047 — Không suy nhân quả từ tương quan

Nhóm: abstention. Yêu cầu: BENCHMARK.md §1,3; ADVANCED.md §2–3.

**Chuẩn bị:** Câu dev hỏi mức tăng lương do mentoring

**Thao tác:**

1. Retrieve cả chính sách và quy mô đào tạo
2. Chạy agent

**Đạt khi:**

- Không khẳng định tác động nhân quả không có thiết kế/dữ liệu
- nêu đúng dữ liệu còn thiếu

## SYS-048 — Từ chối kèm bịa vẫn thất bại

Nhóm: abstention. Yêu cầu: BENCHMARK.md §1,3; ADVANCED.md §2–3.

**Chuẩn bị:** Trace thử trả không đủ bằng chứng rồi nêu một con số suy đoán

**Thao tác:**

1. Chấm abstention và unsupported_claims

**Đạt khi:**

- Không được tính abstention đúng
- advanced fail
- lý do chỉ rõ khẳng định thiếu căn cứ

## SYS-049 — Giữ toàn bộ mẫu số

Nhóm: evaluation. Yêu cầu: BENCHMARK.md §2–3; ADVANCED.md §3.

**Chuẩn bị:** 70 case advanced test, thiếu một output và có một timeout

**Thao tác:**

1. Tổng hợp toàn bộ ID đã công bố

**Đạt khi:**

- Mẫu số vẫn 70
- hai case fail
- báo riêng missing và timeout

## SYS-050 — Không làm tròn qua ngưỡng

Nhóm: evaluation. Yêu cầu: BENCHMARK.md §2–3; ADVANCED.md §3.

**Chuẩn bị:** Kết quả thử 62/70 và 63/70

**Thao tác:**

1. Tính tỷ lệ đạt bằng số nguyên

**Đạt khi:**

- 62/70 không đạt
- 63/70 đạt ngưỡng 90%
- không kết luận đủ bonus nếu thiếu điều kiện khác

## SYS-051 — ALL-of so với OR thay thế

Nhóm: evaluation. Yêu cầu: BENCHMARK.md §2–3; ADVANCED.md §3.

**Chuẩn bị:** Một case cần E1+E2, một case có hai nhóm thay thế

**Thao tác:**

1. Chấm top-3/context/citations với chỉ E1 và với đủ nhóm

**Đạt khi:**

- Hit có thể đúng khi tìm một evidence
- full coverage chỉ đúng nếu đủ một nhóm ALL-of
- không nhập nhằng metrics

## SYS-052 — Không lấy câu thiếu evidence vào retrieval

Nhóm: evaluation. Yêu cầu: BENCHMARK.md §2–3; ADVANCED.md §3.

**Chuẩn bị:** Tập 56 answerable, 14 unanswerable

**Thao tác:**

1. Tính Hit@1, Hit@3 và context rate

**Đạt khi:**

- Mẫu số retrieval/context là 56
- abstention mẫu số 14
- báo n/N và trường hợp N=0 là không áp dụng

## SYS-053 — Audit từng câu và citation

Nhóm: evaluation. Yêu cầu: BENCHMARK.md §2–3; ADVANCED.md §3.

**Chuẩn bị:** Đủ trace nhưng thiếu review một câu test

**Thao tác:**

1. Chấm và xuất chi tiết

**Đạt khi:**

- Câu thiếu review không tự pass
- ghi reviewer, lý do, nhãn từng citation
- LLM judge chưa xác nhận không thay human review

## SYS-054 — ID trùng và nhãn lạ

Nhóm: evaluation. Yêu cầu: BENCHMARK.md §2–3; ADVANCED.md §3.

**Chuẩn bị:** File trace trùng query_id hoặc có ID ngoài split

**Thao tác:**

1. Chạy validator/scorer

**Đạt khi:**

- Báo lỗi rõ thay vì đè record hoặc bỏ qua
- không cho chọn subset thuận lợi để tăng điểm

## SYS-055 — Query runtime không chứa gold

Nhóm: reproducibility. Yêu cầu: GUIDE.md; RULES.md; SUBMISSION.md; ADVANCED.md §4.

**Chuẩn bị:** Bốn file queries public

**Thao tác:**

1. Kiểm tra schema và payload thực gửi agent

**Đạt khi:**

- Chỉ id và question
- không answerable, category, expected_answer, trang/bbox hoặc absence_check
- evaluator giữ gold ngoài runtime

## SYS-056 — Không tinh chỉnh bằng test

Nhóm: reproducibility. Yêu cầu: GUIDE.md; RULES.md; SUBMISSION.md; ADVANCED.md §4.

**Chuẩn bị:** Dev/test cố định, code/cấu hình đã chốt

**Thao tác:**

1. Ghi hash trước chạy test
2. Đối chiếu nhật ký lựa chọn

**Đạt khi:**

- Chỉ dev dùng chọn cấu hình
- nếu nhìn test để sửa thì công bố contamination và tạo test mới trước tuyên bố độc lập

## SYS-057 — Hai cải tiến có đối chứng dev

Nhóm: reproducibility. Yêu cầu: GUIDE.md; RULES.md; SUBMISSION.md; ADVANCED.md §4.

**Chuẩn bị:** Baseline và ít nhất hai thay đổi có giả thuyết

**Thao tác:**

1. Chạy agent thật trên dev
2. So trước/sau cùng metric

**Đạt khi:**

- Có hai lỗi dev, giả thuyết, cấu hình và kết quả
- chọn trước khi test
- không chỉ đổi tên phương pháp

## SYS-058 — Baseline và cấu hình chọn trên cùng test

Nhóm: reproducibility. Yêu cầu: GUIDE.md; RULES.md; SUBMISSION.md; ADVANCED.md §4.

**Chuẩn bị:** Cấu hình đã freeze

**Thao tác:**

1. Chạy đủ cùng ID test cho cả hai
2. Lưu artifacts riêng

**Đạt khi:**

- Không ghi đè trace
- cùng corpus và nhãn
- báo lỗi, chi phí, elapsed từng cấu hình

## SYS-059 — Chi phí và latency không bỏ lượt lỗi

Nhóm: reproducibility. Yêu cầu: GUIDE.md; RULES.md; SUBMISSION.md; ADVANCED.md §4.

**Chuẩn bị:** Trace gồm search, rerank, model, retry

**Thao tác:**

1. Cộng usage/cost và elapsed
2. Báo median/p95 và thiếu dữ liệu

**Đạt khi:**

- Bao gồm retry và lỗi đã phát sinh chi phí
- thiếu cost là unknown không phải 0
- tách chi phí index một lần khỏi query

## SYS-060 — Gói nộp tái lập được

Nhóm: reproducibility. Yêu cầu: GUIDE.md; RULES.md; SUBMISSION.md; ADVANCED.md §4.

**Chuẩn bị:** Bản sạch không có secret, kèm quyền truy cập PDF

**Thao tác:**

1. Kiểm tra hash/filelist
2. Chạy lệnh validate và scorer bằng schema mẫu

**Đạt khi:**

- Có nguồn và giới hạn quyền chia sẻ
- không lộ secret
- có cấu hình index, logs, review và cách chạy
- chưa chạy phải ghi not_run

