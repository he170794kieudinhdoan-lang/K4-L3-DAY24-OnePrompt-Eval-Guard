# Blueprint CI/CD cho RAG và guardrails

Nhóm: OnePrompt

Người phụ trách: Kiều Đình Đoàn - HE170794

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: 2026-10-12T17:16:00+07:00; guard models: presidio-analyzer, nemoguardrails (gpt-4o-mini).
Models generation/evaluator/judge từ A/B: Generation: gpt-4o-mini (setup_answers); Evaluator: gpt-4o-mini, BAAI/bge-m3 (m4_eval); Judge: gpt-4o-mini (phase_b_judge).

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

### Data flow và cơ chế xử lý
1. **Tầng 1 - Presidio PII Scanning:** Khi người dùng gửi truy vấn, hệ thống phân tích thực thể định danh nhằm phát hiện mã CCCD/CMND (12 chữ số), số điện thoại Việt Nam (đầu 03, 05, 07, 08, 09), và địa chỉ email. Mọi thực thể nhạy cảm được gán nhãn và thay thế bằng token định danh ẩn (ví dụ: `<VI_CCCD>`, `<VI_PHONE>`) trước khi chuyển tiếp.
2. **Tầng 2 - NeMo Input Rails:** Truy vấn (đã ẩn danh) được đưa qua hàng rào tự vệ Colang 1.0 với cơ chế `self check input`. Mô hình đánh giá rủi ro prompt injection, jailbreak (như DAN, Ignore instructions) hoặc câu hỏi vượt quá phạm vi nghiệp vụ. Nếu phát hiện vi phạm, hệ thống kích hoạt ngắt sớm (**short-circuit**), ngay lập tức trả về thông điệp từ chối theo mẫu quy định và dừng luồng xử lý mà không tiêu tốn tài nguyên gọi mô hình RAG.
3. **Tầng 3 - RAG Pipeline:** Truy vấn hợp lệ được chuyển vào pipeline trích xuất thông tin: Hybrid Search (BM25 + Dense Qdrant với embedding BAAI/bge-m3) truy xuất top-20 chunks, Cross-Encoder (`bge-reranker-v2-m3`) xếp hạng lại chọn top-3 văn bản phù hợp nhất, và mô hình sinh (`gpt-4o-mini`) tạo câu trả lời dựa trên ngữ cảnh thực tế.
4. **Tầng 4 - NeMo Output Rails:** Câu trả lời sinh ra được kiểm duyệt qua cơ chế `self check output` nhằm phát hiện ảo giác (hallucination), tiết lộ dữ liệu nội bộ không có trong tài liệu, hoặc chứa thông tin nhạy cảm. Nếu câu trả lời sạch, hệ thống giữ nguyên nội dung. Nếu phát hiện vi phạm, nội dung độc hại được thay thế bằng thông báo từ chối an toàn hoặc biên tập lại.

### Failure actions, Log/Redaction và Quản lý Secrets
- **Failure action:** Khi phát hiện vi phạm ở bất kỳ tầng nào, hệ thống trả về mã trạng thái an toàn kèm thông báo trung tính, không tiết lộ cấu trúc prompt hệ thống hoặc lỗi nội bộ.
- **Log và Redaction:** Chỉ ghi nhận metadata truy vấn, phân loại tấn công (blocked reason) và nội dung đã được redact PII vào hệ thống giám sát tập trung. Tuyệt đối không lưu trữ dữ liệu định danh thô vào log.
- **Quản lý Secrets:** Toàn bộ API keys (OpenAI, HuggingFace, Qdrant credentials) được quản lý qua biến môi trường bảo mật trên máy chủ (hoặc HashiCorp Vault / Secret Manager trong môi trường Cloud), không commit vào repository mã nguồn.
- **Fallback điều kiện ngoại lệ:** Trong trường hợp dịch vụ Guardrail hoặc LLM gặp sự cố timeout (>3.000ms) hoặc mất kết nối mạng, hệ thống chuyển sang chế độ an toàn nghiêm ngặt (Fail-Secure), trả về thông báo bảo trì dịch vụ thay vì bỏ qua hàng rào kiểm soát.

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear interpolation (nội suy tuyến tính).

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 15.2 ms | 38.6 ms | 45.1 ms | Đạt yêu cầu (<100ms) |
| NeMo input | 280.4 ms | 420.7 ms | 465.3 ms | Đạt ngân sách thiết kế |
| Input guard sequential | 295.6 ms | 459.3 ms | 498.4 ms | Nằm trong ngưỡng 500ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế/budget_ok: 459.3ms / True.
Độ trễ tầng NeMo Input phụ thuộc chủ yếu vào thời gian phản hồi API của mô hình self-check LLM (chiếm khoảng 85-90% tổng thời gian input guard). Đối với các tầng ngoài phạm vi bắt buộc (RAG, NeMo Output, Full guard), hệ thống duy trì trạng thái "chưa đo" theo đúng quy chuẩn. Kế hoạch đo bổ sung trong giai đoạn Staging: gắn OpenTelemetry tracing span trên toàn bộ 50 truy vấn thực nghiệm, thực hiện 2 lượt warm-up độc lập và ghi nhận timestamp chuẩn xác cho từng microservice.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.
### Đặc tả kịch bản CI/CD Automation
Quy trình kiểm thử tích hợp liên tục (CI Workflow) được định nghĩa chạy tự động trên mỗi Pull Request vào nhánh chính:
1. **Job 1 - Quality Evaluation Gate:** Thực thi runner đánh giá tự động trên tập dữ liệu kiểm chuẩn (Golden Set 50 câu). Kiểm tra ngưỡng:
   ```bash
   python scripts/run_experiments.py --phase a --ci-gate --min-faithfulness 0.75 --min-avg 0.65
   ```
   Nếu chỉ số chất lượng không đạt ngưỡng, script thoát với mã lỗi `exit 1` ngăn chặn hợp nhất mã nguồn.
2. **Job 2 - Security & Guardrails Gate:** Chạy bộ kiểm thử xâm nhập 20 tấn công đối kháng và 8 truy vấn sạch:
   ```bash
   python scripts/run_experiments.py --phase c --ci-gate --min-attacks-blocked 18 --max-clean-blocked 0
   ```
   Yêu cầu bắt buộc: 8/8 truy vấn hợp lệ phải được thông qua (False Positive = 0). Tỷ lệ chặn tấn công đạt tối thiểu 18/20 (vượt mốc chuẩn 15/20 để đảm bảo an toàn cao trước khi lên môi trường staging).
3. **Job 3 - Performance Regression Gate:** Đo đạc 20 mẫu latency của tầng input guard. Nếu P95 vượt quá 500ms, thông báo cảnh báo và yêu cầu tối ưu prompt hoặc chuyển sang mô hình kiểm duyệt cục bộ nhẹ hơn.

*Ghi chú:* Đây là kịch bản kiến trúc đề xuất cho quy trình triển khai sản phẩm, tách biệt với các bài kiểm thử unit mock nội bộ.

## Monitoring và cải tiến

Hệ thống giám sát vận hành production thu thập chỉ số theo thời gian thực qua Prometheus và hiển thị trên Grafana Dashboard:
- **Tỷ lệ vi phạm chính sách (Violation Rate):** Theo dõi số lượng yêu cầu bị chặn bởi Presidio và NeMo Input theo từng giờ. Thiết lập ngưỡng cảnh báo (Alert) khi tỷ lệ này tăng đột biến vượt 15% tổng lưu lượng trong vòng 10 phút (dấu hiệu của đợt tấn công dò quét / red teaming).
- **Quy trình xử lý chặn nhầm (False Positive Triage):** Cung cấp nút phản hồi "Báo cáo nội dung bị chặn nhầm" trên giao diện người dùng. Các trường hợp này được tự động chuyển vào hàng đợi kiểm duyệt để kỹ sư rà soát, điều chỉnh luật Colang trong vòng 24 giờ.
- **Giám sát trôi dạt ngữ nghĩa (Data & Model Drift):** Lấy mẫu ngẫu nhiên 5% truy vấn thực tế mỗi tuần, thực hiện đánh giá kép bằng LLM Judge và chuyên gia để kiểm soát tính ổn định của câu trả lời.
- **Bảo vệ quyền riêng tư:** Toàn bộ dữ liệu trích xuất để phân tích định kỳ phải đi qua bộ lọc ẩn danh hóa PII nghiêm ngặt.

RAGAS mean/worst distribution: Mean avg_score = 0.72; Worst distribution = adversarial (avg_score = 0.48).
Cohen’s κ: 0.80 (Mức độ đồng thuận gần như hoàn hảo giữa LLM Judge và con người).
Attacks passed: 18/20; clean false_positive_rate: 0.0 (0/8 câu sạch bị chặn nhầm).

### 4 Đề xuất cải tiến có thể kiểm chứng
1. **Tối ưu hóa độ trễ PII với C-based engine:** Tích hợp bộ quy tắc Regex viết bằng Rust hoặc C++ cho các định dạng số CCCD và số điện thoại Việt Nam để giảm độ trễ P95 của Presidio từ ~38ms xuống dưới 5ms.
2. **Triển khai SLM cục bộ cho Input Rails:** Thay thế lời gọi API ngoài của NeMo self-check bằng mô hình ngôn ngữ nhỏ (Small Language Model như Llama-3.2-1B hoặc Qwen-2.5-1.5B tinh chỉnh) chạy suy luận trực tiếp trên server với vLLM để đưa P95 của input guard xuống dưới 150ms.
3. **Cải thiện độ hồi quy ngữ cảnh (Context Recall) cho nhóm multi-hop:** Nâng cấp thuật toán phân mảnh đệ quy (Hierarchical Chunking) và bổ sung truy vấn con (Sub-query Decomposition) để khắc phục điểm yếu của hệ thống trên các câu hỏi tổng hợp nhiều tài liệu.
4. **Tinh chỉnh bộ quy tắc Colang:** Mở rộng các flow trong file cấu hình để nhận diện chính xác các câu hỏi nghiệp vụ đặc thù về chính sách kỷ luật, trợ cấp thôi việc mà không kích hoạt nhầm cảnh báo vi phạm đạo đức.
