from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from rag.config import GEMINI_MODEL
from rag.llm_utils import extract_text
from rag.prompts import EVALUATION_PROMPT, QUESTION_GENERATION_PROMPT
from rag.schemas import EvaluationResult, InterviewQuestions
from rag.vectorstore import get_interview_kb_retriever, get_user_docs_retriever


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# --- Chain A: 질문 생성 ---

def get_context_chain():
    retriever = get_user_docs_retriever()
    return {"context": retriever | format_docs} | QUESTION_GENERATION_PROMPT


def get_chain_a():
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    structured_llm = llm.with_structured_output(InterviewQuestions)
    return get_context_chain() | structured_llm


# --- Chain B: 답변 평가 ---

def get_evaluation_context_chain():
    """입력: {"question": str, "answer": str} — Prompt 단독/연결 검증용"""
    kb_retriever = get_interview_kb_retriever()

    def retrieve_kb_context(inputs: dict) -> str:
        docs = kb_retriever.invoke(inputs["question"])
        return format_docs(docs)

    return (
        {
            "context": RunnableLambda(retrieve_kb_context),
            "question": RunnableLambda(lambda x: x["question"]),
            "answer": RunnableLambda(lambda x: x["answer"]),
        }
        | EVALUATION_PROMPT
    )


def get_chain_b():
    """전체 Chain B: KB Retriever → Prompt → Gemini Judge → dict(EvaluationResult + retrieved_sources)

    retrieved_sources는 LLM이 생성하지 않고, retriever 결과에서 코드가 직접 추출한다.
    시스템이 이미 아는 사실(어떤 문서에서 검색됐는지)을 모델에게 다시 묻지 않는다."""
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    structured_llm = llm.with_structured_output(EvaluationResult)
    kb_retriever = get_interview_kb_retriever()

    def evaluate(inputs: dict) -> dict:
        docs = kb_retriever.invoke(inputs["question"])
        context = format_docs(docs)
        sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})

        prompt_value = EVALUATION_PROMPT.invoke({
            "question": inputs["question"],
            "answer": inputs["answer"],
            "context": context,
        })
        result = structured_llm.invoke(prompt_value)
        return {**result.model_dump(), "retrieved_sources": sources}

    return RunnableLambda(evaluate)
