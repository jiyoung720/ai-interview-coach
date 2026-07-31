# Gemini가 with_structured_output()으로 반환해야 하는 데이터의 "틀(스키마)" 정의.
# 각 노드가 자유 텍스트가 아니라 아래 구조에 맞는 객체를 받도록 강제한다.
from typing import Literal

from pydantic import BaseModel, Field


# generation_node가 반환. 면접 질문 5개를 문자열 리스트로
class InterviewQuestions(BaseModel):
    questions: list[str]


# 감점 항목 하나. 만점에서 무엇 때문에 얼마나 깎였는지를 사용자에게 보여주기 위한 단위.
# "왜 이 점수인지 납득이 안 된다"는 문제를 점수 자체가 아니라 근거로 해소한다.
class Deduction(BaseModel):
    reason: str = Field(description="무엇이 부족해서 감점했는지 한 문장")
    points: int = Field(ge=1, le=10, description="이 항목으로 깎은 점수")


# judge_node가 반환. 채점 결과이며, decide_next_step이 여기의 technical_score를 읽어 분기함.
#
# 필드 순서에 의도가 있다: structured output은 정의된 순서대로 생성되므로,
# deductions를 technical_score보다 앞에 두어 "깎을 것을 먼저 세고 그 합을 10에서 빼는"
# 흐름을 유도한다. 점수를 먼저 내면 감점 목록이 사후 정당화가 되어 둘이 어긋나기 쉽다.
class EvaluationResult(BaseModel):
    deductions: list[Deduction] = Field(
        description="10점 만점에서 깎은 항목들. 만점이면 빈 목록"
    )
    technical_score: int = Field(ge=0, le=10, description="기술적 정확성. 10에서 deductions 합을 뺀 값")
    completeness_score: int = Field(ge=0, le=10, description="설명의 완성도")
    level: Literal["junior", "middle", "senior"] = Field(
        description="이 답변이 보여주는 역량 수준. 지원자의 연차가 아니라 답변 하나의 수준"
    )
    strengths: list[str]        # 답변의 강점 목록
    improvements: list[str]     # 보완할 약점 목록 → learning_tip_node의 입력이 됨
    overall_feedback: str       # 전반적 피드백 한두 문장


# learning_tip_node가 반환. followup_node가 여기의 topic을 이어받아 꼬리질문을 만듦
class LearningTip(BaseModel):
    topic: str                      # 보완할 핵심 주제
    reason: str                     # 왜 이 주제를 공부해야 하는지
    recommended_sections: list[str] # 참고할 KB 부분


# fundamentals_node가 반환 (0~3점). 개념을 거의 모르는 상태라 학습 방향 제시보다
# 개념 자체를 설명해주는 것이 적절하다고 판단해 별도 스키마로 분리
class ConceptExplanation(BaseModel):
    concept: str            # 질문이 묻고 있던 핵심 개념
    explanation: str        # 개념을 처음 접하는 사람 기준의 설명
    key_points: list[str]   # 꼭 기억해야 할 포인트


# advanced_question_node가 반환 (7~10점). 이미 잘 답한 사람에게 더 깊이 파고드는 질문
class AdvancedQuestion(BaseModel):
    question: str   # 심화 질문
    intent: str     # 이 질문으로 무엇을 확인하려는지 (사용자에게 의도를 알려주는 용도)
