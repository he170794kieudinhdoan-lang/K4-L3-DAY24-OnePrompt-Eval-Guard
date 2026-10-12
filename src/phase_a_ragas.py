from __future__ import annotations

"""Phase A: RAGAS Production Evaluation — 50q, 3 distributions, cluster analysis."""

import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH, ANSWERS_PATH, ARTIFACTS_DIR
from src.experiment_support import write_json

Distribution = str  # "factual" | "multi_hop" | "adversarial"

DIAGNOSTIC_TREE = {
    "faithfulness":      ("LLM hallucinating", "Tighten system prompt, lower temperature"),
    "context_recall":    ("Missing relevant chunks", "Improve chunking or add BM25"),
    "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
    "answer_relevancy":  ("Answer doesn't match question", "Improve prompt template"),
}


@dataclass
class RagasResult:
    question_id: int
    distribution: Distribution
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float

    @property
    def avg_score(self) -> float:
        return (self.faithfulness + self.answer_relevancy +
                self.context_precision + self.context_recall) / 4

    @property
    def worst_metric(self) -> str:
        scores = {
            "faithfulness":      self.faithfulness,
            "answer_relevancy":  self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall":    self.context_recall,
        }
        return min(scores, key=scores.get)


# ─── Đã implement sẵn ────────────────────────────────────────────────────────

@dataclass
class RagasEvaluation:
    """Task 2 output: measured rows plus model identifiers reported by m4."""
    results: list[RagasResult]
    evaluator_models: list[str]

def load_test_set_50q(path: str = TEST_SET_PATH) -> list[dict]:
    """Load 50q test set với 3 distributions."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_answers(path: str = ANSWERS_PATH) -> list[dict]:
    """Load pre-generated answers từ setup_answers.py."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"answers_50q.json không tìm thấy tại {path}\n"
            "→ Chạy trước: python scripts/setup_answers.py --live"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict]) -> dict:
    """Provided exporter: preserve the student-produced Task 3 rows verbatim."""
    per_dist: dict[str, dict] = {}
    for dist in ["factual", "multi_hop", "adversarial"]:
        subset = [r for r in results if r.distribution == dist]
        if subset:
            per_dist[dist] = {
                "count": len(subset),
                "faithfulness":      sum(r.faithfulness for r in subset) / len(subset),
                "answer_relevancy":  sum(r.answer_relevancy for r in subset) / len(subset),
                "context_precision": sum(r.context_precision for r in subset) / len(subset),
                "context_recall":    sum(r.context_recall for r in subset) / len(subset),
                "avg_score":         sum(r.avg_score for r in subset) / len(subset),
            }

    report = {
        "total_questions": len(results),
        "per_question": [asdict(r) for r in results],
        "per_distribution": per_dist,
        "failure_clusters": clusters,
        "bottom_10": bottom,
    }
    return report


def save_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict],
                        path: str = os.path.join(ARTIFACTS_DIR, "ragas_50q.json")) -> None:
    write_json(path, build_phase_a_report(results, clusters, bottom))



# ─── Tasks 1-4: Sinh viên implement ──────────────────────────────────────────

DISTRIBUTIONS = ("factual", "multi_hop", "adversarial")
METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
LOW, OK = 0.5, 0.7  # ngưỡng đọc metric khi chẩn đoán: < LOW là thấp, >= OK là ổn
_VERSION_RE = re.compile(r"\bv\d{4}\b|\bv\d+\.\d+\b", re.IGNORECASE)
_ABSTAIN_RE = re.compile(r"không tìm thấy|không có thông tin", re.IGNORECASE)


def group_by_distribution(test_set: list[dict]) -> dict[str, list[dict]]:
    """Task 1: Nhóm 50 câu hỏi theo 3 distributions.

    Returns:
        {"factual": [...], "multi_hop": [...], "adversarial": [...]}
    """
    groups: dict[str, list[dict]] = {d: [] for d in DISTRIBUTIONS}
    for item in test_set:
        dist = item.get("distribution")
        if dist not in groups:
            raise ValueError(f"Câu {item.get('id')}: distribution không hợp lệ {dist!r}.")
        groups[dist].append(item)
    return groups


def _metric(record, name: str, question_id) -> float:
    """Đọc metric từ object (thuộc tính) hoặc dict của m4; bắt buộc float hữu hạn trong [0,1]."""
    raw = record.get(name) if isinstance(record, dict) else getattr(record, name, None)
    if raw is None:
        raise ValueError(f"Câu {question_id}: m4 không trả metric {name}.")
    value = float(raw)  # NumPy/Pandas scalar → float Python
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"Câu {question_id}: {name}={value} không hợp lệ (cần hữu hạn trong [0,1]).")
    return value


def run_ragas_50q(answers: list[dict]) -> RagasEvaluation:
    """Task 2: Chạy RAGAS 4 metrics trên toàn bộ 50 câu hỏi.

    Gọi m4.evaluate_ragas đúng một lần trên toàn bộ answers, ghép điểm về từng câu theo
    thứ tự đầu vào (không zip âm thầm khi lệch số dòng) và lấy evaluator_models từ
    metadata của chính lượt evaluation đó — không đoán bằng JUDGE_MODEL.
    """
    if not answers:
        raise ValueError("Không có answers để chấm RAGAS.")
    try:
        from src.m4_eval import evaluate_ragas
    except ImportError as e:
        raise ValueError("Thiếu src/m4_eval.py; không thể chấm RAGAS và khai evaluator models.") from e

    questions     = [a["question"]       for a in answers]
    ans_texts     = [a["answer"]         for a in answers]
    contexts      = [list(a["contexts"]) for a in answers]
    ground_truths = [a["ground_truth"]   for a in answers]

    raw = evaluate_ragas(questions, ans_texts, contexts, ground_truths)
    per_q = list(raw.get("per_question") or [])
    if len(per_q) != len(answers):
        raise ValueError(f"m4 trả {len(per_q)} kết quả cho {len(answers)} câu; không ghép theo vị trí được.")
    evaluator_models = (raw.get("metadata") or {}).get("evaluator_models")
    if not isinstance(evaluator_models, list) or not evaluator_models:
        raise ValueError("m4 phải trả metadata.evaluator_models (model IDs thực sự dùng).")

    results = []
    for a, pq in zip(answers, per_q):
        echoed = pq.get("question") if isinstance(pq, dict) else getattr(pq, "question", None)
        if echoed is not None and echoed != a["question"]:
            raise ValueError(f"Câu {a['id']}: kết quả m4 lệch thứ tự so với answers.")
        results.append(RagasResult(
            question_id=a["id"], distribution=a["distribution"],
            question=a["question"], answer=a["answer"],
            contexts=list(a["contexts"]), ground_truth=a["ground_truth"],
            **{m: _metric(pq, m, a["id"]) for m in METRICS},
        ))
    return RagasEvaluation(results, list(evaluator_models))


def _diagnose(r: RagasResult) -> tuple[str, str]:
    """Chẩn đoán từ tổ hợp 4 metric + bằng chứng trong answer/contexts của chính câu đó."""
    f, ar, cp, cr = r.faithfulness, r.answer_relevancy, r.context_precision, r.context_recall
    worst = r.worst_metric
    abstained = bool(_ABSTAIN_RE.search(r.answer))
    head = f"{worst}={getattr(r, worst):.2f} thấp nhất (F={f:.2f}, AR={ar:.2f}, CP={cp:.2f}, CR={cr:.2f})."

    if abstained:
        # Answer từ chối không có khẳng định nào → RAGAS chấm F/AR thấp; không phải hallucination.
        diag = "Pipeline trả 'Không tìm thấy' nên answer không đáp ứng câu hỏi"
        if cr >= OK:
            diag += " dù contexts đã có ý của reference → lỗi generation (prompt từ chối quá chặt)"
        elif cr > 0:
            diag += f"; contexts chỉ phủ một phần reference (CR={cr:.2f}) nhưng model cũng không dùng phần đã có"
        else:
            diag += "; evaluator chấm contexts không phủ reference (CR=0)"
        fix = ("Cho model trả lời phần có căn cứ và nêu rõ phần thiếu thay vì từ chối toàn bộ, "
               "hướng dẫn tính từng bước từ contexts; tăng top_k để lấy đủ các tài liệu cần ghép")
    elif worst == "context_recall":
        diag = "Retrieval bỏ sót ý của reference trong top-k contexts"
        if r.distribution == "multi_hop":
            diag += "; câu cần ghép nhiều tài liệu nhưng contexts chỉ phủ một phần"
        fix = ("Tăng recall: kiểm tra chunk chứa đáp án có trong top-20 hybrid không, "
               "tăng RERANK_TOP_K hoặc tách query multi-hop thành các query con")
    elif worst == "context_precision":
        if cr >= OK:
            diag = "Đã lấy được đoạn đúng nhưng xếp sau các đoạn nhiễu (ranking kém)"
            fix = "Siết reranker/ngưỡng điểm rerank và lọc metadata (nguồn, phiên bản) trước khi đưa vào prompt"
        else:
            diag = "Phần lớn contexts lấy sai tài liệu, đoạn liên quan vừa ít vừa xếp thấp"
            fix = "Cải thiện truy vấn (BM25 từ khóa chính sách, query rewrite) và lọc theo metadata nguồn"
    elif worst == "faithfulness":
        if cr >= OK:
            diag = "Contexts đã đủ nhưng answer thêm khẳng định không được contexts hỗ trợ (lỗi generation)"
            fix = "Prompt bắt buộc chỉ dùng và trích dẫn contexts, temperature=0, từ chối khi thiếu dữ kiện"
        else:
            diag = "Contexts thiếu nên model tự bổ sung từ kiến thức ngoài (hallucination do retrieval)"
            fix = "Sửa retrieval trước (recall), đồng thời buộc model trả 'Không tìm thấy' khi contexts không đủ"
    else:  # answer_relevancy
        diag = "Answer lệch trọng tâm hoặc trả lời thiếu phần chính của câu hỏi"
        fix = "Prompt yêu cầu trả lời trực tiếp đủ từng ý được hỏi trước khi giải thích"

    versions = sorted({v.lower() for v in _VERSION_RE.findall(" ".join(r.contexts))})
    if len(versions) > 1:
        diag += f"; contexts trộn nhiều phiên bản ({', '.join(versions)}) → nguy cơ dùng bản hết hiệu lực"
        fix += "; ưu tiên/lọc bản hiện hành theo metadata phiên bản"
    return f"{head} {diag}.", f"{fix}."


def bottom_10(results: list[RagasResult]) -> list[dict]:
    """Task 3: Lấy 10 câu hỏi có avg_score thấp nhất.

    Returns:
        [{"rank": 1, "question_id": ..., "distribution": ...,
          "question": ..., "avg_score": ..., "worst_metric": ...,
          "diagnosis": ..., "suggested_fix": ...}, ...]
    """
    # Hòa điểm thì theo question_id để thứ tự ổn định giữa các lần chạy.
    ranked = sorted(results, key=lambda r: (r.avg_score, r.question_id))[:10]
    output = []
    for rank, r in enumerate(ranked, 1):
        diagnosis, fix = _diagnose(r)
        output.append({
            "rank": rank,
            "question_id": r.question_id,
            "distribution": r.distribution,
            "question": r.question,
            "avg_score": round(r.avg_score, 4),
            "worst_metric": r.worst_metric,
            "worst_score": round(getattr(r, r.worst_metric), 4),
            "diagnosis": diagnosis,
            "suggested_fix": fix,
        })
    return output


def cluster_analysis(results: list[RagasResult]) -> dict:
    """Task 4: Phân tích failure clusters theo (worst_metric × distribution).

    Matrix thống kê worst_metric của mọi câu, không coi mọi câu là một failure.
    Nhóm yếu nhất = distribution có avg_score trung bình thấp nhất (bỏ nhóm rỗng).
    Tổng matrix theo cột chỉ là kích thước nhóm 20/20/10, không đo chất lượng.
    """
    if not results:
        raise ValueError("Không có kết quả RAGAS để phân tích cluster.")
    matrix = {m: {d: 0 for d in DISTRIBUTIONS} for m in METRICS}
    for r in results:
        matrix[r.worst_metric][r.distribution] += 1

    by_dist = {d: [r for r in results if r.distribution == d] for d in DISTRIBUTIONS}
    means = {d: sum(r.avg_score for r in rows) / len(rows) for d, rows in by_dist.items() if rows}
    weakest = min(means, key=means.get)  # chất lượng thấp nhất, KHÔNG phải nhóm đông nhất
    totals = {m: sum(matrix[m].values()) for m in METRICS}
    dominant_metric = max(METRICS, key=lambda m: totals[m])

    weak_rows = by_dist[weakest]
    weak_metric_means = {m: sum(getattr(r, m) for r in weak_rows) / len(weak_rows) for m in METRICS}
    weak_metric = min(weak_metric_means, key=weak_metric_means.get)
    others = ", ".join(f"{d} {means[d]:.3f}" for d in means if d != weakest)
    spread = ", ".join(f"{d} {matrix[dominant_metric][d]}" for d in DISTRIBUTIONS)
    # Matrix đếm MỌI câu: metric thấp nhất của câu gần điểm tối đa không phải lỗi thật.
    dom_rows = [r for r in results if r.worst_metric == dominant_metric]
    dom_mean = sum(getattr(r, dominant_metric) for r in dom_rows) / len(dom_rows)
    weak_qs = [r for r in results if r.avg_score < OK]
    weak_counts = {m: sum(r.worst_metric == m for r in weak_qs) for m in METRICS}
    weak_dominant = max(METRICS, key=lambda m: weak_counts[m]) if weak_qs else None
    insight = (
        f"Nhóm yếu nhất theo avg_score trung bình là '{weakest}' ({means[weakest]:.3f}; {others}). "
        f"Trong nhóm này metric có mean thấp nhất là {weak_metric} ({weak_metric_means[weak_metric]:.3f}). "
        f"Metric thấp nhất phổ biến nhất trên toàn bộ là {dominant_metric} "
        f"({totals[dominant_metric]}/{len(results)} câu: {spread}), nhưng điểm trung bình của nó "
        f"tại các câu đó là {dom_mean:.3f} nên phần lớn chỉ là metric thấp nhất của câu đã tốt. "
    )
    if weak_dominant:
        breakdown = ", ".join(f"{m} {weak_counts[m]}" for m in METRICS if weak_counts[m])
        insight += (f"Chỉ xét {len(weak_qs)} câu có avg_score < {OK}: worst_metric là {breakdown}; "
                    f"hướng sửa ưu tiên cho nhóm này: {DIAGNOSTIC_TREE[weak_dominant][1]}.")
    else:
        insight += f"Không có câu nào avg_score < {OK}."
    return {
        "matrix": matrix,
        "distribution_avg_scores": {d: round(v, 6) for d, v in means.items()},
        "worst_metric_totals": totals,
        "dominant_failure_distribution": weakest,
        "dominant_failure_metric": dominant_metric,
        "insight": insight,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "a", *sys.argv[1:]]))
