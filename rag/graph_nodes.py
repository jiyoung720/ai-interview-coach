# 실제로 검색하고, Gemini를 호출하고, 분기를 판단하는 진짜 로직이 전부 여기 있음
from rag.graph_state import InterviewState
from rag.llm_utils import extract_text
from rag.vectorstore import get_interview_kb_retriever


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def retrieval_node(state: InterviewState) -> dict:
    """KB Retriever로 question과 관련된 context를 검색하고,
    retrieved_sources를 코드에서 직접 추출한다 (LLM에게 생성시키지 않음)."""
    kb_retriever = get_interview_kb_retriever()      # KB 검색기 가져오기
    docs = kb_retriever.invoke(state["question"])    # question으로 검색 → 관련 chunk 3개
    context = format_docs(docs)                       # 3개 chunk의 본문을 \n\n로 이어붙여 하나의 context 문자열로 만듦
    # retrieved_sources(어느 문서에서 나왔는지)는 LLM에게 물어보지 않고 코드가 직접 metadata에서 추출
    sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})  # 출처 파일명 추출
    return {"context": context, "retrieved_sources": sources}


def judge_node(state: InterviewState) -> dict:
    """context를 참고해 answer를 평가한다. retrieval_node 이후에 실행되어야 한다."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from rag.config import GEMINI_MODEL
    from rag.prompts import EVALUATION_PROMPT
    from rag.schemas import EvaluationResult

    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    # Gemini가 무조건 EvaluationResult 스키마(technical_score, improvements 등)에 맞는 구조화된 객체를 반환하게 함
    structured_llm = llm.with_structured_output(EvaluationResult)

    # retrieval이 채운 context + 원래 있던 question, answer를 프롬프트에 채워 Gemini에 보냄
    prompt_value = EVALUATION_PROMPT.invoke({
        "question": state["question"],
        "answer": state["answer"],
        "context": state["context"],
    })
    result = structured_llm.invoke(prompt_value)

    return {"evaluation_result": result}   # 채점 결과(EvaluationResult)를 State에 채움


def user_docs_retrieval_node(state: InterviewState) -> dict:
    """Chain A용 Retrieval Node. User Docs(Collection 1)에서 검색."""
    # retrieval_node와 로직은 같고, KB 대신 사용자가 올린 문서(user_docs)를 검색한다는 점만 다름
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
    # judge_node와 같은 기법: Gemini가 InterviewQuestions 스키마(questions 리스트)에 맞춰 반환하게 강제
    structured_llm = llm.with_structured_output(InterviewQuestions)

    prompt_value = QUESTION_GENERATION_PROMPT.invoke({"context": state["context"]})
    result = structured_llm.invoke(prompt_value)

    return {"generated_questions": result}


# technical_score 구간별 분기 경계값.
# 0~3점: 개념 자체를 모름 -> 기초 개념 설명
# 4~6점: 부분 이해 -> Learning Tip + Followup
# 7~10점: 정확히 답함 -> 심화 질문
FUNDAMENTALS_THRESHOLD = 4   # 이 값 미만이면 기초 개념 설명
ADVANCED_THRESHOLD = 7       # 이 값 이상이면 심화 질문

# technical_score < 5일 때만 실행
def learning_tip_node(state: InterviewState) -> dict:
    """평가 결과의 약점(improvements)을 보완할 학습 팁을 생성한다.
    followup_node보다 먼저 실행되어, 여기서 정한 topic을 Followup이 이어받는다."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from rag.config import GEMINI_MODEL
    from rag.prompts import LEARNING_TIP_PROMPT
    from rag.schemas import LearningTip

    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    structured_llm = llm.with_structured_output(LearningTip)

    # judge가 채운 약점 목록(improvements)을 "- 항목" 불릿 문자열로 만들어 프롬프트에 넣음
    improvements = "\n".join(f"- {item}" for item in state["evaluation_result"].improvements)

    prompt_value = LEARNING_TIP_PROMPT.invoke({
        "question": state["question"],
        "improvements": improvements,
        "context": state["context"],
    })
    result = structured_llm.invoke(prompt_value)    # LearningTip 스키마로 강제

    return {"learning_tip": result}   # topic/reason/recommended_sections를 State에 채움 (다음 노드가 topic을 이어받음)


def followup_node(state: InterviewState) -> dict:
    """learning_tip_node가 정한 topic을 그대로 겨냥한 꼬리질문을 생성한다.
    출력이 질문 문자열 하나뿐이라 다른 노드와 달리 with_structured_output()을
    쓰지 않고 일반 텍스트로 받은 뒤 extract_text()로 정리한다."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from rag.config import GEMINI_MODEL
    from rag.prompts import FOLLOWUP_PROMPT

    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)

    # 순차 설계의 핵심: improvements를 다시 해석하지 않고, 앞 노드가 정한 topic을 그대로 이어받음
    # → 학습 팁과 꼬리질문이 항상 같은 주제를 겨냥하게 됨
    focus_topic = state["learning_tip"].topic

    prompt_value = FOLLOWUP_PROMPT.invoke({
        "question": state["question"],
        "answer": state["answer"],
        "focus_topic": focus_topic,
        "context": state["context"],
    })
    response = llm.invoke(prompt_value)   # structured_output 없이 일반 텍스트로 받음

    return {
        "next_action": "followup_generated",
        "followup_question": extract_text(response),   # Gemini 3+ 응답 형식 이슈를 우회해 순수 텍스트만 추출
    }


def fundamentals_node(state: InterviewState) -> dict:
    """0~3점 경로. 개념을 거의 모르는 상태이므로 학습 방향 제시(Learning Tip)가 아니라
    개념 자체를 [Reference] 범위 안에서 설명해준다."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from rag.config import GEMINI_MODEL
    from rag.prompts import FUNDAMENTALS_PROMPT
    from rag.schemas import ConceptExplanation

    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    structured_llm = llm.with_structured_output(ConceptExplanation)

    prompt_value = FUNDAMENTALS_PROMPT.invoke({
        "question": state["question"],
        "answer": state["answer"],
        "context": state["context"],
    })
    result = structured_llm.invoke(prompt_value)

    return {"next_action": "fundamentals_explained", "concept_explanation": result}


def advanced_question_node(state: InterviewState) -> dict:
    """7~10점 경로. 이미 정확히 답했으므로 보완할 약점이 없다.
    코칭 대신 한 단계 깊은 심화 질문을 던져 이해의 깊이를 확인한다."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    from rag.config import GEMINI_MODEL
    from rag.prompts import ADVANCED_QUESTION_PROMPT
    from rag.schemas import AdvancedQuestion

    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
    structured_llm = llm.with_structured_output(AdvancedQuestion)

    prompt_value = ADVANCED_QUESTION_PROMPT.invoke({
        "question": state["question"],
        "answer": state["answer"],
        "context": state["context"],
    })
    result = structured_llm.invoke(prompt_value)

    return {"next_action": "advanced_question_generated", "advanced_question": result}


def decide_next_step(state: InterviewState) -> str:
    """technical_score 구간에 따라 세 경로 중 하나를 고른다."""
    # graph.py의 add_conditional_edges가 호출하는 라우팅 함수.
    # 다른 노드와 달리 State를 갱신하지 않고(반환이 str), 다음에 갈 경로만 문자열로 답함.
    # 분기 조건(technical_score)이 사용자 입력이 아니라 직전에 Gemini가 생성한 값이라는 게 핵심.
    score = state["evaluation_result"].technical_score
    if score < FUNDAMENTALS_THRESHOLD:
        return "fundamentals"
    if score >= ADVANCED_THRESHOLD:
        return "advanced"
    return "learning_tip"
