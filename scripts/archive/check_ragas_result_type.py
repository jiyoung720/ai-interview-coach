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
result = graph.invoke({"question": "JWT란 무엇인가?"})
context = result["context"]

dataset = Dataset.from_dict({
    "question": ["JWT란 무엇인가?"],
    "answer": ["모르겠습니다."],
    "contexts": [[context]],
})

eval_result = evaluate(dataset, metrics=[faithfulness], llm=evaluator_llm, embeddings=evaluator_embeddings)

print("type:", type(eval_result))
print("repr:", eval_result)
print("eval_result['faithfulness']:", eval_result["faithfulness"])
print("type of that:", type(eval_result["faithfulness"]))
