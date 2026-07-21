from langchain_core.prompts import ChatPromptTemplate

QUESTION_GENERATION_PROMPT = ChatPromptTemplate.from_template("""
당신은 기술 면접관입니다.
다음 프로젝트 문서를 참고하여 기술 면접 질문 5개를 생성하세요.

[Context]
{context}
""")

# completeness_score 기준 문구는 Judge Calibration 실험에서 Judge가 질문 범위를 벗어난
# 배경지식까지 커버리지 체크리스트처럼 채점하던 문제를 발견한 뒤 추가한 것 (52.9% -> 94.1%로 개선)
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
- technical_score (0~10): 답변이 기술적으로 정확한가
- completeness_score (0~10): [Question]에서 직접 묻고 있는 내용에 한정하여,
  그 범위 안에서 충분히 설명했는가. [Reference]에는 있지만 질문이 요구하지
  않은 배경지식(예: 다른 개념, 보안 이슈, 대안 전략)을 답변에서 언급하지
  않았다는 이유로 감점하지 않는다.
- strengths: 답변의 강점 목록
- improvements: 보완이 필요한 부분 목록
- overall_feedback: 전반적인 피드백 한두 문장
""")

LEARNING_TIP_PROMPT = ChatPromptTemplate.from_template("""
당신은 기술 면접 코치입니다.
아래는 지원자의 답변에 대한 평가에서 드러난 약점입니다. 이 약점을 보완하기 위해
무엇을 공부해야 할지 학습 팁 1개를 생성하세요.

[Question]
{question}

[Weak Points]
{improvements}

[Reference]
{context}

- topic: 보완해야 할 핵심 주제 (예: "JWT Access/Refresh Token 구조")
- reason: 왜 이 주제를 공부해야 하는지, [Weak Points]에 근거해 설명
- recommended_sections: [Reference]에서 참고할 만한 부분을 구체적으로 지목
""")

FOLLOWUP_PROMPT = ChatPromptTemplate.from_template("""
당신은 기술 면접관입니다.
아래는 지원자의 답변과 그에 대한 평가입니다. [Focus Topic]을 정확히 겨냥하는
꼬리질문 1개를 생성하세요.

[Question]
{question}

[Answer]
{answer}

[Focus Topic]
{focus_topic}

[Reference]
{context}

꼬리질문은 [Focus Topic]에서 다루는 내용을 확인하는 것이어야 하며,
원래 질문의 범위를 벗어나지 않아야 합니다.
""")
