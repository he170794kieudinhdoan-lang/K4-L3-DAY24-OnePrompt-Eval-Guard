from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (EVALUATOR_EMBEDDING_PROVIDER, LLM_API_KEY, LLM_BASE_URL,
                    LLM_EMBEDDING_MODEL, LLM_MAX_RETRIES, LLM_MODEL, TEST_SET_PATH)

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _score(value) -> float:
    """Metric → float Python; giá trị không đọc được thành NaN để bước sau chấm lại."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str],
                   nan_retries: int = 2) -> dict:
    """Run RAGAS evaluation (Lab 24 adapter).

    Trả về điểm trung bình 4 metric, "per_question" (list[EvalResult], đúng thứ tự đầu vào)
    và "metadata": {"evaluator_models": [...]} — model IDs LLM + embedding thực sự truyền
    vào RAGAS trong lượt này.

    RAGAS cho NaN khi judge LLM trả output không parse được. Những câu có NaN được chấm
    LẠI thật (tối đa `nan_retries` lần); nếu vẫn NaN thì raise — không điền điểm giả.
    Thiếu key hoặc RAGAS lỗi cũng raise, không trả list rỗng âm thầm.
    """
    n = len(questions)
    if not (n == len(answers) == len(contexts) == len(ground_truths)):
        raise ValueError("evaluate_ragas: questions/answers/contexts/ground_truths phải cùng độ dài.")
    if n == 0:
        raise ValueError("evaluate_ragas: không có câu hỏi nào để chấm.")
    if not LLM_API_KEY:
        raise RuntimeError("evaluate_ragas: thiếu OPENAI_API_KEY — RAGAS cần LLM làm evaluator.")

    import math
    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
    from ragas.run_config import RunConfig

    # Mặc định ragas 0.1.x dùng gpt-3.5-turbo + ada-002 → chỉ định model rõ ràng,
    # temperature=0 để điểm ổn định giữa các lần chạy.
    judge = ChatOpenAI(model=LLM_MODEL, temperature=0, api_key=LLM_API_KEY,
                       base_url=LLM_BASE_URL, max_retries=LLM_MAX_RETRIES)
    if EVALUATOR_EMBEDDING_PROVIDER == "local":
        # Key không có model embedding OpenAI → embed local bằng sentence-transformers.
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name=LLM_EMBEDDING_MODEL,
                                           encode_kwargs={"normalize_embeddings": True})
        embedding_id = embeddings.model_name
    else:
        # check_embedding_ctx_length=False: gửi text thô thay vì token id của tiktoken
        # (endpoint không phải OpenAI, như Gemini, không hiểu token id).
        embeddings = OpenAIEmbeddings(model=LLM_EMBEDDING_MODEL, api_key=LLM_API_KEY,
                                      base_url=LLM_BASE_URL, check_embedding_ctx_length=False)
        embedding_id = embeddings.model
    # answer_relevancy mặc định sinh 3 câu hỏi ngược bằng 1 request n=3; Gemini
    # không hỗ trợ n>1 → giảm strictness về 1 (vẫn cùng công thức, ít mẫu hơn).
    answer_relevancy.strictness = 3 if LLM_BASE_URL is None else 1
    # Model ID đọc từ chính object đã truyền vào evaluate(), không đoán từ config khác.
    evaluator_models = [judge.model_name, embedding_id]

    def _run(indices: list[int]) -> list[dict]:
        dataset = Dataset.from_dict({
            "question": [questions[i] for i in indices],
            "answer": [answers[i] for i in indices],
            "contexts": [list(contexts[i]) for i in indices],
            "ground_truth": [ground_truths[i] for i in indices],
        })
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=judge,
            embeddings=embeddings,
            raise_exceptions=False,
            run_config=RunConfig(max_workers=4, max_retries=10, max_wait=90, timeout=300),
        )
        rows = result.to_pandas().to_dict("records")
        if len(rows) != len(indices):
            raise RuntimeError(f"RAGAS trả {len(rows)} dòng cho {len(indices)} câu.")
        return [{m: _score(row.get(m)) for m in METRICS} for row in rows]

    scores = _run(list(range(n)))
    for attempt in range(nan_retries):
        pending = [i for i, s in enumerate(scores) if any(math.isnan(s[m]) for m in METRICS)]
        if not pending:
            break
        print(f"  ↻ Chấm lại {len(pending)} câu có NaN (lần {attempt + 1}/{nan_retries})")
        for i, s in zip(pending, _run(pending)):
            # Chỉ thay metric đang NaN; metric đã đo hợp lệ giữ nguyên.
            scores[i] = {m: (s[m] if math.isnan(scores[i][m]) else scores[i][m]) for m in METRICS}

    still_nan = [i for i, s in enumerate(scores) if any(math.isnan(s[m]) for m in METRICS)]
    if still_nan:
        raise RuntimeError(f"RAGAS vẫn trả NaN sau {nan_retries} lần chấm lại ở vị trí {still_nan}.")

    per_question = [
        EvalResult(question=questions[i], answer=answers[i], contexts=list(contexts[i]),
                   ground_truth=ground_truths[i], **scores[i])
        for i in range(n)
    ]
    means = {m: sum(getattr(r, m) for r in per_question) / n for m in METRICS}
    return {**means, "per_question": per_question,
            "metadata": {"evaluator_models": evaluator_models}}


# Diagnostic Tree: metric thấp nhất → (chẩn đoán, hướng xử lý)
DIAGNOSTIC_TREE = {
    "faithfulness": ("LLM tự bịa câu trả lời ngoài tài liệu (hallucination)",
                     "Thắt chặt system prompt, giảm temperature về 0"),
    "context_recall": ("Hệ thống tìm kiếm bỏ sót đoạn văn chứa đáp án",
                       "Cải thiện chunking hoặc bổ sung từ khóa BM25"),
    "context_precision": ("Đoạn văn không liên quan bị xếp lên đầu",
                          "Bổ sung cross-encoder reranking hoặc lọc theo metadata"),
    "answer_relevancy": ("Câu trả lời lệch trọng tâm câu hỏi",
                         "Viết lại prompt hướng dẫn mô hình trả lời trực tiếp hơn"),
}


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree.

    Xếp câu hỏi theo điểm trung bình 4 metric tăng dần; với mỗi câu lấy metric thấp
    nhất để tra chẩn đoán. Metric NaN (judge lỗi) bị bỏ qua, không coi là 0.
    """
    import math

    analyzed = []
    for r in eval_results:
        scores = {m: getattr(r, m) for m in METRICS}
        valid = {m: s for m, s in scores.items() if s is not None and not math.isnan(s)}
        if not valid:
            continue
        worst_metric = min(valid, key=valid.get)
        diagnosis, fix = DIAGNOSTIC_TREE[worst_metric]
        analyzed.append({
            "question": r.question,
            "avg_score": round(sum(valid.values()) / len(valid), 4),
            "worst_metric": worst_metric,
            "score": round(valid[worst_metric], 4),
            "diagnosis": diagnosis,
            "suggested_fix": fix,
            "scores": {m: (round(s, 4) if m in valid else None) for m, s in scores.items()},
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "contexts": r.contexts,
        })

    analyzed.sort(key=lambda x: x["avg_score"])
    return analyzed[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    import math
    from dataclasses import asdict

    def _clean(v):  # NaN không hợp lệ trong JSON chuẩn
        return None if isinstance(v, float) and math.isnan(v) else v

    per_question = [{k: _clean(v) for k, v in asdict(r).items()}
                    for r in results.get("per_question", [])]
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(per_question),
        "failures": failures,
        "per_question": per_question,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
