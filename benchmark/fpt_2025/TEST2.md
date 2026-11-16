# Advanced test2 — bộ test giữ lại (held-out) sau vòng cải thiện E2

Tạo ngày 2026-11-16 **sau** khi bộ `advanced.test` đã bị đọc để chẩn đoán (không còn độc lập), và **trước** khi chạy
bất kỳ cấu hình nào trên bộ này. Mục đích: đánh giá E2 đã đóng băng (`starter/results/runs/E2.test.manifest.json`).

- 30 câu: bảng 6, ảnh/sơ đồ 5, biểu đồ 5, multi-hop 4, text 4 (có đáp án) + 6 thiếu bằng chứng — đúng tối thiểu ADVANCED.md §2.
- **Chọn trang:** chỉ dùng trang không có trong gold/absence_check của 240 câu cũ; random seed cố định `fpt-heldout-test2-v1`
  theo nhóm (`test2_page_picks.json`). Biểu đồ chỉ còn 3 trang chưa dùng (48, 65, 152) nên 5 câu biểu đồ lấy từ các chuỗi khác nhau.
- **Đáp án:** đọc từ text layer và ảnh trang gốc, không chạy hệ thống khi soạn; mọi quote được kiểm có trên đúng trang,
  phép tính được kiểm (`build_test2.py`). Câu thiếu bằng chứng có tìm toàn văn 232 trang (một câu ứng viên về thù lao BKS bị loại vì có công bố ở trang 108, 215).
- **Giới hạn:** người soạn (Claude) đã biết điểm mạnh/yếu của hệ thống; random trang giảm nhưng không loại bỏ thiên lệch này.
  Chưa có người duyệt độc lập (`independent_reviewer_pending`).
- Hash: `gold/advanced.test2.json` a68f4972…d6a8c; `queries/advanced.test2.json` 2b1a7ede…a6d2e.
- Chạy một lần: `python -m src.run_agent --suite advanced --split test2 --allow-test --name E2_gpt54_v4 --model gpt-5.4 --prompt v4 --cite-expand --decompose`.
