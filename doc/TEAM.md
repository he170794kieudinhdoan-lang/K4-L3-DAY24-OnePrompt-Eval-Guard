# Nhóm thực hiện K4 Track 3B

Tên nhóm: OnePrompt

Repo chung: https://github.com/he170794kieudinhdoan-lang/K4-L3-DAY24-OnePrompt-Eval-Guard.git

Trưởng nhóm/người nộp: Kiều Đình Đoàn - 2A202602936

Ngày lab/deadline áp dụng: 12/10/2026 23:59 — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: d98f9b47c27678be1687a2853dd55aed6aecba24

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Nguyễn Việt Hùng | 2A202602972 | Phase A Lead: RAGAS 4 metrics, ma trận lỗi và phân tích cụm thất bại (Tasks 1-4) | src/phase_a_ragas.py, artifacts/ragas_50q.json, doc/reports/failure_clusters.md |
| 2 | Đỗ Việt Hoàng | 2A202602882 | Phase B Lead: Pairwise Judge đảo vị trí, tính Cohen's Kappa và báo cáo thiên vị (Tasks 5-8) | src/phase_b_judge.py, artifacts/judge_results.json, doc/reports/bias_report.md |
| 3 | Trần Quốc Khánh | 2A202602824 | Phase C Lead: Quét PII Presidio, NeMo Guardrails luồng vào/ra và đo latency P95 (Tasks 9a-12) | src/phase_c_guard.py, guardrails/config.yml, guardrails/rails.co, artifacts/guard_results.json |
| 4 | Kiều Đình Đoàn | 2A202602936 | Project Lead: Tích hợp pipeline sinh 50 câu, viết CI/CD Blueprint và audit nộp bài | scripts/setup_answers.py, artifacts/answers_50q.json, doc/reports/blueprint.md, doc/TEAM.md |

Người tích hợp/chạy batch/nộp link: Kiều Đình Đoàn (MSSV: 2A202602936), chạy scripts/setup_answers.py tạo 50 câu trả lời, điều phối kiểm thử và nộp repo.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows 11, Python 3.11.9, compiler MSVC C++ Build Tools.
Virtualenv/dependencies/imports: Môi trường ảo .venv tại D:\day 24, cài đặt requirements-test.lock.txt và thư viện RAG (pypdf, underthesea, rank-bm25, qdrant-client, sentence-transformers, flashrank, openai). Chạy thử 60 unit tests scaffold ban đầu passed.
Models/Qdrant/50 answers đã chuẩn bị: Tải trước cache mô hình BAAI/bge-m3 và BAAI/bge-reranker-v2-m3; Qdrant chạy cơ chế in-memory fallback ổn định; đã hoàn thành chạy scripts/setup_answers.py --live sinh đầy đủ 50 câu trả lời (20 factual, 20 multi_hop, 10 adversarial) vào artifacts/answers_50q.json, đạt chuẩn kiểm định validate_answers.
NeMo Guardrails đang được kiểm thử mock offline với cấu hình Colang 1.0 và prompts tự kiểm tra an toàn trong guardrails/.

## INDIVIDUAL

Sao chép mẫu cho mỗi thành viên; tiêu đề họ tên không dấu-MSSV.

### NguyenVietHung-2A202602972

- Phần được giao và phần thực tế đã làm: Phụ trách Phase A trong src/phase_a_ragas.py. Cài đặt hàm group_by_distribution phân loại 50 câu theo 3 tập dữ liệu (20 factual, 20 multi_hop, 10 adversarial), hoàn thiện adapter run_ragas_50q gọi m4 tính 4 độ đo (faithfulness, answer_relevancy, context_precision, context_recall), hàm bottom_10 lọc 10 câu có avg_score thấp nhất kèm chẩn đoán lỗi, và hàm cluster_analysis lập ma trận phân tích điểm yếu cốt lõi của hệ thống.
- Bằng chứng: Mã nguồn src/phase_a_ragas.py, kết quả thực nghiệm artifacts/ragas_50q.json và báo cáo phân tích lỗi doc/reports/failure_clusters.md.
- Cách kiểm tra: Chạy pytest tests/test_phase_a.py để kiểm tra logic hợp đồng và chạy python scripts/run_experiments.py --phase a --live để thu thập dữ liệu đánh giá thực tế.
- Điều đã học: Hiểu rõ cách đánh giá pipeline RAG bằng 4 khía cạnh độc lập; phân biệt rõ giữa số lượng mẫu tuyệt đối của từng phân phối và điểm chất lượng trung bình khi xác định điểm nghẽn chính của hệ thống trích xuất.
- Giới hạn/cách xử lý: Nhóm câu hỏi multi_hop thường có điểm context recall thấp do tài liệu bị phân mảnh ở nhiều file; hướng khắc phục là tăng cường cấu trúc phân mảnh cha-con và bổ sung từ khóa truy vấn.
- Nguồn/AI hỗ trợ nếu có: Tham khảo tài liệu kỹ thuật RAGAS framework và sử dụng trợ lý code để tra cứu cấu trúc dataclass, tự kiểm chứng toàn bộ logic bằng test suite có sẵn.

### DoVietHoang-2A202602882

- Phần được giao và phần thực tế đã làm: Phụ trách Phase B trong src/phase_b_judge.py. Cài đặt hàm pairwise_judge so sánh cặp câu trả lời A/B dựa trên reference ground-truth, hàm swap_and_average thực hiện 2 lượt đánh giá đảo vị trí để triệt tiêu position bias, hàm cohen_kappa tính hệ số đồng thuận giữa 10 nhãn của mô hình và nhãn con người, cùng hàm bias_report thống kê mức độ thiên vị vị trí và độ dài câu trả lời.
- Bằng chứng: Mã nguồn src/phase_b_judge.py, kết quả đánh giá artifacts/judge_results.json và báo cáo doc/reports/bias_report.md.
- Cách kiểm tra: Chạy pytest tests/test_phase_b.py và thực thi python scripts/run_experiments.py --phase b --live trên 5 cặp câu hỏi chuẩn.
- Điều đã học: Hiểu cách hoạt động của LLM as a Judge; nắm vững cơ chế định lượng hiện tượng thiên vị câu trả lời dài (verbosity bias) và cách dùng hệ số Cohen's Kappa để đánh giá độ tin cậy của mô hình đánh giá so với con người.
- Giới hạn/cách xử lý: Mô hình giám khảo có xu hướng ưu tiên câu trả lời dài hơn dù nội dung thừa thãi; giải pháp là siết chặt tiêu chí chấm điểm trong prompt, yêu cầu bám sát các ý thiết yếu trong ground-truth.
- Nguồn/AI hỗ trợ nếu có: Tra cứu công thức toán thống kê về hệ số tương đồng Kappa từ tài liệu mở, tự viết mã nguồn và kiểm chứng logic với các kịch bản biên.

### TranQuocKhanh-2A202602824

- Phần được giao và đã thực hiện: Phụ trách Phase C (Tasks 9a–12). Trong src/phase_c_guard.py, hoàn thiện quét và ẩn danh CCCD/CMND, số điện thoại Việt Nam và email bằng Presidio; gọi NeMo input/output rails theo quyết định activated_rails; chạy bộ adversarial cùng clean controls; đo tuần tự Presidio và NeMo input với hai lượt warm-up, 20 mẫu timed và percentile nội suy tuyến tính. Điều chỉnh policy trong guardrails/config.yml để cho phép câu hỏi về quy định mật khẩu nhưng chặn yêu cầu lấy mật khẩu và nội dung ngoài phạm vi. Bổ sung test chống chặn nhầm từ các entity NER không thuộc chính sách PII.
- Bằng chứng: src/phase_c_guard.py, guardrails/config.yml, tests/test_phase_c.py và kết quả chạy thật artifacts/guard_results.json (metadata ghi guard model gpt-4o-mini).
- Cách kiểm tra: Chạy .venv/Scripts/python.exe -m pytest tests/test_phase_c.py -q: 13/13 test pass. Chạy .venv/Scripts/python.exe scripts/run_experiments.py --phase c --live --latency-samples 20, sau đó .venv/Scripts/python.exe scripts/check_lab.py: PASS Phase C artifact. Report cuối ghi 20/20 attacks bị chặn, 8/8 clean inputs được cho qua (false-positive rate 0), và 4/4 output cases đúng; hai output sạch được giữ nguyên, hai output nhạy cảm được thay thế.
- Điều đã học: Chỉ đếm attacks sẽ che giấu lỗi chặn mọi câu hỏi; 8 clean controls cho thấy false positives. Model NER tiếng Anh của Presidio từng gán các cụm tiếng Việt về chính sách thành PERSON, nên tầng chặn PII chỉ dùng các loại identifier mà đề bài yêu cầu. Latency phải đo từ raw samples, loại warm-up và tính P95 trên tổng thời gian của từng mẫu thay vì cộng P95 của từng tầng.
- Giới hạn và cách xử lý: Input guard P95 là 843,513 ms (Presidio 16,799 ms; NeMo input 832,459 ms), vượt mục tiêu 500 ms. Đây là phép đo input_layers_sequential, chưa đo RAG, output rail hoặc full request có short-circuit; không dùng nó để kết luận độ trễ toàn hệ thống. Bộ 20 attacks, 8 clean inputs và 4 output cases chỉ là mẫu kiểm thử của lab; nhóm cần đưa số đo và kế hoạch cải thiện NeMo vào blueprint chung.
- Nguồn/AI hỗ trợ: Dùng Codex hỗ trợ rà soát mã, phân tích report, sửa lọc entity Presidio và diễn đạt policy NeMo. Kết quả được đối chiếu bằng test offline, bộ dữ liệu mẫu, batch chạy thật và checker của repo; không dùng AI để tạo số liệu giả.

### KieuDinhDoan-2A202602936

- Phần được giao và phần thực tế đã làm: Giữ vai trò trưởng nhóm điều phối, phụ trách tích hợp dữ liệu ban đầu, viết bản thiết kế CI/CD Blueprint và audit toàn bộ bài nộp. Đưa 5 module m1-m5 từ Day 18 vào src/, cấu hình môi trường, chạy scripts/setup_answers.py tạo 50 câu trả lời chuẩn xác, soạn thảo toàn bộ tài liệu kiến trúc tại doc/reports/blueprint.md, tổng hợp doc/TEAM.md và chạy script kiểm định check_lab.py.
- Bằng chứng: Các tệp src/m1_chunking.py đến m5_enrichment.py, kết quả artifacts/answers_50q.json, báo cáo doc/reports/blueprint.md, tệp doc/TEAM.md và log kiểm tra từ scripts/check_lab.py.
- Cách kiểm tra: Chạy python scripts/setup_answers.py --live, kiểm định schema với validate_answers và audit tổng thể với python scripts/check_lab.py --with-tests.
- Điều đã học: Hiểu cách lắp ghép các thành phần từ chunking, hybrid search đến cross-encoder reranking thành một pipeline hoàn chỉnh; nắm vững tư duy thiết kế các cổng kiểm soát chất lượng (Quality Gates) tự động trước khi triển khai hệ thống AI.
- Giới hạn/cách xử lý: Mô hình reranker chạy trên CPU tốn nhiều tài nguyên xử lý; đã cấu hình cơ chế fallback in-memory cho Qdrant để đảm bảo tiến trình tạo 50 câu trả lời diễn ra liên tục, không bị ngắt quãng.
- Nguồn/AI hỗ trợ nếu có: Sử dụng công cụ để tối ưu kịch bản dòng lệnh và kiểm tra tính hợp lệ của JSON Schema, tự rà soát toàn bộ các tiêu chí trong rubric bài lab.

## Cập nhật sau khi nộp

Không có bản cập nhật nào sau khi nộp.
