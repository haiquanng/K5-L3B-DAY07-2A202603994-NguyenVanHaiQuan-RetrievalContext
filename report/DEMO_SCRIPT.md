# Kịch bản demo và trả lời phản biện Lab 07

Bản đối chiếu ngày 16/11/2026. Thời lượng đề xuất: **12 phút demo + 5 phút hỏi đáp**. Dùng báo cáo FPT 2025 `BCTN_2025_ad403f779b.pdf`. Các số trang dưới đây là **trang PDF vật lý**, không phải số in ở chân trang.

**Ba điều cần nói đúng từ đầu**

- Chat web chạy thật với `gpt-5.4-mini`, prompt v1, index hiện tại. Nó chưa dùng cấu hình E2 (`gpt-5.4`, prompt v4, decomposition, calculator, citation expansion). Không gán điểm E2 cho UI mặc định.
- Các tỷ lệ benchmark đang có là **proxy + LLM judge**, chưa phải nhãn người chấm. E2 đã dùng lỗi test để chẩn đoán trước khi sửa; kết quả chạy lại test của E2 không còn độc lập.
- 300 ca đã thiết kế gồm **240 câu QA + 60 đặc tả hệ thống**. Không nói “đã chạy và đạt 300 test”: mới có kết quả gắn ID cho 14/60 ca hệ thống, gồm 13 pass và 1 partial.

**Chuẩn bị trước buổi demo**

Mở UI tại http://127.0.0.1:3007. Nếu chưa chạy, dùng hai terminal trong `web`: `npm run backend` và `npm run dev`. PostgreSQL Day 6 phải đang hoạt động; nguồn PDF và index cần sẵn có.

Trong Cấu hình truy xuất, chọn Hybrid, Advanced, Top-k 5, budget 24.000 ký tự, tối đa 6 bước model, tắt rerank, bật mở rộng cùng trang. Đây là cấu hình UI hiện tại; không tuyên bố giống cấu hình benchmark B1/E2.

Gửi một câu đơn giản để nạp embedding model trước khi trình bày. Lần đầu có thể chậm vì nạp bge-m3; không dùng lượt khởi động này để suy ra độ trễ ổn định. Sau đó mở Trò chuyện mới. Chuẩn bị sẵn tài liệu này và [báo cáo](individual/2A202603994_NguyenVanHaiQuan.md); không cần mở file `.env`.

**Lịch trình 12 phút**

| Thời gian | Thao tác | Điều cần chứng minh |
|---|---|---|
| 0:00–0:45 | Giới thiệu bài toán | Trả lời từ tài liệu với bằng chứng, biết từ chối |
| 0:45–1:45 | Thư viện nguồn → ledger → mở trang gốc | Đúng PDF, nối Day 6, coverage toàn tài liệu |
| 1:45–3:15 | Hỏi doanh thu → nguồn → hỏi tiếp năm 2024 | Agent thật, citation và hội thoại |
| 3:15–4:15 | Mở Luồng xử lý và Context | Query, rank/score, context thực, budget, usage |
| 4:15–6:15 | Demo bảng LED và một câu đa trang hoặc sơ đồ | Đọc đúng hàng/cột; phối hợp evidence |
| 6:15–7:15 | Hỏi ROE từng quý | Từ chối có lý do; không suy số liệu quý từ năm |
| 7:15–8:15 | Trình bày lỗi DEV-039 đã lưu | Citation đúng ID vẫn có thể trả lời sai |
| 8:15–9:45 | Bảng retrieval và thí nghiệm C1/C2/C3 | ≥3 phương pháp, ≥2 cải tiến, đánh đổi |
| 9:45–11:15 | Bảng kết quả B1/E2 và giới hạn | Dev/test, n/N, post-hoc, human review |
| 11:15–12:00 | Tải transcript; mở Đối chiếu lab | Bằng chứng tái lập, phần còn thiếu |

Nếu chỉ có 5 phút: giữ Thư viện → doanh thu → citation/trace/context → ROE từng quý → lỗi DEV-039 → bảng kết quả. Bỏ các lần chạy bổ sung; không bỏ phần giới hạn kết quả.

**1. Lời mở đầu — có thể đọc gần nguyên văn**

> Em xây một hệ thống Agentic RAG trên Báo cáo thường niên FPT 2025, gồm 232 trang. Mục tiêu là tìm đúng bằng chứng trong văn bản, bảng, biểu đồ và sơ đồ, rồi trả lời có thể kiểm tra lại. Em đánh giá riêng khả năng truy xuất, context gửi model và chất lượng câu trả lời; một câu có citation chưa chắc đã đúng.

**2. Chứng minh nguồn và index**

Bấm **Thư viện nguồn**. Chỉ filename, hash nguồn, 723 chunk, 723 embedding và ledger 232 trang. Giải thích 229 trang có chunk; ba trang 56, 109, 159 là trang mở chương, đã ghi lý do không tạo chunk. Bấm một ô ledger để mở PDF.

> Em không chỉ index các trang có trong bộ câu hỏi. Pipeline duyệt toàn tài liệu và giữ provenance: trang PDF, trang in, vùng bbox và crop gốc. 232 trang có ledger không có nghĩa là cả 232 trang đều chứa chunk hữu ích.

**3. Câu mở đầu đã chạy thành công qua UI API**

Dán đúng câu:

> Doanh thu của FPT năm 2025 là bao nhiêu, đơn vị gì?

Đáp án đã quan sát: **70.113 tỷ VNĐ**, citation `fpt-ar2025:p010:chart01`, trang PDF 10. Mở citation số trong câu trả lời, sau đó mở bảng Nguồn để xem crop và metadata.

> Đây là kết quả lấy từ backend thật. Em kiểm tra cả con số, năm và đơn vị trên trang gốc; không chỉ nhìn model trả lời trôi chảy.

Trong cùng hội thoại, hỏi:

> Còn năm 2024 thì sao?

Lượt đã lưu trả **62.848,794 tỷ VNĐ**, tương đương **62.848.794 triệu VNĐ** ở PDF 214. Biểu đồ PDF 10 làm tròn thành **62.849 tỷ VNĐ**. Hai cách ghi không tự động mâu thuẫn; phải đối chiếu đơn vị và độ làm tròn.

> Backend nhận một phần lịch sử để hiểu câu hỏi tiếp nối. Lịch sử giúp hiểu ý, nhưng không được coi là evidence; câu trả lời mới vẫn phải có nguồn của lượt hiện tại.

Bằng chứng ba lượt kiểm thử thật nằm tại `starter/results/web_smoke/answer.json`, `followup.json`, `abstention.json` khi chạy trên máy này. Đây là kiểm tra tích hợp, không phải bộ benchmark đã chấm.

**4. Giải thích trace và context ngay trên UI**

Bấm **Xem luồng xử lý** rồi **Context**. Chỉ query gốc, các query bổ sung nếu có, thứ hạng/score, những chunk được gửi model, số ký tự và điều kiện dừng.

> Dense tìm theo ý nghĩa; lexical tìm theo từ và số; Hybrid hợp nhất hai bảng xếp hạng. Agent có thể tìm thêm hoặc mở các đoạn cùng trang khi thiếu dữ kiện. Context khử trùng theo chunk ID và bị giới hạn ngân sách để kiểm soát thông tin đưa vào model.

Cần nói chính xác:

- Top-k 5 là số chunk chọn ở mỗi lượt search để xét vào context. Ranking câu gốc có thể lưu 10 candidate để đánh giá; pool Hybrid là 50 mỗi nhánh. Các con số này thuộc các bước khác nhau.
- 24.000 là **ký tự text evidence**, không phải token và không phải toàn bộ prompt. Mỗi chunk tối đa 2.500 ký tự. Prompt, lịch sử, metadata và ảnh không nằm trong ngân sách text này.
- Tối đa 6 **bước model** không đồng nghĩa tối đa 6 lần search: một bước có thể gọi nhiều tool.
- UI stream sự kiện tool bằng NDJSON. Câu trả lời xuất hiện khi `final_answer` hoàn tất; không phải stream từng token và không hiển thị suy nghĩ nội bộ.
- Context của adapter web giữ đúng text sau khi cắt. Evaluator CLI cũ có điểm cần kiểm chứng vì lấy lại full chunk từ DB để tính proxy; không dùng số “context đủ” đó như bằng chứng chắc chắn về phần model thực sự đã đọc.

**5. Bảng, đa trang và sơ đồ — chọn hai câu nếu đủ thời gian**

Câu bảng:

> Theo bảng các chỉ tiêu ESG cam kết, tỷ lệ sử dụng bóng đèn LED thực tế năm 2025 và cam kết năm 2026 là bao nhiêu?

Mốc kiểm: **88% và 100%**, hàng 8, PDF 115. Không lấy 95% ở hàng đào tạo môi trường. Hai số này đã đối chiếu trực tiếp trên ảnh trang gốc; chưa có smoke test riêng cho đúng câu này với UI hiện tại.

Câu đa trang:

> Theo báo cáo, trần sở hữu nước ngoài và tỷ lệ sở hữu nước ngoài hiện tại là bao nhiêu? Chênh lệch là bao nhiêu điểm phần trăm, và có thể coi đó là số cổ phiếu room chính xác không?

Mốc kiểm: **49%** ở PDF 32; **38,73%** ở PDF 33; chênh **10,27 điểm phần trăm**. Không suy ra số cổ phiếu room chính xác chỉ từ tỷ lệ đã làm tròn. Cần nguồn hỗ trợ cả hai vế. Không dùng câu trả lời này như thông tin giao dịch hiện tại; đây là số liệu trong báo cáo năm 2025.

Câu sơ đồ:

> Theo nhánh “Công ty liên kết” trong sơ đồ tổ chức, hai công ty là gì? Nếu cần, hãy xem ảnh sơ đồ gốc.

Mốc kiểm: **Synnex FPT và FPT Retail**, PDF 31. Nhánh “Khối Giáo dục, Đầu tư và Khác” là nhánh khác, gồm FPT Education và FPT Investment. Tránh cách hỏi mơ hồ “Khối đầu tư” khi muốn hỏi công ty liên kết.

> Với sơ đồ, tìm đúng tên công ty chưa đủ; phải giữ đúng quan hệ giữa các hộp. Advanced cho phép model mở crop bằng `view_image`, nhưng em chỉ nói model đã xem ảnh nếu trace thực sự có tool này.

Nếu agent không gọi `view_image`, vẫn có thể trả lời từ mô tả sơ đồ đã index. Đừng nói “vision luôn chạy ở mọi câu advanced”.

**6. Câu thiếu bằng chứng đã chạy thành công**

Mở chat mới rồi dán:

> Báo cáo có công bố ROE riêng cho từng quý trong năm 2025 không? Nếu có, cho biết từng quý.

Lượt đã lưu có `status=abstain`, nêu không tìm thấy ROE từng quý; có thể nhắc ROE theo năm 2024 là 28,5% và 2025 là 28,1% với nguồn PDF 59.

> Từ chối ở đây không có nghĩa model hỏng. Tài liệu có ROE theo năm nhưng không đủ evidence cho từng quý. Trả lời đúng cần nêu rõ phần thiếu, không chia ROE năm cho bốn để tạo dữ liệu quý.

Từ việc top-k không có kết quả không thể kết luận cả tài liệu không có thông tin. Benchmark âm có kiểm tra thiếu evidence riêng; agent cần tìm thêm trước khi từ chối.

**7. Một lỗi thật, có trace trước/sau — bắt buộc nên trình bày**

Dùng case dev `FPT-ADVANCED-DEV-039`, không cần cố làm cho phiên bản hiện tại trả lời sai trực tiếp.

Câu hỏi: “Hai hộp công ty thuộc nhánh Công ty liên kết trong sơ đồ là gì?”

| Lần chạy đã lưu | Câu trả lời | Đối chiếu PDF 31 |
|---|---|---|
| `advanced.dev.hybrid_k5` | FPT Online và FPT Telecom | Sai: hai công ty này nằm ở nhánh viễn thông |
| `advanced.dev.c2_prompt_v2_view_image` | Synnex FPT và FPT Retail | Đúng nhánh Công ty liên kết |

Cả hai đều có citation `fpt-ar2025:p031:diagram01`. Mở PDF 31 để chỉ các đường nối. Trace gốc nằm trong `starter/results/agent/<tên-lần-chạy>/traces.json`; tìm ID trên.

> Lỗi không nằm ở việc thiếu citation: model đã trích đúng vùng nhưng hiểu sai cấu trúc. Em thử cho phép xem crop và bổ sung quan hệ sơ đồ vào index. C2 sửa được câu này nhưng tổng dev lại giảm từ 53/70 xuống 50/70, nên không thể lấy một ví dụ thành công để kết luận cấu hình tốt hơn toàn bộ.

Đây là ví dụ minh họa lỗi và cải thiện đã có, không phải tái chạy hiện tại. Phân biệt rõ “trace đã lưu” với “lượt đang demo”.

**8. Giải thích công nghệ trong khoảng 90 giây**

Luồng index: **PDF → PyMuPDF/layout → vùng và chunk có provenance → bge-m3 → PostgreSQL/pgvector**.

Luồng hỏi: **Next.js → Python agent → dense/BM25/Hybrid → context → model/tool → answer + citation + trace → UI**.

| Thành phần | Vai trò trong dự án | Cách giải thích ngắn |
|---|---|---|
| Next.js, React, TypeScript | Chat, cấu hình, lịch sử, bảng nguồn, benchmark | Giao diện trình bày và kiểm chứng |
| API Next.js | Proxy tới Python, truyền stream NDJSON | Trình duyệt không nhận API key |
| Python HTTP adapter | Giữ embedding model trong bộ nhớ, nhận/hủy lượt chat | Tái sử dụng backend của lab, tránh nạp model mỗi câu |
| PyMuPDF và vision | Trích text/layout; mô tả bảng, biểu đồ, sơ đồ | Giữ số trang, bbox và crop để kiểm tra nguồn |
| BAAI/bge-m3 | Embedding văn bản 1.024 chiều, cùng revision Day 6 | Câu hỏi và chunk nằm trong cùng không gian vector |
| PostgreSQL + pgvector | Lưu document/page/region/chunk/vector; dense cosine | Dense truy vấn trực tiếp vector store Day 6 |
| BM25/bigram | Xếp hạng từ khóa và số, chạy trong Python trên cùng chunk | Hữu ích khi hỏi tên, thuật ngữ, con số chính xác |
| Hybrid RRF | Hợp nhất thứ hạng dense và BM25 bigram | Không cộng trực tiếp hai score khác thang đo |
| Reranker | Model chấm lại Hybrid top-20 | Có thể cải thiện thứ hạng nhưng thêm độ trễ và chi phí |
| gpt-5.4-mini trên UI | Chọn tool, đọc evidence, trả lời/từ chối | Agent chưa được fine-tune trên PDF |
| `search`, `open_page`, `view_image`, `final_answer` | Các hành động của agent web | Có trace để kiểm chứng; ảnh chỉ bật ở Advanced |
| E2 qua CLI | gpt-5.4, prompt v4, decomposition và `calculate` | Là thí nghiệm khác, chưa phải cấu hình UI mặc định |

Đa phương thức ở đây chủ yếu là chuyển nội dung hình thành mô tả có provenance để truy xuất bằng **text embedding**, kết hợp xem lại ảnh gốc khi cần. Không tuyên bố đang dùng image embedding kiểu CLIP. Bảng có tsvector trong schema không có nghĩa BM25 hiện chạy bằng SQL; implementation BM25 nằm trong `src/retrieval.py`.

**9. Kết quả nên trình bày**

Bảng retrieval advanced dev đã lưu, 56 câu có đáp án; dùng cùng cutoff để so sánh. Các giá trị là nhãn proxy, tại phiên bản index của thí nghiệm đó.

| Phương pháp | Hit@1 | Evidence Hit@3 | Full evidence@3 |
|---|---:|---:|---:|
| Dense | 36/56 | 43/56 | 37/56 |
| BM25 | 37/56 | 48/56 | 42/56 |
| BM25 bigram | 40/56 | 48/56 | 41/56 |
| Hybrid | 41/56 | 50/56 | 43/56 |
| Hybrid + rerank | 40/56 | 51/56 | 46/56 |

> Hit@3 chỉ cần có ít nhất một evidence phù hợp trong top-3. Full evidence@3 đòi đủ một nhóm bằng chứng, nên thấp hơn ở câu multi-hop. Retrieval tốt chưa đảm bảo model đọc đúng hoặc trả lời đủ.

Ít nhất hai cấu hình cải thiện đã thử: C1 bổ sung prompt đọc đơn vị/tách vế; C2 thêm xem ảnh; C3 yêu cầu trích nguồn đầy đủ. Advanced dev lần lượt là baseline 53/70, C1 53/70, C2 50/70, C3 54/70. Một lần baseline chạy lại là 55/70: có biến động; không suy ra khoảng tin cậy thống kê từ chỉ hai lần chạy.

| Cấu hình | Basic test | Advanced test | Diễn giải phải đi kèm |
|---|---:|---:|---|
| Baseline trước khi xem test | 43/50 (86%) | 46/70 (65,7%) | Proxy + LLM judge |
| B1 chốt trước khi xem test | 44/50 (88%) | 47/70 (67,1%) | Thêm citation xác định trên cùng trace baseline; không gọi lại model |
| E2 sau chẩn đoán lỗi test | 47/50 (94%) | 64/70 (91,4%) | Post-hoc, test không độc lập; chưa có nhãn người chấm |

E1/E2 được so trên advanced dev sau vòng chẩn đoán: E1 mini 57/70, E2 gpt-5.4 62/70. E2 có thêm sửa index hai bảng cạnh nhau, prompt v4, decomposition và calculator. Đây không phải thí nghiệm chỉ đổi model so với B1.

E2 advanced test ghi chi phí agent khoảng **$1,87/70 câu**, p50 **9,4 giây**, p95 **20,9 giây**; baseline khoảng **$0,47/70 câu**, p50 **4,4 giây**, p95 **27,1 giây**. Phân biệt chi phí agent với chi phí judge và index; không cộng baseline và B1 như hai lần model độc lập. p50 E2 cao hơn nhưng p95 trong lần đo này thấp hơn: tránh nói tất cả thước đo latency đều tăng.

> B1 là kết quả của cấu hình đã chọn trước khi xem test, nhưng vẫn cần người chấm xác nhận. E2 cho thấy hướng cải thiện đạt 91,4% theo proxy trên bộ đã biết; em không dùng con số đó để tuyên bố đạt bonus. Cần test mới chưa dùng để chỉnh và chấm từng câu theo PDF gốc.

Ngưỡng advanced là **63/70**, không phải 90% trên 56 câu có đáp án. Giữ cả 14 câu thiếu evidence và mọi lỗi/timeout/missing trong mẫu số. Basic không có yêu cầu accuracy tuyệt đối 90%.

Không nhập `auto.json` vào UI rồi gọi đó là `summary.json` đã review. Phòng thử nghiệm nhận output của `tools.py score` sau khi có nhãn đúng định dạng; hiện chưa có bộ review hoàn chỉnh. Trình bày bảng proxy trong báo cáo và ghi nhãn rõ ràng.

**10. Bộ câu hỏi để thử trên chat**

“Đã chạy web” chỉ có nghĩa đã quan sát một lượt tích hợp thành công; không bảo đảm lần nào model cũng trả lời giống nhau. “Đã đối chiếu nguồn” nghĩa là có đáp án trong PDF, chưa xác nhận bằng một lượt riêng với cấu hình UI hiện tại. Không đưa các đáp án dưới đây vào prompt hệ thống hoặc truy vấn runtime.

| # | Câu hỏi có thể sao chép | Đáp án/hành vi cần kiểm | Trang PDF | Trạng thái |
|---|---|---|---|---|
| 1 | Doanh thu của FPT năm 2025 là bao nhiêu, đơn vị gì? | 70.113 tỷ VNĐ | 10 | Đã chạy web |
| 2 | Còn năm 2024 thì sao? | Hỏi tiếp câu 1; khoảng 62.849 tỷ VNĐ; bảng chi tiết 62.848.794 triệu VNĐ | 10 hoặc 214 | Đã chạy web |
| 3 | Báo cáo có công bố ROE riêng cho từng quý trong năm 2025 không? Nếu có, cho biết từng quý. | Từ chối phần quý; không suy từ ROE năm | Nguồn ROE năm có ở 59; không có evidence quý trong benchmark | Đã chạy web, abstain |
| 4 | Theo biểu đồ doanh thu 2021–2025, doanh thu có tăng liên tục không và năm 2025 gấp khoảng bao nhiêu lần 2021? | Tăng liên tục; 35.657 → 70.113 tỷ; khoảng 1,966 lần | 10 | Đã đối chiếu nguồn |
| 5 | Theo bảng ESG, tỷ lệ sử dụng bóng đèn LED thực tế 2025 và cam kết 2026 là bao nhiêu? | 88%; 100%; đúng hàng 8, không lấy 95% của hàng khác | 115 | Đã đối chiếu ảnh nguồn |
| 6 | Bốn công ty con thuộc Khối Công nghệ trong sơ đồ tổ chức là gì? | FPT Software, FPT IS, FPT Digital, FPT Smart Cloud | 31 | Đã đối chiếu ảnh nguồn |
| 7 | Hai công ty thuộc nhánh Công ty liên kết trong sơ đồ là gì? | Synnex FPT và FPT Retail | 31 | Có trace dev đúng/sai để so sánh; nguồn đã kiểm |
| 8 | Nhánh Khối Giáo dục, Đầu tư và Khác nối với hai công ty con nào? | FPT Education và FPT Investment | 31 | Đã đối chiếu ảnh nguồn |
| 9 | Trần sở hữu nước ngoài, tỷ lệ đang nắm giữ và chênh lệch là bao nhiêu? Có suy ra số cổ phiếu room chính xác từ hai tỷ lệ này không? | 49%; 38,73%; 10,27 điểm phần trăm; không suy số cổ phiếu chính xác từ tỷ lệ làm tròn | 32, 33 | Đã đối chiếu nguồn; câu khó về điều kiện |
| 10 | Theo biểu đồ ROE 2021–2025, năm nào cao nhất và mức bao nhiêu? | 2024; 28,5% | 11 | Đã đối chiếu nguồn |
| 11 | Trong báo cáo, Giám đốc Nhân sự được Forbes vinh danh Top 30 Under 30 năm 2020 là ai? | Ông Chu Quang Huy | 43 | Có gold dev và nội dung nguồn tương ứng |
| 12 | Chỉ từ biểu đồ doanh thu 2021–2025, cho biết doanh thu 2020 chính xác tới VNĐ. | Từ chối suy ngoài miền năm và độ chính xác của biểu đồ | 10 | Ca thiếu evidence trong dev; chưa chạy web riêng |
| 13 | Từ tỷ lệ nữ và tổng nhân sự nước ngoài, tính chính xác số nữ người nước ngoài giữ chức quản lý. | Từ chối: thiếu bảng chéo giới tính × quốc tịch × cấp quản lý | Không có đủ tập evidence | Ca thiếu evidence trong dev; chưa chạy web riêng |

Nếu muốn thể hiện đủ text/table/chart/image/multi-hop, dùng câu 11/5/4/7/9. Với demo ngắn, câu 1/2/3 là ba lượt có bằng chứng chạy web sẵn; thêm câu 5 hoặc 7 sau khi người trình bày tự tập trước.

**11. Câu hỏi phản biện và câu trả lời gợi ý**

| Câu hỏi có thể được hỏi | Cách trả lời |
|---|---|
| RAG khác hỏi model thông thường ở đâu? | Hệ thống truy xuất evidence từ corpus xác định trước khi trả lời; có nguồn và trace để kiểm tra. Nó vẫn có thể đọc sai evidence, nên RAG không tự bảo đảm đúng. |
| Có fine-tune model trên báo cáo không? | Không. Dự án index tài liệu và đưa evidence vào context lúc hỏi. |
| Tại sao dùng cùng embedding với Day 6? | Query và vector lưu phải dùng cùng model/revision/chiều để cosine có ý nghĩa. Dự án dùng bge-m3 1.024 chiều và revision được ghi trong code. |
| Dense và BM25 khác nhau thế nào? | Dense tìm gần về ngữ nghĩa; BM25 dựa trên token, tần suất và độ dài đoạn, có lợi cho tên và số cụ thể. Không phương pháp nào luôn tốt nhất. |
| Vì sao chọn Hybrid? | Hợp nhất hai tín hiệu; trong advanced dev đã lưu, Hit@3 là 50/56 so với dense 43/56. Vẫn cần xem chất lượng cuối và chi phí. |
| Hybrid có cộng raw score không? | Không. RRF cộng theo thứ hạng: với trọng số bằng nhau, mỗi nhánh góp 1/(60 + rank). Score hybrid không phải xác suất câu trả lời đúng. |
| Tại sao không bật rerank mặc định? | Rerank tăng Full@3 advanced dev từ 43/56 lên 46/56 trong thí nghiệm đã lưu, nhưng median retrieval khoảng 2,5 giây so với 51,5 ms và thêm phí model. Chưa chứng minh luôn tăng grounded answer đủ để bù chi phí. |
| Tại sao top-k 5 nhưng trace có 10 candidate? | Ranking câu gốc lưu sâu 10 để đánh giá; chỉ top-k xét vào context. Candidate pool, ranking lưu và context là ba tầng khác nhau. |
| Có giới hạn 6 search không? | Giới hạn 6 bước model, không phải 6 tool call. Một bước có thể gọi nhiều search. |
| 24.000 ký tự bằng bao nhiêu token? | Không có tỷ lệ cố định, nhất là tiếng Việt. Budget là ký tự evidence; token thực đọc từ usage API. |
| Có index ảnh thật không? | Có vùng ảnh/sơ đồ/biểu đồ, bbox và crop; vision tạo mô tả để text embedding truy xuất. Advanced có thể xem lại crop. Không phải tất cả ảnh đều có image embedding riêng. |
| Citation hợp lệ có nghĩa câu trả lời đúng không? | Không. Runtime kiểm ID đã có trong context; người chấm còn phải kiểm nội dung thực sự hỗ trợ từng ý. DEV-039 là ví dụ citation đúng vùng nhưng trả lời sai quan hệ. |
| Không tìm thấy top-k có chứng minh tài liệu không có đáp án không? | Không. Phải xem các lượt tìm bổ sung và kiểm tra thiếu evidence của benchmark. Từ chối nhầm được báo riêng. |
| Vì sao 240 câu, có đủ đánh giá không? | 100 basic và 140 advanced, chia đôi dev/test; có nhóm nội dung, phép tính, multi-hop và 20% câu thiếu evidence. Số lượng hỗ trợ coverage, nhưng không thay cho gold tốt, test độc lập và người chấm. Không tuyên bố 240 đại diện cho mọi báo cáo. |
| 60 system case có tính vào accuracy advanced không? | Không. Advanced accuracy có mẫu số 70 câu test đã công bố. Ca hệ thống kiểm tra vận hành và hợp đồng dữ liệu riêng. |
| E2 đạt 91,4% thì được bonus chưa? | Chưa đủ cơ sở. Nhãn chưa human-reviewed và test đã được dùng để chẩn đoán trước khi sửa. Cần test mới, review toàn bộ và đầy đủ artifact. |
| Sao UI vẫn dùng mini khi E2 tốt hơn? | Web hiện nối cấu hình mini v1 để demo luồng thực; E2 là cấu hình CLI khác. Muốn demo đúng E2 cần thêm/chọn preset E2 rõ ràng và kiểm tra lại; không tự nhận UI đang là E2. |
| Hai lần baseline lệch nhau nói lên điều gì? | Có biến động đầu ra. Hai lần chạy chưa đủ để khẳng định một khoảng tin cậy hay mọi chênh lệch nhỏ đều có/không có ý nghĩa. Cần lặp có thiết kế để ước lượng. |
| B1 có phải hai lượt model độc lập với baseline không? | Không. B1 áp dụng citation expansion xác định lên cùng trace; phù hợp so sánh theo cặp nhưng cần ghi rõ, không tính hai lần chi phí inference. |
| Lịch sử chat có làm rò gold không? | Chat chỉ nhận câu hỏi, config whitelist và tối đa sáu tin nhắn user/assistant. Backend không đọc gold. Người dùng vẫn không nên tự dán đáp án chuẩn nếu đang muốn đo năng lực độc lập. |
| Vì sao không import auto.json để hiện điểm ngay? | UI nhập summary của evaluator có nhãn review. Đổi tên file hoặc gán nhãn human_confirmed giả không biến proxy thành bằng chứng chấm thật. |
| Bấm Dừng có hủy phí API đã phát sinh không? | Không. Nó ngắt stream và chặn bước tiếp theo; request model đã gửi có thể tiếp tục đến khi hoàn tất/timeout. |

**12. Nếu demo gặp lỗi**

| Tình huống | Xử lý và lời giải thích |
|---|---|
| Lượt đầu chậm | Chờ model embedding nạp; dùng lượt đã khởi động để trình bày. Không đổi câu liên tục hoặc chạy nhiều backend để chữa chậm. |
| Backend báo đang bận sau khi Dừng | Đợi request đang bay kết thúc. Dừng có tính phối hợp, không thu hồi request đã gửi. |
| Agent trả sai | Mở citation, chỉ rõ sai ở retrieval, context hay đọc/tính toán; ghi nhận lỗi thật. Không lặp nhiều lần rồi chỉ trưng kết quả thuận lợi như tỷ lệ thành công. |
| Không có ảnh crop | Mở PDF đầy đủ tại đúng trang và dùng bbox/metadata để đối chiếu. |
| Không có API/mạng | Trình bày trace đã lưu, nói rõ là replay kết quả trước. Không gọi đó là live demo. |
| Phòng thử nghiệm chưa có điểm | Mở bảng proxy trong báo cáo, giải thích đang thiếu review. Không sửa nhãn để UI hiện pass. |

**Câu kết thúc gợi ý**

> Phần đã chứng minh là pipeline chạy thật từ PDF đến retrieval, context, answer và citation, có trace và đo chi phí. Các thí nghiệm cho thấy sửa index và cách đọc evidence có tác động rõ, nhưng số điểm hiện tại vẫn cần quy trình chấm độc lập. Việc tiếp theo là chốt cấu hình muốn đánh giá, tạo test mới nếu đã dùng test cũ để chỉnh, và đối chiếu từng câu với tài liệu gốc.

**Nguồn đối chiếu trong repo**

- [PDF gốc](../pdf/BCTN_2025_ad403f779b.pdf): trang 10, 11, 31, 32, 33, 43, 115, 214; ảnh trang 31 và 115 đã được xem trực tiếp khi soạn.
- [Code adapter web](../src/web_api.py), [agent](../src/agent.py), [retrieval](../src/retrieval.py), [UI README](../web/README.md).
- [Báo cáo và phân tích lỗi](individual/2A202603994_NguyenVanHaiQuan.md), [tiêu chí chọn cấu hình](selection_criteria.md).
- Kết quả gốc: `starter/results/retrieval/*.json`, `starter/results/agent/*/auto.json`, `traces.json`; lấy đúng suite/split/config nêu trong bảng.
- [Benchmark](../BENCHMARK.md), [advanced](../ADVANCED.md), [rubric](../RUBRIC.md), [hướng dẫn trình bày](../GUIDE.md).
