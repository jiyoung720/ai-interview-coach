# POST /generate-question 엔드포인트 담당
# 역할: 검색어를 받아서, 그 검색어와 관련된 사용자 문서를 찾아 면접 질문 5개를 만들어 줌
# Chain A: 검색어 → 관련 문서 검색 → 질문 생성
from fastapi import APIRouter
from pydantic import BaseModel

from rag.graph import build_chain_a_graph

router = APIRouter()


class GenerateQuestionRequest(BaseModel):
    query: str = "프로젝트 기술 스택"   # = 뒤는 기본값. 안 보내도 이 값으로 동작

# 질문 생성 요청
@router.post("/generate-question")
def generate_question(request: GenerateQuestionRequest):
    # rag/graph.py의 빌더를 호출해서 Chain A 그래프를 만듬
    graph = build_chain_a_graph()   # 그래프 만들고,
    # 입력은 query지만 State에는 question 키로 담음 (Chain A/B가 State 스키마를 공유하기 때문)
    result = graph.invoke({"question": request.query})  # 그래프 호출
    # 최종 State에서 생성된 질문 5개(generated_questions.questions)만 꺼내 반환
    return {"questions": result["generated_questions"].questions}