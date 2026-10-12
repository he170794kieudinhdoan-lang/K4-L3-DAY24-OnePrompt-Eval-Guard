from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (EMBEDDING_MODEL, LLM_API_KEY, LLM_BASE_URL, RAGAS_MODEL,
                    TEST_SET_PATH)


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


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    lengths = {len(questions), len(answers), len(contexts), len(ground_truths)}
    if len(lengths) != 1 or not questions:
        raise ValueError("RAGAS input lists must have the same non-zero length")
    if not LLM_API_KEY:
        # Keep unit tests and offline development deterministic, but mark the
        # result invalid so save_report() cannot turn it into a fake report.
        return {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "per_question": [],
            "evaluation_error": (
                "RAGAS requires OPENAI_API_KEY or GEMINI_API_KEY in .env"
            ),
        }

    try:
        from ragas import evaluate
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from ragas.run_config import RunConfig
        from datasets import Dataset
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_openai import ChatOpenAI

        llm_kwargs = {
            "model": RAGAS_MODEL,
            "api_key": LLM_API_KEY,
            "temperature": 0,
            "timeout": 900,
            "max_retries": 3,
        }
        if LLM_BASE_URL:
            llm_kwargs["base_url"] = LLM_BASE_URL
        evaluator_llm = ChatOpenAI(**llm_kwargs)

        class SingleCandidateLLMWrapper(LangchainLLMWrapper):
            """Emulate n completions with n single-candidate Gemini calls."""

            def generate_text(self, prompt, n=1, temperature=None, stop=None,
                              callbacks=None):
                if temperature is None:
                    temperature = self.get_temperature(n=n)
                results = [
                    self.langchain_llm.generate_prompt(
                        prompts=[prompt], temperature=temperature, stop=stop,
                        callbacks=callbacks,
                    )
                    for _ in range(n)
                ]
                first = results[0]
                first.generations = [[r.generations[0][0] for r in results]]
                return first

            async def agenerate_text(self, prompt, n=1, temperature=None,
                                     stop=None, callbacks=None):
                if temperature is None:
                    temperature = self.get_temperature(n=n)
                results = []
                for _ in range(n):
                    result = await self.langchain_llm.agenerate_prompt(
                        prompts=[prompt], temperature=temperature, stop=stop,
                        callbacks=callbacks,
                    )
                    results.append(result)
                first = results[0]
                first.generations = [[r.generations[0][0] for r in results]]
                return first

        evaluator_llm = SingleCandidateLLMWrapper(evaluator_llm)
        evaluator_embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            encode_kwargs={"normalize_embeddings": True},
        )

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
            run_config=RunConfig(
                timeout=900, max_retries=10, max_wait=60, max_workers=1
            ),
            raise_exceptions=True,
        )
        df = result.to_pandas()
        per_question = [
            EvalResult(
                question=str(row["question"]),
                answer=str(row["answer"]),
                contexts=row["contexts"] if isinstance(row["contexts"], list) else [row["contexts"]],
                ground_truth=str(row["ground_truth"]),
                faithfulness=float(row.get("faithfulness", 0.0) or 0.0),
                answer_relevancy=float(row.get("answer_relevancy", 0.0) or 0.0),
                context_precision=float(row.get("context_precision", 0.0) or 0.0),
                context_recall=float(row.get("context_recall", 0.0) or 0.0),
            )
            for _, row in df.iterrows()
        ]
        return {
            "faithfulness": float(df["faithfulness"].mean()) if "faithfulness" in df else 0.0,
            "answer_relevancy": float(df["answer_relevancy"].mean()) if "answer_relevancy" in df else 0.0,
            "context_precision": float(df["context_precision"].mean()) if "context_precision" in df else 0.0,
            "context_recall": float(df["context_recall"].mean()) if "context_recall" in df else 0.0,
            "per_question": per_question,
        }
    except Exception as e:
        raise RuntimeError(f"RAGAS evaluation failed: {e}") from e


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten prompt, lower temperature"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25"),
        "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
        "answer_relevancy": ("Answer doesn't match question", "Improve prompt template"),
    }

    scored = []
    for r in eval_results:
        metrics = {
            "faithfulness": r.faithfulness,
            "context_recall": r.context_recall,
            "context_precision": r.context_precision,
            "answer_relevancy": r.answer_relevancy,
        }
        avg = sum(metrics.values()) / len(metrics)
        worst_metric = min(metrics, key=metrics.get)
        scored.append((avg, r, worst_metric, metrics[worst_metric]))

    scored.sort(key=lambda x: x[0])
    bottom = scored[:bottom_n]

    results = []
    for avg, r, worst_metric, worst_score in bottom:
        diagnosis, fix = diagnostic_tree.get(worst_metric, ("Unknown", "Review pipeline"))
        results.append({
            "question": r.question,
            "avg_score": round(avg, 4),
            "worst_metric": worst_metric,
            "score": round(worst_score, 4),
            "diagnosis": diagnosis,
            "suggested_fix": fix,
        })
    return results


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    if results.get("evaluation_error") or not results.get("per_question"):
        raise RuntimeError(
            results.get("evaluation_error")
            or "Refusing to save an empty RAGAS report"
        )
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
