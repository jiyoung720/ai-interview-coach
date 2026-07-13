from datasets import Dataset
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import context_precision

from rag.config import GEMINI_MODEL
from rag.embeddings import get_embeddings
from rag.graph import build_retrieval_only_graph

evaluator_llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(model=GEMINI_MODEL))
evaluator_embeddings = LangchainEmbeddingsWrapper(get_embeddings())

graph = build_retrieval_only_graph()
question = "JWT란 무엇인가?"
reference = (
    "JWT는 사용자 인증 정보를 안전하게 전달하기 위한 토큰 기반 인증 방식으로, "
    "Header, Payload, Signature로 구성되며 서버가 별도 세션 저장소 없이 "
    "서명을 검증해 사용자를 인증할 수 있다."
)

result = graph.invoke({"question": question})
context = result["context"]

dataset = Dataset.from_dict({
    "question": [question],
    "contexts": [[context]],
    "reference": [reference],
    "answer": [reference],  # context_precision 계산에 answer 컬럼도 요구될 수 있어 동일값으로 채움
})

eval_result = evaluate(
    dataset,
    metrics=[context_precision],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)

print(eval_result)
