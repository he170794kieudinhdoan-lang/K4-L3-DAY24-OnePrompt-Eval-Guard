# Nhóm thực hiện K4 Track 3B

Tên nhóm: OnePrompt

Repo chung: https://github.com/he170794kieudinhdoan-lang/K4-L3-DAY24-OnePrompt-Eval-Guard

Trưởng nhóm/người nộp: {{Họ tên và MSSV}}

Ngày lab/deadline áp dụng: 11:59 AM 13/10/2026 (mặc định trong README, chờ thông báo coach nếu điều chỉnh) — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: {{Commit SHA}}

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Nguyễn Việt Hưng | 2A202602972 | Phase A: Task 1–4 (`src/phase_a_ragas.py`); tích hợp m1–m5 + adapter m4; sinh 50 answers; chạy RAGAS live; viết `doc/reports/failure_clusters.md` | Commit `0cef74de1daa7bbfe8cfa1ac9f1d3946921f4e05` trên nhánh `phase-a-nguyenviethung`; `artifacts/answers_50q.json`, `artifacts/ragas_50q.json` |
| 2 | {{Họ tên}} | {{MSSV}} | {{Phase/file/hàm}} | {{Commit/PR/report}} |
| 3 | {{Họ tên}} | {{MSSV}} | {{Phase/file/hàm}} | {{Commit/PR/report}} |

Người tích hợp/chạy batch/nộp link: {{Họ tên, công việc và bằng chứng}}.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler (máy Nguyễn Việt Hưng): Windows 11 Home 10.0.26200, Python 3.11.9, MSVC 14.44 (VS Build Tools 2022) + Windows SDK 10.0.26100 cài ở ổ D: (ổ C không đủ chỗ); build `annoy==1.17.3` thành công.
Virtualenv/dependencies/imports: `py -3.11 -m venv .venv`; `pip install -r requirements/requirements.txt -c requirements/constraints-core.txt`; `pip check` → "No broken requirements found"; import ragas 0.1.22, nemoguardrails 0.10.0, presidio_analyzer, spacy, torch 2.14.1+cpu OK. pip kéo `pyarrow 26` cần NumPy 2 (xung đột với `numpy==1.26.4` nhưng pip check không phát hiện) → hạ `pyarrow==21.0.0`.
Models/Qdrant/50 answers đã chuẩn bị: Qdrant `qdrant/qdrant:v1.9.7` qua Docker; BAAI/bge-m3 và BAAI/bge-reranker-v2-m3 tải về cache HF; `scripts/setup_answers.py --live` sinh 50 answers (20/20/10), cả 50 ở mode `llm` với `gemini-3.5-flash-lite`, không có extractive fallback. Key OpenAI chỉ có gpt-5.x rồi hết credit nên dùng Gemini qua endpoint tương thích OpenAI (`OPENAI_BASE_URL`, model khai trong `.env`). 6/130 chunks dùng enrichment theo luật do lỗi API; 2 PDF scan không có text layer nên không index. NeMo/Presidio mới kiểm tra import, chưa chạy guard runtime (phần Phase C).
Nếu cài full NeMo chưa thành công, ghi lỗi thực tế; không dùng unit test pass
hoặc pip resolve để khẳng định runtime đã chạy.

## INDIVIDUAL

Sao chép mẫu cho mỗi thành viên; tiêu đề họ tên không dấu-MSSV.

### NguyenVietHung-2A202602972

- Phần được giao và phần thực tế đã làm: Phase A. Viết Task 1 `group_by_distribution`, Task 2 `run_ragas_50q` (gọi m4 một lần, kiểm tra đủ dòng/đúng thứ tự/không NaN/trong [0,1], lấy `evaluator_models` từ metadata m4), Task 3 `bottom_10` (diagnosis theo tổ hợp metric + dấu hiệu câu từ chối, contexts trộn phiên bản), Task 4 `cluster_analysis` (matrix worst_metric × distribution, nhóm yếu theo mean thấp nhất, insight tách câu yếu). Đưa m1–m5 từ bài Day 18 vào `src/` và sửa adapter: m4 trả `metadata.evaluator_models`, raise khi thiếu key/lỗi thay vì trả list rỗng, chấm lại thật các dòng NaN; m2 tương thích qdrant-client 1.9; m5 dùng `max_completion_tokens`. `config.py` cho override model qua `.env` (mặc định giữ nguyên starter). Viết `doc/reports/failure_clusters.md`.
- Bằng chứng: commit `0cef74de1daa7bbfe8cfa1ac9f1d3946921f4e05` (nhánh `phase-a-nguyenviethung`); `artifacts/answers_50q.json`, `artifacts/ragas_50q.json` (metadata: generation `gemini-3.5-flash-lite`, evaluator `gemini-3.1-flash-lite` + `BAAI/bge-m3`, created_at 2026-10-12T18:17:53Z); `doc/reports/failure_clusters.md`.
- Cách kiểm tra: `python -m pytest tests/test_phase_a.py` → 6 passed (mock m4); live: `python scripts/setup_answers.py --live` rồi `python scripts/run_experiments.py --phase a --live` → runner validate và lưu `ragas_50q.json`; `python scripts/check_lab.py` → PASS answers_50q.json, Phase A artifact, phase_a_ragas.py, failure_clusters.md. Đọc thủ công answer/contexts/reference của 10 câu bottom để đối chiếu diagnosis.
- Điều đã học: bốn metric RAGAS đo các tầng khác nhau (faithfulness/answer_relevancy cho generation, context_precision/recall cho retrieval) nên phải đọc chung với dữ liệu; matrix worst_metric đếm mọi câu nên metric "phổ biến nhất" (answer_relevancy 25/50, phần lớn ở câu factual 0.94) không phải lỗi thật — nhóm yếu chọn bằng mean (multi_hop 0.657); câu từ chối "Không tìm thấy" bị chấm faithfulness 0 dù không hallucinate; bẫy phiên bản v2023/v2024 làm contexts bị bản cũ chiếm chỗ.
- Giới hạn/cách xử lý: dùng Gemini free tier thay `gpt-4o-mini` (key OpenAI hết credit); `gemini-3.5-flash-lite` hết quota 500 request/ngày giữa lượt chấm đầu nên lượt đó bị dừng, chấm lại bằng `gemini-3.1-flash-lite`; evaluator chấm context_precision=0 cho 14 câu kể cả câu có contexts đúng chủ đề → ghi là giới hạn, không kết luận retrieval sai chỉ từ CP. Sau lượt đo phát hiện diagnosis ghi câu 27 là hallucination (thực ra là câu từ chối) → sửa `_diagnose`/insight và áp lại Task 3/4 trên đúng điểm đã đo, không gọi lại RAGAS, `validate_phase_a` đạt.
- Nguồn/AI hỗ trợ nếu có: m1–m5 lấy từ bài Day 18 của chính tôi (repo K4-Track3A-Day18-NguyenVietHung-02972-Production-RAG). Dùng Claude Code (Anthropic) hỗ trợ cài môi trường, viết/sửa code Phase A, adapter m4 và soạn báo cáo; tôi kiểm chứng bằng unit tests, chạy live thật, `check_lab.py` và đọc lại từng câu bottom 10 so với answer/contexts/reference. Không dùng AI để điền số đo: mọi số trong báo cáo lấy từ `ragas_50q.json`.

### {{HoVaTen}}-{{MSSV}}

- Phần được giao và phần thực tế đã làm: {{Nhiệm vụ, file/hàm, mục đích}}.
- Bằng chứng: {{Commit/PR và artifacts/reports liên quan}}.
- Cách kiểm tra: {{Unit mock hoặc live experiment, lệnh và kết quả}}.
- Điều đã học: {{Khái niệm và cách thể hiện trong bài}}.
- Giới hạn/cách xử lý: {{Vấn đề và kiểm chứng}}.
- Nguồn/AI hỗ trợ nếu có: {{Công cụ, phạm vi, cách tự kiểm chứng}}.

## Cập nhật sau khi nộp

{{Ghi phiên bản nộp; nếu sửa sau deadline, ghi commit/thời điểm/lý do và thông báo
coach cho phép áp dụng bản cập nhật. Nếu không có cập nhật, ghi rõ không có.}}
