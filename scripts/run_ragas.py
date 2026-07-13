import json
from pathlib import Path

from datasets import Dataset
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import faithfulness

from rag.config import GEMINI_MODEL
from rag.embeddings import get_embeddings
from rag.graph import build_retrieval_only_graph

CALIBRATION_PATH = Path("tests/fixtures/calibration_set.json")

# 먼저 3개만 시험 실행. 문제없으면 None으로 바꿔 전체 실행.
LIMIT = None


def main():
    calibration_set = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    if LIMIT is not None:
        calibration_set = calibration_set[:LIMIT]

    evaluator_llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(model=GEMINI_MODEL))
    evaluator_embeddings = LangchainEmbeddingsWrapper(get_embeddings())
    graph = build_retrieval_only_graph()

    context_cache: dict[str, str] = {}
    results = []

    print(f"총 {len(calibration_set)}개 케이스 실행 중...\n")

    for i, case in enumerate(calibration_set, 1):
        question = case["question"]
        answer = case["answer"]
        answer_level = case["answer_level"]

        if question not in context_cache:
            retrieval_result = graph.invoke({"question": question})
            context_cache[question] = retrieval_result["context"]
        context = context_cache[question]

        dataset = Dataset.from_dict({
            "question": [question],
            "answer": [answer],
            "contexts": [[context]],
        })

        eval_result = evaluate(
            dataset,
            metrics=[faithfulness],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
        score = eval_result["faithfulness"][0]

        print(f"Case {i:02d} [{answer_level:30}] faithfulness = {score:.4f}")
        results.append({"case": i, "answer_level": answer_level, "faithfulness": score})

    print("\n" + "=" * 50)

    by_level: dict[str, list[float]] = {}
    for r in results:
        by_level.setdefault(r["answer_level"], []).append(r["faithfulness"])

    print("카테고리별 평균 Faithfulness:")
    for level, scores in by_level.items():
        avg = sum(scores) / len(scores)
        print(f"  {level:30}: {avg:.4f} (n={len(scores)})")

    overall_avg = sum(r["faithfulness"] for r in results) / len(results)
    print(f"\n전체 평균 Faithfulness: {overall_avg:.4f}")


if __name__ == "__main__":
    main()
