from pydantic import BaseModel, Field


class InterviewQuestions(BaseModel):
    questions: list[str]


class EvaluationResult(BaseModel):
    technical_score: int = Field(ge=0, le=10, description="기술적 정확성")
    completeness_score: int = Field(ge=0, le=10, description="설명의 완성도")
    strengths: list[str]
    improvements: list[str]
    overall_feedback: str


class LearningTip(BaseModel):
    topic: str
    reason: str
    recommended_sections: list[str]
