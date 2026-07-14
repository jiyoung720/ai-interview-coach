from rag.prompts import EVALUATION_PROMPT

filled = EVALUATION_PROMPT.invoke({
    "question": "JWT란 무엇인가?",
    "answer": "잘 모르겠습니다.",
    "context": "JWT는 토큰 기반 인증 방식이다.",
})
print(filled.to_string())
