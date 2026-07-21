# Gemini가 with_structured_output()으로 반환해야 하는 데이터의 "틀(스키마)" 정의.
# 각 노드가 자유 텍스트가 아니라 아래 구조에 맞는 객체를 받도록 강제한다.
from pydantic import BaseModel, Field


# generation_node가 반환. 면접 질문 5개를 문자열 리스트로
class InterviewQuestions(BaseModel):
    questions: list[str]


# judge_node가 반환. 채점 결과이며, decide_next_step이 여기의 technical_score를 읽어 분기함
class EvaluationResult(BaseModel):
    technical_score: int = Field(ge=0, le=10, description="기술적 정확성")   # ge/le = 0~10 사이 정수만 허용
    completeness_score: int = Field(ge=0, le=10, description="설명의 완성도")
    strengths: list[str]        # 답변의 강점 목록
    improvements: list[str]     # 보완할 약점 목록 → learning_tip_node의 입력이 됨
    overall_feedback: str       # 전반적 피드백 한두 문장


# learning_tip_node가 반환. followup_node가 여기의 topic을 이어받아 꼬리질문을 만듦
class LearningTip(BaseModel):
    topic: str                      # 보완할 핵심 주제
    reason: str                     # 왜 이 주제를 공부해야 하는지
    recommended_sections: list[str] # 참고할 KB 부분
