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

# Faithfulness에는 context만 필요하므로, Judge/LearningTip/Followup을 거치지 않는
# Retrieval 전용 그래프만 실행한다 — 불필요한 Gemini 호출을 줄인다.
graph = build_retrieval_only_graph()

question = "JWT란 무엇인가?"
user_answer = (
    "JWT는 사용자 인증 정보를 안전하게 전달하기 위한 토큰 기반 인증 방식으로, "
    "Header, Payload, Signature로 구성되며 서버가 별도 세션 저장소 없이 "
    "서명을 검증해 사용자를 인증할 수 있습니다."
)

result = graph.invoke({"question": question})
context = result["context"]

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

print(eval_result)
