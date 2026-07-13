import json
from pathlib import Path

from datasets import Dataset
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import context_precision, faithfulness

from rag.config import GEMINI_MODEL
from rag.embeddings import get_embeddings
from rag.vectorstore import get_interview_kb_gemini_retriever, get_interview_kb_retriever

CALIBRATION_PATH = Path("tests/fixtures/calibration_set.json")


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def evaluate_retriever(name, retriever, good_cases, evaluator_llm, evaluator_embeddings):
    print(f"\n{'=' * 50}")
    print(f"[{name}]")
    print("=" * 50)

    faithfulness_scores = []
    precision_scores = []

    for case in good_cases:
        question = case["question"]
        answer = case["answer"]  # good 답변
        docs = retriever.invoke(question)
        context = format_docs(docs)

        dataset = Dataset.from_dict({
            "question": [question],
            "answer": [answer],
            "contexts": [[context]],
            "reference": [answer],
        })

        result = evaluate(
            dataset,
            metrics=[faithfulness, context_precision],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
        f_score = result["faithfulness"][0]
        p_score = result["context_precision"][0]

        print(f"  {question}")
        print(f"    faithfulness={f_score:.4f}  context_precision={p_score:.4f}")

        faithfulness_scores.append(f_score)
        precision_scores.append(p_score)

    avg_f = sum(faithfulness_scores) / len(faithfulness_scores)
    avg_p = sum(precision_scores) / len(precision_scores)
    print(f"\n  평균: faithfulness={avg_f:.4f}  context_precision={avg_p:.4f}")
    return avg_f, avg_p


def main():
    calibration_set = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    seen = set()
    good_cases = []
    for case in calibration_set:
        if case["answer_level"] == "good" and case["question"] not in seen:
            good_cases.append(case)
            seen.add(case["question"])

    evaluator_llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(model=GEMINI_MODEL))
    evaluator_embeddings = LangchainEmbeddingsWrapper(get_embeddings())

    sroberta_f, sroberta_p = evaluate_retriever(
        "ko-sroberta-multitask", get_interview_kb_retriever(), good_cases, evaluator_llm, evaluator_embeddings
    )
    gemini_f, gemini_p = evaluate_retriever(
        "Gemini Embedding (gemini-embedding-001)", get_interview_kb_gemini_retriever(), good_cases, evaluator_llm, evaluator_embeddings
    )

    print(f"\n{'=' * 50}")
    print("최종 비교")
    print("=" * 50)
    print(f"{'':30} {'Faithfulness':>15} {'Context Precision':>20}")
    print(f"{'ko-sroberta-multitask':30} {sroberta_f:>15.4f} {sroberta_p:>20.4f}")
    print(f"{'Gemini Embedding':30} {gemini_f:>15.4f} {gemini_p:>20.4f}")


if __name__ == "__main__":
    main()
