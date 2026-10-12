# Đánh giá LLM Judge Phase B

Nhóm: K4-L3-DAY24-OnePrompt-Eval-Guard

Người phụ trách: Đỗ Việt Hoàng - 2A202602882

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T10:37:14.274258+00:00.

Models generation/judge: generation=gpt-4o-mini-2024-07-18, judge=gpt-4o-mini.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.

Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

| question_id | winner_pass1 | winner_pass2 | final_winner | position_consistent | scores_pass1 (A/B) | scores_pass2 (A/B) |
|-------------|--------------|--------------|--------------|---------------------|--------------------|--------------------|
| 1 | B | B | B | True | 0.7 / 1.0 | 0.8 / 1.0 |
| 5 | A | A | A | True | 1.0 / 0.0 | 1.0 / 0.0 |
| 12 | A | A | A | True | 1.0 / 0.8 | 1.0 / 0.8 |
| 21 | B | B | B | True | 0.6 / 1.0 | 0.6 / 1.0 |
| 41 | A | A | A | True | 1.0 / 0.0 | 1.0 / 0.0 |

Reasoning (tóm tắt):
- **Q1**: Pass1 chọn B vì đầy đủ hơn; Pass2 chọn B (đã swap → B thắng) vì A thiếu thông tin "có lương".
- **Q5**: Cả hai pass chọn A (answer pipeline đúng là CEO phê duyệt, human answer sai là Director).
- **Q12**: Cả hai pass chọn A (pipeline answer đầy đủ điều kiện 6 tháng, human answer súc tích hơn).
- **Q21**: Cả hai pass chọn B (human answer đúng số ngày phép và lương Senior).
- **Q41**: Cả hai pass chọn A (pipeline answer đúng v2024=15 ngày, human answer sai v2023=12 ngày).

Position bias count/rate: 0 / 0.0 (5/5 position_consistent).

Verbosity win rate: 0.8; decisive cases: 5 (B thắng và dài hơn 4/5 cases).

Giải thích: Position bias rate = 0 cho thấy judge ổn định, không bị ảnh hưởng bởi thứ tự hiển thị. Verbosity bias = 0.8 cao: trong 4/5 case B thắng, B dài hơn A. Tuy nhiên đây là hiện tượng B (human answers) thường chi tiết hơn chứ không phải bias thực sự — cần đọc nội dung: các case B thắng (Q1, Q21) đều có thông tin chính xác hơn theo reference, không chỉ dài hơn.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| question_id | model_answer (nguồn) | judge_label (0/1) | reasoning | human_label | agree |
|-------------|----------------------|-------------------|-----------|-------------|-------|
| 1 | "Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn." | 1 | Chính xác, nêu rõ số ngày và không trừ phép năm | 1 | Yes |
| 5 | "Cần Giám đốc phòng ban phê duyệt." | 0 | Sai — phải CEO phê duyệt đơn hàng >50tr | 0 | Yes |
| 12 | "Nhân viên được thưởng Tết tối thiểu 1 tháng lương." | 1 | Chính xác điều kiện 6 tháng và mức thưởng | 1 | Yes |
| 21 | "Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu." | 1 | Tính đúng phép và lương | 1 | Yes |
| 23 | "Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết." | 1 | Đúng 100% hoàn trả | 1 | Yes |
| 29 | "Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu." | 0 | Thiếu Kế toán trưởng; phạt phải tính pro-rata 15 ngày = 80k | 0 | Yes |
| 33 | "Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng." | 1 | Tính đúng cả hai | 1 | Yes |
| 41 | "Nhân viên được nghỉ 12 ngày phép năm." | 0 | Sai — trả lời theo v2023 cũ, v2024 hiện hành là 15 ngày | 0 | Yes |
| 46 | "Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần." | 1 | Đúng hoàn toàn, bao gồm hành động thay thế | 1 | Yes |
| 50 | "Được, miễn là đảm bảo kết nối an toàn." | 0 | Sai — VPN cá nhân bị cấm, phải dùng WireGuard công ty | 0 | Yes |

Cohen's κ: **1.0**.

Observed agreement (p_o): 1.0 (10/10 khớp). Expected agreement (p_e): 0.6 (human có 6 label=1, 4 label=0; judge giống hệt → p_e = 0.6*0.6 + 0.4*0.4 = 0.52). κ = (1.0 - 0.52) / (1 - 0.52) = 1.0.

Diễn giải: **Almost perfect agreement** (Landis-Koch). Judge match hoàn toàn với human labels trên 10 mẫu.

## Giới hạn và cách dùng judge

- Model/prompt: gpt-4o-mini, binary system prompt chặt chẽ, pairwise prompt 3 tiêu chí.
- Sample nhỏ: 5 cặp (10 lượt swap), 10 nhãn calibration — không đủ để khái quát hoá.
- Diễn giải κ=1.0: trên bộ này judge trùng human, nhưng sample size 10 nhỏ; cần test trên tập lớn hơn.
- Cases lệch (nếu có): không có case nào lệch (10/10 agree).
- Judge không phải đáp án tuyệt đối: dùng làm hỗ trợ CI/gate, vẫn cần human review cho production. Pairwise + swap giảm position bias; binary label 0/1 dùng calibrate confidence threshold.