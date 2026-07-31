# Gemini에게 실제로 보내는 프롬프트 원문 4개. (질문 생성 로직은 코드가 아니라 프롬프트 문구에 있다고 볼 수 있음)
# {context}처럼 중괄호로 둘러싼 부분이 빈칸이고, 노드가 .invoke({...})로 실제 값을 채워 완성한다.
# "질문 생성/채점 로직"의 실체는 코드가 아니라 아래 프롬프트 문구에 있다.
from langchain_core.prompts import ChatPromptTemplate

# generation_node가 사용. 빈칸은 context 하나
QUESTION_GENERATION_PROMPT = ChatPromptTemplate.from_template("""
당신은 기술 면접관입니다.
다음 프로젝트 문서를 참고하여 기술 면접 질문 5개를 생성하세요.

[Context]
{context}
""")

# judge_node가 사용. 빈칸은 question, answer, context 3개
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

채점은 10점 만점에서 부족한 만큼 깎아나가는 방식으로 합니다.
먼저 감점할 항목을 정하고, 그 합을 10에서 뺀 값을 technical_score로 삼으세요.

[technical_score 루브릭]
- 9~10점: 개념이 정확하고, 왜 그런지 근거나 동작 원리까지 설명했다
- 7~8점 : 개념은 맞지만 이유나 동작 원리 설명이 얕다
- 4~6점 : 방향은 맞으나 핵심이 빠졌거나 부분적으로 부정확하다
- 1~3점 : 질문과 관련은 있으나 설명의 대부분이 틀렸다
- 0점   : 모른다고 답했거나 질문과 무관한 내용이다

분량이 많다는 이유로 점수를 올리지 마세요. 길게 썼지만 틀린 답변은
짧고 정확한 답변보다 낮은 점수여야 합니다.

[감점하지 않는 경우]
아래는 technical_score의 감점 사유가 아닙니다.
- 답변이 짧다: 짧더라도 틀린 내용이 없으면 감점하지 않습니다.
  분량이나 상세함이 부족한 것은 completeness_score에서 다룹니다.
- 더 깊이 설명할 여지가 있다: improvements에 적되 감점하지는 않습니다.
- 질문이 요구하지 않은 배경지식을 다루지 않았다.

틀리거나 빠진 내용이 없다면 technical_score는 10점이고 deductions는 빈 목록입니다.
깎을 이유를 억지로 찾지 마세요.

[Reference]에 없는 내용을 사실처럼 단정하지 마세요.

평가 항목:
- deductions: 감점 항목 목록. 각 항목에 무엇이 부족했는지(reason)와 깎은 점수(points)를
  적습니다. **points의 합은 반드시 (10 - technical_score)와 같아야 합니다.**
  만점이면 빈 목록으로 두세요.
- technical_score (0~10): 위 루브릭에 따른 기술적 정확성
- completeness_score (0~10): [Question]에서 직접 묻고 있는 내용에 한정하여,
  그 범위 안에서 충분히 설명했는가. [Reference]에는 있지만 질문이 요구하지
  않은 배경지식(예: 다른 개념, 보안 이슈, 대안 전략)을 답변에서 언급하지
  않았다는 이유로 감점하지 않는다.
- level: 이 답변이 보여주는 역량 수준. 지원자의 실제 연차를 단정하는 것이 아니라
  답변 하나가 드러낸 수준을 판단합니다.
  - senior: 트레이드오프를 알고 상황에 따라 무엇을 택할지까지 설명한다
  - middle: 개념과 동작 원리를 정확히 설명한다
  - junior: 개념은 알지만 설명이 표면적이거나 부정확하다
- strengths: 답변의 강점 목록
- improvements: 보완이 필요한 부분 목록
- overall_feedback: 전반적인 피드백 한두 문장
""")

# learning_tip_node가 사용. 빈칸은 question, improvements(judge가 찾은 약점), context 3개
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

# followup_node가 사용. focus_topic은 learning_tip이 정한 topic을 그대로 이어받은 값
# (순차 설계가 프롬프트 레벨에서 드러나는 지점). 빈칸은 question, answer, focus_topic, context 4개
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

출력은 질문 문장 그 자체만 작성하세요. 마크다운 서식(**, # 등),
"[꼬리질문]" 같은 라벨, 따옴표로 감싸는 것 없이 순수 텍스트로만 출력합니다.
""")

# fundamentals_node가 사용 (0~3점). 빈칸은 question, answer, context 3개
# 개념을 거의 모르는 상태이므로, 학습 방향을 제시하는 Learning Tip과 달리
# 개념 자체를 처음부터 설명하도록 지시한다.
FUNDAMENTALS_PROMPT = ChatPromptTemplate.from_template("""
당신은 기술 면접 코치입니다.
지원자가 아래 질문의 핵심 개념을 거의 이해하지 못한 상태입니다.
[Reference]에 근거해 이 개념을 처음 접하는 사람도 이해할 수 있도록 설명하세요.

[Question]
{question}

[Answer]
{answer}

[Reference]
{context}

- concept: [Question]이 묻고 있는 핵심 개념의 이름
- explanation: 사전 지식이 없다고 가정하고, [Reference] 범위 안에서 설명
- key_points: 이 개념에서 꼭 기억해야 할 핵심 포인트 목록

[Reference]에 없는 내용은 추가하지 마세요.
""")

# advanced_question_node가 사용 (7~10점). 빈칸은 question, answer, context 3개
# 이미 정확히 답한 지원자에게는 보완할 약점이 없으므로, 코칭 대신
# 한 단계 더 깊은 질문을 던져 이해의 깊이를 확인한다.
ADVANCED_QUESTION_PROMPT = ChatPromptTemplate.from_template("""
당신은 기술 면접관입니다.
지원자가 아래 질문에 정확하게 답했습니다. 이제 이해의 깊이를 확인하기 위해
한 단계 더 깊은 심화 질문 1개를 생성하세요.

[Question]
{question}

[Answer]
{answer}

[Reference]
{context}

- question: 지원자가 이미 설명한 내용을 전제로, 실무 상황이나 트레이드오프를
  묻는 심화 질문 1개. 이미 답한 내용을 다시 묻지 마세요.
- intent: 이 질문으로 무엇을 확인하려는지 한 문장

질문은 [Reference] 범위 안에서 답할 수 있는 것이어야 합니다.
""")
