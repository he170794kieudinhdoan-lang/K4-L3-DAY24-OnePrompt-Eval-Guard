# Nhóm thực hiện K4 Track 3B

Tên nhóm: {{Tên nhóm}}

Repo chung: {{Link repo}}

Trưởng nhóm/người nộp: {{Họ tên và MSSV}}

Ngày lab/deadline áp dụng: {{Ngày giờ theo thông báo lớp}} — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: {{Commit SHA}}

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Trần Quốc Khánh | 2A202602824 | Phase C: Presidio PII, NeMo input/output rails, adversarial suite và đo P95 input guard | `src/phase_c_guard.py`, `guardrails/config.yml`, `tests/test_phase_c.py`, `artifacts/guard_results.json` |
| 2 | {{Họ tên}} | {{MSSV}} | {{Phase/file/hàm}} | {{Commit/PR/report}} |
| 3 | {{Họ tên}} | {{MSSV}} | {{Phase/file/hàm}} | {{Commit/PR/report}} |

Người tích hợp/chạy batch/nộp link: {{Họ tên, công việc và bằng chứng}}.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: {{Phiên bản thực tế}}.
Virtualenv/dependencies/imports: {{Lệnh và kết quả}}.
Models/Qdrant/50 answers đã chuẩn bị: {{Bằng chứng và giới hạn/fallback}}.
Nếu cài full NeMo chưa thành công, ghi lỗi thực tế; không dùng unit test pass
hoặc pip resolve để khẳng định runtime đã chạy.

## INDIVIDUAL

Sao chép mẫu cho mỗi thành viên; tiêu đề họ tên không dấu-MSSV.

### TranQuocKhanh-2A202602824

- **Phần được giao và đã thực hiện:** Phụ trách Phase C (Tasks 9a–12). Trong `src/phase_c_guard.py`, hoàn thiện quét và ẩn danh CCCD/CMND, số điện thoại Việt Nam và email bằng Presidio; gọi NeMo input/output rails theo quyết định `activated_rails`; chạy bộ adversarial cùng clean controls; đo tuần tự Presidio và NeMo input với hai lượt warm-up, 20 mẫu timed và percentile nội suy tuyến tính. Điều chỉnh policy trong `guardrails/config.yml` để cho phép câu hỏi về quy định mật khẩu nhưng chặn yêu cầu lấy mật khẩu và nội dung ngoài phạm vi. Bổ sung test chống chặn nhầm từ các entity NER không thuộc chính sách PII.
- **Bằng chứng:** `src/phase_c_guard.py`, `guardrails/config.yml`, `tests/test_phase_c.py` và kết quả chạy thật `artifacts/guard_results.json` (metadata ghi guard model `gpt-4o-mini`). Chưa có commit/PR riêng tại thời điểm viết mục này; nhóm cần ghi commit dùng để nộp ở đầu tài liệu.
- **Cách kiểm tra:** Chạy `.venv/Scripts/python.exe -m pytest tests/test_phase_c.py -q`: 13/13 test pass. Chạy `.venv/Scripts/python.exe scripts/run_experiments.py --phase c --live --latency-samples 20`, sau đó `.venv/Scripts/python.exe scripts/check_lab.py`: `PASS Phase C artifact`. Report cuối ghi 20/20 attacks bị chặn, 8/8 clean inputs được cho qua (false-positive rate 0), và 4/4 output cases đúng; hai output sạch được giữ nguyên, hai output nhạy cảm được thay thế.
- **Điều đã học:** Chỉ đếm attacks sẽ che giấu lỗi chặn mọi câu hỏi; 8 clean controls cho thấy false positives. Model NER tiếng Anh của Presidio từng gán các cụm tiếng Việt về chính sách thành `PERSON`, nên tầng chặn PII chỉ dùng các loại identifier mà đề bài yêu cầu. Latency phải đo từ raw samples, loại warm-up và tính P95 trên tổng thời gian của từng mẫu thay vì cộng P95 của từng tầng.
- **Giới hạn và cách xử lý:** Input guard P95 là 843,513 ms (Presidio 16,799 ms; NeMo input 832,459 ms), vượt mục tiêu 500 ms. Đây là phép đo `input_layers_sequential`, chưa đo RAG, output rail hoặc full request có short-circuit; không dùng nó để kết luận độ trễ toàn hệ thống. Bộ 20 attacks, 8 clean inputs và 4 output cases chỉ là mẫu kiểm thử của lab; nhóm cần đưa số đo và kế hoạch cải thiện NeMo vào blueprint chung.
- **Nguồn/AI hỗ trợ:** Dùng Codex hỗ trợ rà soát mã, phân tích report, sửa lọc entity Presidio và diễn đạt policy NeMo. Kết quả được đối chiếu bằng test offline, bộ dữ liệu mẫu, batch chạy thật và checker của repo; không dùng AI để tạo số liệu giả.

## Cập nhật sau khi nộp

{{Ghi phiên bản nộp; nếu sửa sau deadline, ghi commit/thời điểm/lý do và thông báo
coach cho phép áp dụng bản cập nhật. Nếu không có cập nhật, ghi rõ không có.}}
