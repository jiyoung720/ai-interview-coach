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
from rag.vectorstore import get_interview_kb_retriever

EVAL_SET_PATH = Path("tests/fixtures/retrieval_eval_set.json")

# 먼저 3개만 시험 실행. 문제없으면 None으로 바꿔 전체 실행.
LIMIT = None


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def main():
    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    if LIMIT is not None:
        eval_set = eval_set[:LIMIT]

    evaluator_llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(model=GEMINI_MODEL))
    evaluator_embeddings = LangchainEmbeddingsWrapper(get_embeddings())
    retriever = get_interview_kb_retriever()

    print(f"총 {len(eval_set)}개 질문 평가 중...\n")

    results = []
    correct_source_count = 0

    for i, case in enumerate(eval_set, 1):
        question = case["question"]
        reference = case["reference"]
        expected_source = case["expected_source"]

        docs = retriever.invoke(question)
        context = format_docs(docs)
        top_source = docs[0].metadata.get("source", "unknown") if docs else "none"
        source_correct = top_source == expected_source

        if source_correct:
            correct_source_count += 1

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
        print(f"     expected={expected_source}  top_source={top_source}  faithfulness={f_score:.4f}  context_precision={p_score:.4f}")

        results.append({
            "question": question,
            "expected_source": expected_source,
            "top_source": top_source,
            "source_correct": source_correct,
            "faithfulness": f_score,
            "context_precision": p_score,
        })

    print("\n" + "=" * 50)
    print(f"Top-1 source 정확도: {correct_source_count}/{len(eval_set)} ({correct_source_count/len(eval_set)*100:.1f}%)")

    avg_f = sum(r["faithfulness"] for r in results) / len(results)
    avg_p = sum(r["context_precision"] for r in results) / len(results)
    print(f"평균 Faithfulness: {avg_f:.4f}")
    print(f"평균 Context Precision: {avg_p:.4f}")

    misses = [r for r in results if not r["source_correct"]]
    if misses:
        print(f"\n예상과 다른 문서가 1순위로 검색된 케이스 ({len(misses)}개):")
        for r in misses:
            print(f"  - {r['question']}")
            print(f"    expected={r['expected_source']}, got={r['top_source']}")


if __name__ == "__main__":
    main()
