from langchain_core.prompts import ChatPromptTemplate

QUESTION_GENERATION_PROMPT = ChatPromptTemplate.from_template("""
당신은 기술 면접관입니다.
다음 프로젝트 문서를 참고하여 기술 면접 질문 5개를 생성하세요.

[Context]
{context}
""")

EVALUATION_PROMPT = ChatPromptTemplate.from_template("""
당신은 기술 면접관입니다.
아래 [Reference] 자료를 참고하여 지원자의 답변을 평가하세요.

[Question]
{question}

[Answer]
{answer}

[Reference]
{context}

평가 기준:
- technical_score: 답변이 기술적으로 정확한가 (0~10)
- completeness_score: 설명이 충분히 구체적이고 완성도 있는가 (0~10)
- strengths: 답변의 강점 목록
- improvements: 보완이 필요한 부분 목록
- overall_feedback: 전반적인 피드백 한두 문장
""")
