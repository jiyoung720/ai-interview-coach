from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI

from rag.config import GEMINI_MODEL


class InterviewQuestions(BaseModel):
    questions: list[str]


llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
structured_llm = llm.with_structured_output(InterviewQuestions)

result = structured_llm.invoke(
    "FastAPI, JWT, PostgreSQL를 사용하는 프로젝트에 대한 기술 면접 질문 5개를 생성하세요."
)
print(type(result))
print(result.questions)
