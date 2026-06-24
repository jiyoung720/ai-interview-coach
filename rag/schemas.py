from pydantic import BaseModel


class InterviewQuestions(BaseModel):
    questions: list[str]
