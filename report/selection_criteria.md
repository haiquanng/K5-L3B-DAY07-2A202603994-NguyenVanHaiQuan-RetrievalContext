# Tiêu chí chọn cấu hình (ghi trước khi xem kết quả C1/C2)

Ghi ngày 2026-11-16, khi đã có kết quả baseline trên advanced dev, C1 đang chạy và **chưa xem** số liệu của C1/C2.
Chỉ dùng dev; test chỉ chạy một lần sau khi chốt.

## Ứng viên

| Tên | Retrieval | Prompt | view_image | Ghi chú |
|---|---|---|---|---|
| baseline `hybrid_k5` | hybrid RRF (dense bge-m3 + BM25 bigram), top-5 | v1 | không | |
| C1 `c1_prompt_v2` | như baseline | v2 | không | tách vế, đúng đơn vị/ghi chú, không ghép chỉ tiêu khác tập |
| C2 `c2_prompt_v2_view_image` | như baseline | v2 | có | model xem ảnh crop vùng gốc |
| (tuỳ chọn) C3 | hybrid + LLM rerank | tốt nhất của C1/C2 | theo C1/C2 | chỉ chạy nếu C1/C2 còn lỗi xếp hạng |

Các tham số chung: `gpt-5.4-mini`, reasoning low, tối đa 6 bước, ngân sách context 24.000 ký tự, mỗi chunk tối đa
2.500 ký tự.

## Tiêu chí

1. **Chính:** strict pass (proxy + LLM judge) trên **advanced dev** (70 câu). Cao hơn là tốt hơn.
2. **Ràng buộc** (cấu hình vi phạm bị loại):
   - 0 câu `error`/`timeout`;
   - từ chối đúng ≥ 12/14 câu thiếu bằng chứng; từ chối nhầm ≤ 3/56 câu có đáp án;
   - trên **basic dev** (50 câu), strict pass không thấp hơn baseline quá 2 câu.
3. **Hoà** (chênh ≤ 2 câu strict pass): chọn cấu hình rẻ hơn (USD/câu), rồi p95 latency thấp hơn.
4. Rerank chỉ được chọn nếu tăng strict pass advanced dev ≥ 3 câu so với cấu hình không rerank tương ứng
   (vì thêm ~2,4 s và ~$0.005 mỗi lượt search).

## Sau khi chốt

- Ghi `run_manifest` (commit, model, index/hash, cấu hình) trước khi chạy test.
- Chạy **baseline và cấu hình đã chọn** trên toàn bộ test của cả hai suite, mỗi suite một lần; không sửa
  pipeline sau khi xem test. Nếu phải sửa, tạo test mới và ghi rõ.
- Kết quả test báo cáo bằng **nhãn người chấm** (`tools.py score`); proxy/LLM judge chỉ là tham khảo.
