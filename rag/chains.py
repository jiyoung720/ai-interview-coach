from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from rag.config import GEMINI_MODEL
from rag.llm_utils import extract_text
from rag.prompts import QUESTION_GENERATION_PROMPT
from rag.schemas import InterviewQuestions
from rag.vectorstore import get_user_docs_retriever


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def get_context_chain():
    """Retriever + Prompt만 연결 (LLM 호출 전 단계 검증용)"""
    retriever = get_user_docs_retriever()
    return {"context": retriever | format_docs} | QUESTION_GENERATION_PROMPT


def get_chain_a():
    """전체 Chain A: Retriever → Prompt → Gemini(structured output) → InterviewQuestions"""
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    structured_llm = llm.with_structured_output(InterviewQuestions)
    return get_context_chain() | structured_llm
