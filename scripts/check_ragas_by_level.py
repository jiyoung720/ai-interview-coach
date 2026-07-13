from datasets import Dataset
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import faithfulness

from rag.config import GEMINI_MODEL
from rag.embeddings import get_embeddings
from rag.graph import build_retrieval_only_graph

evaluator_llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(model=GEMINI_MODEL))
evaluator_embeddings = LangchainEmbeddingsWrapper(get_embeddings())

graph = build_retrieval_only_graph()
question = "JWT란 무엇인가?"

cases = {
    "bad": "모르겠습니다.",
    "average": "JWT는 세션 대신 쓰는 건데, 서버에 로그인 정보를 저장해두는 방식입니다.",
    "good": (
        "JWT는 사용자 인증 정보를 안전하게 전달하기 위한 토큰 기반 인증 방식으로, "
        "Header, Payload, Signature로 구성되며 서버가 별도 세션 저장소 없이 "
        "서명을 검증해 사용자를 인증할 수 있습니다."
    ),
}

result = graph.invoke({"question": question})
context = result["context"]

print("Faithfulness\n")
for level, user_answer in cases.items():
    dataset = Dataset.from_dict({
        "question": [question],
        "answer": [user_answer],
        "contexts": [[context]],
    })

    eval_result = evaluate(
        dataset,
        metrics=[faithfulness],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )
    score = eval_result["faithfulness"][0]

    print(f"{level:8}: {score:.4f}")
