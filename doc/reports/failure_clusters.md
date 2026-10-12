# Phân tích lỗi Phase A

Nhóm: OnePrompt

Người phụ trách: Nguyễn Việt Hùng — 2A202602972

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T18:17:53Z (01:17 ngày 13/10/2026, UTC+07:00).
Generation mode/fallback và điều kiện chạy: cả 50 answers ở mode `llm` (không có extractive fallback),
sinh bằng `scripts/setup_answers.py --live` qua pipeline m1 (hierarchical chunking) → m5 (enrichment)
→ m2 (BM25 + BGE-M3 dense trên Qdrant v1.9.7, RRF) → m3 (bge-reranker-v2-m3, top-3) → generation.
Corpus có 26 tài liệu / 130 child chunks; 2 PDF scan (BCTC, Nghị định 13) không có text layer nên bị
bỏ qua. 6/130 chunks lỗi enrichment (5 lần JSON hỏng, 1 lần 429) và rơi về enrichment theo luật.
Models generation/evaluator: generation `gemini-3.5-flash-lite`; evaluator `gemini-3.1-flash-lite`
(LLM của RAGAS) + `BAAI/bge-m3` (embedding cho answer_relevancy, chạy local) — lấy từ
`metadata.evaluator_models` của m4. Lý do khác cấu hình mặc định `gpt-4o-mini`: key OpenAI của nhóm
chỉ mở model gpt-5.x rồi hết credit, nên chuyển sang Gemini qua endpoint tương thích OpenAI.
Evaluator khác model generation vì `gemini-3.5-flash-lite` hết quota free-tier 500 request/ngày giữa
lượt chấm đầu (lượt đó bị dừng, không lưu). Gemini không hỗ trợ `n>1` nên answer_relevancy dùng
strictness=1.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 1.000 | 0.810 | 0.950 |
| answer_relevancy | 0.892 | 0.740 | 0.879 |
| context_precision | 0.950 | 0.400 | 0.800 |
| context_recall | 0.925 | 0.679 | 0.725 |
| avg_score | 0.942 | 0.657 | 0.838 |

## Bottom 10 và nguyên nhân

Diagnosis/suggested_fix dưới đây là output của Task 3 (`bottom_10`) đúng như trong JSON (rút gọn
phần lặp lại điểm số). Cột "Đối chiếu thủ công" là nhận xét sau khi đọc answer/contexts/reference.

| Rank | ID | Distribution | avg | worst_metric | Diagnosis (Task 3) | Suggested fix (Task 3) | Đối chiếu thủ công |
|---|---|---|---|---|---|---|---|
| 1 | 27 | multi_hop | 0.000 | faithfulness | Trả "Không tìm thấy"; evaluator chấm CR=0 | Trả lời phần có căn cứ, tính từng bước, tăng top_k | Contexts CÓ đoạn phép năm v2024 và quy tắc thâm niên v2024; model không tự tính 15+2−4=13 → lỗi generation |
| 2 | 39 | multi_hop | 0.250 | answer_relevancy | Trả "Không tìm thấy"; CR=0; contexts trộn v1.0/v2.0 | Như trên + lọc bản hiện hành theo metadata | Contexts có yêu cầu v2.0 nhưng thiếu đoạn yêu cầu của v1.0 → thiếu một vế so sánh, model từ chối cả câu |
| 3 | 33 | multi_hop | 0.375 | answer_relevancy | Trả "Không tìm thấy"; contexts phủ một phần (CR=0.50) | Như trên | 3 contexts đều về phép năm, thiếu `phu_cap.md` → retrieval chỉ lấy 1 trong 2 tài liệu cần ghép |
| 4 | 22 | multi_hop | 0.479 | context_precision | Contexts lấy sai tài liệu, đoạn liên quan xếp thấp | Query rewrite, lọc metadata nguồn | 2/3 contexts đúng (`mua_sam.md`), 1 đoạn `tam_ung.md` lạc đề; answer thiếu ý "3 báo giá" và có F=0.50 |
| 5 | 49 | adversarial | 0.538 | context_precision | Như rank 4 | Như rank 4 | Contexts là v2024 + 2 đoạn v2023; answer nêu đúng 12 → 15 ngày và chỉ ra v2024 hiện hành nhưng bỏ quy tắc thâm niên |
| 6 | 37 | multi_hop | 0.540 | context_precision | Như rank 4 | Như rank 4 | Cả 3 contexts từ `bao_mat_su_co.md`, đúng chủ đề; thiếu `phan_loai_du_lieu.md` → CP=0 khó giải thích (xem phần giới hạn) |
| 7 | 35 | multi_hop | 0.556 | context_precision | Như rank 4 | Như rank 4 | Contexts đúng (thử việc + bảng lương); answer không tính ra 10.200.000 và bỏ số tiền phụ cấp |
| 8 | 41 | adversarial | 0.571 | context_precision | Như rank 4 | Như rank 4 | Bẫy phiên bản: answer liệt kê ngang hàng 15 ngày (2024) và 12 ngày (2023), không khẳng định v2024 là hiện hành |
| 9 | 21 | multi_hop | 0.605 | context_precision | Trả "Không tìm thấy" một phần; CR=0.50 | Trả lời phần có căn cứ, tăng top_k | Đúng 18 ngày phép nhưng 2/3 contexts là v2023, không có `bang_luong_2024.md` → báo không tìm thấy lương |
| 10 | 29 | multi_hop | 0.613 | context_precision | Như rank 4 | Như rank 4 | Cả 3 contexts từ `tam_ung.md`, đúng chủ đề; answer đúng người duyệt nhưng không tính phạt 80.000 VNĐ |

Ba nhóm nguyên nhân rút ra sau khi đọc từng câu:

1. **Generation từ chối quá mức (27, 39, 33, một phần 21).** System prompt của setup là
   "Trả lời CHỈ dựa trên context. Nếu không có → nói 'Không tìm thấy.'". Với câu multi-hop cần ghép
   hoặc tính toán, chỉ cần thiếu một mảnh là model từ chối toàn bộ, kể cả phần contexts đã đủ (câu 27
   có đủ dữ kiện). Câu từ chối không có khẳng định nào nên RAGAS chấm faithfulness/answer_relevancy về 0
   — đây không phải hallucination.
2. **Retrieval chỉ lấy một trong hai tài liệu cần ghép (33, 21, 37, 39).** Top-3 sau rerank bị chiếm
   bởi nhiều chunk của cùng một tài liệu (hoặc cả v2023 lẫn v2024 của cùng chủ đề), nên tài liệu thứ hai
   (`phu_cap.md`, `bang_luong_2024.md`, `phan_loai_du_lieu.md`, mục yêu cầu của `mat_khau_v1.md`) bị đẩy ra.
3. **Phiên bản cũ chiếm chỗ (41, 49, 21).** Với câu về phép năm, 2/3 contexts là `nghi_phep_nam_v2023.md`.
   Answer 41 trình bày v2023 và v2024 ngang hàng thay vì ưu tiên bản hiện hành; câu 21 tính đúng nhờ
   đoạn thâm niên v2024 nhưng mất chỗ cho bảng lương.

## Matrix và nhóm yếu nhất

Mỗi câu được đếm một lần theo worst_metric của nó (tổng mỗi cột = 20/20/10 là kích thước nhóm, không
phải số lỗi).

| worst_metric | factual | multi_hop | adversarial | Tổng |
|---|---|---|---|---|
| faithfulness | 0 | 4 | 1 | 5 |
| answer_relevancy | 17 | 5 | 3 | 25 |
| context_precision | 2 | 9 | 2 | 13 |
| context_recall | 1 | 2 | 4 | 7 |

Nhóm yếu theo mean thấp nhất: multi_hop; mean: 0.657 (factual 0.942, adversarial 0.838).
Worst metric xuất hiện nhiều nhất: answer_relevancy; số câu: 25.

answer_relevancy đứng đầu matrix chỉ vì 17 câu factual có ba metric còn lại gần 1.0, nên metric thấp
nhất của chúng là answer_relevancy (trung bình 0.815 tại 25 câu đó) — không phải lỗi thật. Khi chỉ xét
12 câu có avg_score < 0.7 thì worst_metric là context_precision 8, faithfulness 2, answer_relevancy 2;
cả 12 câu yếu đều thuộc multi_hop (10) hoặc adversarial (2: câu 41, 49), không có câu factual nào. multi_hop yếu nhất vì cả bốn metric đều thấp nhất trong ba
nhóm, rõ nhất là context_precision 0.400 và context_recall 0.679: câu hỏi cần 2 tài liệu nhưng top-3
contexts thường chỉ phủ một tài liệu, và khi thiếu mảnh thì generation từ chối.

Đề xuất sửa và cách kiểm chứng:

1. **Đa dạng nguồn trong top-k:** sau rerank giới hạn tối đa 2 chunk/tài liệu và tăng `RERANK_TOP_K`
   từ 3 lên 5 cho câu có nhiều ý (hoặc tách câu multi-hop thành query con). Kiểm chứng: chạy lại setup +
   Phase A, so context_recall và avg_score của multi_hop với 0.679 / 0.657 hiện tại; theo dõi riêng
   câu 21, 33, 37, 39.
2. **Ưu tiên bản hiện hành:** gắn metadata `version`/`superseded` khi index, lọc hoặc hạ điểm bản đã bị
   thay thế trước rerank. Kiểm chứng: câu 41, 49, 21 không còn chunk v2023 chiếm 2/3 contexts, answer 41
   khẳng định 15 ngày theo v2024.
3. **Sửa prompt generation:** cho phép trả lời phần có căn cứ, nêu rõ phần thiếu, và tính từng bước khi
   câu hỏi có phép tính. Kiểm chứng: số câu chứa "Không tìm thấy" giảm từ 4 (21, 27, 33, 39), câu 27 ra
   13 ngày, đồng thời faithfulness của factual không giảm khỏi 1.0.

## Bẫy adversarial và giới hạn

Adversarial mean 0.838 thấp hơn factual 0.942 nhưng cao hơn multi_hop 0.657. Hai câu adversarial thấp
nhất đều là bẫy phiên bản phép năm (41: 0.571, 49: 0.538). Retrieval lấy được bản v2024 nhưng luôn kèm
2 đoạn v2023; ở câu 49 model nhận ra v2024 là hiện hành vì câu hỏi nói rõ "cũ (v2023)", còn ở câu 41
(hỏi trống không phiên bản) model liệt kê cả hai bản như nhau. Điểm thấp hơn của nhóm adversarial vì vậy
chưa chứng minh pipeline nhận ra version conflict: nó chỉ xử lý được khi câu hỏi tự gợi ý phiên bản.
Các câu adversarial còn lại (42–48, 50) đạt 0.75–0.99.

Giới hạn của lượt đo:

- **Evaluator không ổn định ở context_precision.** `gemini-3.1-flash-lite` chấm CP=0 cho 14 câu, kể cả
  câu 29 và 37 có cả ba contexts đúng tài liệu và đúng chủ đề khi đọc thủ công. Vì vậy chẩn đoán
  "contexts lấy sai tài liệu" của Task 3 cho các câu này (dựa thuần vào điểm CP) chỉ đúng một phần: lỗi
  thật là thiếu tài liệu thứ hai và thiếu phép tính, không phải lấy sai tài liệu. Cần chấm lại bằng
  evaluator mạnh hơn trước khi dùng CP làm CI gate.
- **Mẫu nhỏ:** 50 câu, adversarial chỉ 10 câu; chênh lệch vài câu đổi mean nhiều.
- **Model khác cấu hình chuẩn:** Gemini free tier thay `gpt-4o-mini`, generation và evaluator là hai model
  khác nhau, answer_relevancy dùng strictness=1 và embedding BGE-M3 local nên điểm không so trực tiếp
  được với nhóm dùng OpenAI.
- **Task 3/4 được áp lại một lần trên cùng điểm đã đo:** sau khi đọc kết quả, phát hiện diagnosis ghi câu
  27 là "hallucination" trong khi answer là câu từ chối. Đã sửa `_diagnose` (xét câu từ chối trước) và
  insight Task 4, rồi chạy lại `bottom_10`/`cluster_analysis` trên đúng `per_question` của lượt đo
  (không gọi lại RAGAS; metadata, điểm và hash nguồn giữ nguyên, `validate_phase_a` đạt).
- 6/130 chunks dùng enrichment theo luật do lỗi API; 2 PDF scan không được index.
