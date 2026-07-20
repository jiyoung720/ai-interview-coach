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

EVAL_SET_PATH = Path("tests/fixtures/retrieval_eval_set.json")


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def evaluate_retriever(name, retriever, eval_set, evaluator_llm, evaluator_embeddings):
    print(f"\n{'=' * 50}")
    print(f"[{name}]")
    print("=" * 50)

    results = []
    correct = 0

    for i, case in enumerate(eval_set, 1):
        question = case["question"]
        reference = case["reference"]
        expected_sources = case["expected_sources"]

        docs = retriever.invoke(question)
        context = format_docs(docs)
        top_source = docs[0].metadata.get("source", "unknown") if docs else "none"
        source_correct = top_source in expected_sources
        if source_correct:
            correct += 1

        dataset = Dataset.from_dict({
            "question": [question],
            "answer": [reference],
            "contexts": [[context]],
            "reference": [reference],
        })
        eval_result = evaluate(
            dataset,
            metrics=[faithfulness, context_precision],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
        f_score = eval_result["faithfulness"][0]
        p_score = eval_result["context_precision"][0]

        status = "OK" if source_correct else "MISS"
        print(f"{i:02d} [{status}] {question}")
        print(f"     top_source={top_source}  faithfulness={f_score:.4f}  context_precision={p_score:.4f}")

        results.append({
            "question": question,
            "expected_sources": expected_sources,
            "top_source": top_source,
            "source_correct": source_correct,
            "faithfulness": f_score,
            "context_precision": p_score,
        })

    avg_f = sum(r["faithfulness"] for r in results) / len(results)
    avg_p = sum(r["context_precision"] for r in results) / len(results)
    accuracy = correct / len(eval_set) * 100

    print(f"\n  Top-1 정확도: {correct}/{len(eval_set)} ({accuracy:.1f}%)")
    print(f"  평균 Faithfulness: {avg_f:.4f}")
    print(f"  평균 Context Precision: {avg_p:.4f}")

    return {"accuracy": accuracy, "faithfulness": avg_f, "context_precision": avg_p, "results": results}


def main():
    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))

    evaluator_llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(model=GEMINI_MODEL))
    evaluator_embeddings = LangchainEmbeddingsWrapper(get_embeddings())

    sroberta = evaluate_retriever(
        "ko-sroberta-multitask", get_interview_kb_retriever(), eval_set, evaluator_llm, evaluator_embeddings
    )
    gemini = evaluate_retriever(
        "Gemini Embedding (gemini-embedding-001)", get_interview_kb_gemini_retriever(), eval_set, evaluator_llm, evaluator_embeddings
    )

    print(f"\n{'=' * 50}")
    print("최종 비교 (Retrieval 평가셋 20문항 기준)")
    print("=" * 50)
    print(f"{'':30} {'Top-1':>10} {'Faithfulness':>15} {'Context Precision':>20}")
    print(f"{'ko-sroberta-multitask':30} {sroberta['accuracy']:>9.1f}% {sroberta['faithfulness']:>15.4f} {sroberta['context_precision']:>20.4f}")
    print(f"{'Gemini Embedding':30} {gemini['accuracy']:>9.1f}% {gemini['faithfulness']:>15.4f} {gemini['context_precision']:>20.4f}")

    diffs = [
        (a["question"], a["top_source"], b["top_source"])
        for a, b in zip(sroberta["results"], gemini["results"])
        if a["top_source"] != b["top_source"]
    ]
    if diffs:
        print(f"\n두 임베딩의 top-1 source가 다른 질문 ({len(diffs)}개):")
        for q, s1, s2 in diffs:
            print(f"  - {q}")
            print(f"    ko-sroberta={s1}  gemini={s2}")
    else:
        print("\n두 임베딩의 top-1 source는 20문항 전부 동일했음.")


if __name__ == "__main__":
    main()
