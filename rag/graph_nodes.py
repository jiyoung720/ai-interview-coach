from rag.graph_state import InterviewState
from rag.llm_utils import extract_text
from rag.vectorstore import get_interview_kb_retriever


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def retrieval_node(state: InterviewState) -> dict:
    """KB Retriever로 question과 관련된 context를 검색하고,
    retrieved_sources를 코드에서 직접 추출한다 (LLM에게 생성시키지 않음)."""
    kb_retriever = get_interview_kb_retriever()
    docs = kb_retriever.invoke(state["question"])

    context = format_docs(docs)
    sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})

    return {"context": context, "retrieved_sources": sources}


def judge_node(state: InterviewState) -> dict:
    """context를 참고해 answer를 평가한다. retrieval_node 이후에 실행되어야 한다."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from rag.config import GEMINI_MODEL
    from rag.prompts import EVALUATION_PROMPT
    from rag.schemas import EvaluationResult

    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    structured_llm = llm.with_structured_output(EvaluationResult)

    prompt_value = EVALUATION_PROMPT.invoke({
        "question": state["question"],
        "answer": state["answer"],
        "context": state["context"],
    })
    result = structured_llm.invoke(prompt_value)

    return {"evaluation_result": result}


def user_docs_retrieval_node(state: InterviewState) -> dict:
    """Chain A용 Retrieval Node — User Docs(Collection 1)에서 검색.
    Chain B의 retrieval_node와 컬렉션만 다르고 패턴은 동일하다."""
    from rag.vectorstore import get_user_docs_retriever

    retriever = get_user_docs_retriever()
    docs = retriever.invoke(state["question"])

    context = format_docs(docs)
    sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})

    return {"context": context, "retrieved_sources": sources}


def generation_node(state: InterviewState) -> dict:
    """context를 기반으로 면접 질문 5개를 생성한다."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from rag.config import GEMINI_MODEL
    from rag.prompts import QUESTION_GENERATION_PROMPT
    from rag.schemas import InterviewQuestions

    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    structured_llm = llm.with_structured_output(InterviewQuestions)

    prompt_value = QUESTION_GENERATION_PROMPT.invoke({"context": state["context"]})
    result = structured_llm.invoke(prompt_value)

    return {"generated_questions": result}


FOLLOWUP_THRESHOLD = 5  # technical_score가 이 값 미만이면 꼬리질문 생성


def followup_node(state: InterviewState) -> dict:
    """평가 결과의 약점(improvements)을 겨냥한 꼬리질문 1개를 생성한다."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from rag.config import GEMINI_MODEL
    from rag.prompts import FOLLOWUP_PROMPT

    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)

    improvements = "\n".join(f"- {item}" for item in state["evaluation_result"].improvements)

    prompt_value = FOLLOWUP_PROMPT.invoke({
        "question": state["question"],
        "answer": state["answer"],
        "improvements": improvements,
        "context": state["context"],
    })
    response = llm.invoke(prompt_value)

    return {
        "next_action": "followup_generated",
        "followup_question": extract_text(response),
    }


def decide_followup(state: InterviewState) -> str:
    """technical_score가 기준 미만이면 꼬리질문 노드로, 아니면 종료."""
    if state["evaluation_result"].technical_score < FOLLOWUP_THRESHOLD:
        return "followup"
    return "end"
