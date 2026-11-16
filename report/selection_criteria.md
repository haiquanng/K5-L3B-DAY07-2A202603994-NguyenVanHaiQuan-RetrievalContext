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

## Bổ sung sau khi xem C1/C2 (trước khi chạy C3)

Kết quả advanced dev (proxy strict pass): baseline 53/70, C1 53/70, C2 50/70; giữa các lần chạy có nhiều câu
đổi đạt/không đạt nên chênh lệch ±3 câu có thể là nhiễu. Lỗi chiếm đa số: đáp án đúng (judge 2/2) nhưng citation
là nguồn tương đương khác trang gold, trong khi chunk gold đã có trong context (51–52/56).

- **C3 `c3_prompt_v3`**: prompt v2 + trích mọi chunk nêu trực tiếp số liệu/ý, ưu tiên nguồn gốc câu hỏi nhắc tới.
  Giả thuyết: tăng strict pass nhờ citation phủ evidence gold; không đổi retrieval.
- **Đo nhiễu**: chạy lại baseline lần 2 (`hybrid_k5_r2`). Một cải tiến chỉ được coi là thật nếu vượt baseline nhiều
  hơn mức chênh giữa hai lần chạy baseline; nếu không, giữ cấu hình đơn giản/rẻ hơn theo tiêu chí hoà.
