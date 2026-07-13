import json
from pathlib import Path

from datasets import Dataset
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import context_precision

from rag.config import GEMINI_MODEL
from rag.embeddings import get_embeddings
from rag.graph import build_retrieval_only_graph

CALIBRATION_PATH = Path("tests/fixtures/calibration_set.json")


def main():
    calibration_set = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))

    # 5개 질문 각각의 "good" 답변을 reference로 재사용 (질문당 1개씩만)
    seen_questions = set()
    good_cases = []
    for case in calibration_set:
        if case["answer_level"] == "good" and case["question"] not in seen_questions:
            good_cases.append(case)
            seen_questions.add(case["question"])

    evaluator_llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(model=GEMINI_MODEL))
    evaluator_embeddings = LangchainEmbeddingsWrapper(get_embeddings())
    graph = build_retrieval_only_graph()

    print(f"{len(good_cases)}개 질문에 대해 Context Precision 평가 중...\n")

    results = []
    for i, case in enumerate(good_cases, 1):
        question = case["question"]
        reference = case["answer"]  # good 답변을 이상적인 정답으로 재사용

        result = graph.invoke({"question": question})
        context = result["context"]

        dataset = Dataset.from_dict({
            "question": [question],
            "contexts": [[context]],
            "reference": [reference],
            "answer": [reference],
        })

        eval_result = evaluate(
            dataset,
            metrics=[context_precision],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
        score = eval_result["context_precision"][0]

        print(f"Q{i}: {question}")
        print(f"   context_precision = {score:.4f}\n")
        results.append(score)

    avg = sum(results) / len(results)
    print("=" * 50)
    print(f"전체 평균 Context Precision: {avg:.4f}")


if __name__ == "__main__":
    main()
