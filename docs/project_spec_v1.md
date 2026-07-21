# AI Interview Coach with RAG - 프로젝트 명세서

> 이 문서는 "현재 상태 요약"을 맨 앞에, 초기 설계부터 지금까지의 "설계 이력"을 뒤에 두는 구조입니다. 최신 구현 기준으로 궁금하면 1~5번만, 왜 이렇게 바뀌었는지 궁금하면 뒤의 설계 이력을 참고하세요.

---

## 1. 프로젝트 목표와 현재 구현 범위

사용자가 이력서/자기소개서/포트폴리오/프로젝트 README(`.md`, `.txt`)를 업로드하면, 그 문서를 기반으로 개인화된 면접 질문을 생성하고, 사용자의 답변을 평가하는 RAG 기반 AI 면접 코치 서비스.

메인 프로젝트(`korean-chatbot`, GPT-style Transformer 직접 구현)의 후속작으로, 기성 LLM(Gemini API)을 활용한 실서비스형 AI 시스템 구축·서빙·평가 역량을 보여주는 것이 목적.

**지원 파일 형식은 현재 `.md`, `.txt`이다.** PDF(`resume.pdf` 등)는 초기 구상 단계의 예시였고 아직은 실제로는 구현하지 않았다 (Future Work).

## 2. 현재 아키텍처

### Collection 1: User Docs
사용자가 업로드하는 이력서/포트폴리오. `POST /documents`로 업로드, Chunking → Embedding(`ko-sroberta-multitask`) → Chroma.

### Collection 2: Interview KB
운영자가 직접 작성하는 고정 콘텐츠. 현재 **18개 문서**(jwt, jwt_logout_invalidation, fastapi, spring_di, spring_boot, spring_layered_architecture, spring_bean_scope, postgresql_index, transaction, docker, http, oauth, caching, session_vs_token, session_auth, token_auth, async_sync, cors). 11개에서 늘어난 것은 다루는 주제 수를 늘린 게 아니라, "문서 분리 단위 = 완결된 근거 단위(retrieval unit)" 원칙에 따라 기존 문서(postgresql, spring, session_vs_token, jwt)를 재구성한 결과 (설계 이력 참고). `scripts/load_kb.py`로 일회성 인덱싱.

### Chain A: 질문 생성
```
User Docs Retrieval Node → Generation Node (Gemini Structured Output) → InterviewQuestions
```
LangGraph StateGraph로 구현. `rag/graph.py`의 `build_chain_a_graph()`.

### Chain B + Agent v3: 답변 평가
```
Interview KB Retrieval Node → Judge Node → Decision(technical_score 구간)
    → (0~3점)  Fundamentals Node        : 개념 자체를 설명
    → (4~6점)  Learning Tip Node → Followup Node : 약점 보완 코칭 + 꼬리질문
    → (7~10점) Advanced Question Node   : 심화 질문
```
`rag/graph.py`의 `build_interview_agent_graph()`. 조건부 분기 함수는 `decide_next_step()` (구현 초기에는 `decide_followup()`으로 불렀으나, Learning Tip 추가 후 이름을 바꿈).

v2까지는 `technical_score < 5` 하나로만 갈렸고 점수가 높으면 아무 노드도 실행되지 않아, 두 갈래 중 한쪽이 비어 있었다. v3에서는 **구간마다 필요한 코칭의 종류가 다르다**는 기준으로 세 갈래로 확장해 모든 점수대에서 결과가 나오도록 했다. 경계값은 `FUNDAMENTALS_THRESHOLD = 4`, `ADVANCED_THRESHOLD = 7`.

4~6점 경로에서는 Learning Tip이 먼저 실행되어 핵심 약점(topic)을 정하고, Followup이 그 topic을 이어받아 동일 주제의 꼬리질문을 생성한다 (병렬이 아닌 순차 설계, 이유는 설계 이력 참고).

### State 스키마 (`rag/graph_state.py`)
```python
class InterviewState(TypedDict, total=False):
    question: str
    answer: str
    context: str
    retrieved_sources: list[str]
    generated_questions: InterviewQuestions
    evaluation_result: EvaluationResult
    next_action: str                            # 어느 경로가 실행됐는지
    concept_explanation: ConceptExplanation     # 0~3점 경로
    learning_tip: LearningTip                   # 4~6점 경로
    followup_question: str                      # 4~6점 경로
    advanced_question: AdvancedQuestion         # 7~10점 경로
```
점수 구간에 따라 셋 중 한 경로만 실행되므로 나머지 키는 State에 존재하지 않는다. API 레이어에서 `.get()`으로 조회해 없으면 `null`로 응답한다.

### API
| Endpoint | 역할 |
|---|---|
| `POST /documents` | User Docs 업로드 + 인덱싱 |
| `POST /generate-question` | Chain A 실행 |
| `POST /evaluate-answer` | Chain B + Agent 실행. 점수 구간에 따라 `concept_explanation` / (`learning_tip` + `followup_question`) / `advanced_question` 중 하나가 채워지고, `next_action`으로 실행된 경로를 알 수 있다 |

## 3. 검증 결과 요약

| 항목 | 결과 | 의미 |
|---|---|---|
| Judge Calibration | 94.1% (16/17) | Gemini Judge가 채점한 technical_score/completeness_score가, 사람이 미리 정한 기대 범위(bad/average/good 등 17개 케이스)와 얼마나 일치하는지의 비율. Judge의 채점 신뢰도 지표이며, 서비스 전체 정확도가 아님 |
| RAGAS Faithfulness | 평균 0.4412 | Calibration Set 17개 답변 각각이 Interview KB의 근거 문서에 실제로 부합하는 정도의 평균. bad/average 카테고리에서 편차가 크게 나타남. 이 역시 서비스 전체 정확도가 아니라, Calibration Set이라는 특정 표본에 대한 근거성 점수 평균임 |
| RAGAS Context Precision | 0.8000 (KB 11개 기준) | Retriever가 검색한 chunk 중 실제로 관련 있는 chunk가 상위에 오는 정도. KB가 2개 문서였을 때는 항상 1.0000이라 변별력이 없었고, 11개로 확장한 뒤에야 의미 있는 값이 나옴 |
| Embedding 비교 (초기, 5문항) | Gemini Embedding이 헷갈리는 케이스 1건에서 더 안정적 | KB 11개 기준, 표본이 작아 일반화 보류로 남겨뒀던 초기 결과. 이후 20문항 재실행에서 결론이 뒤집힘(아래 행 참고) |
| Retrieval 평가셋 (20문항, reference 기반) | Top-1 100% (20/20), Faithfulness 0.9708, Context Precision 1.0000 | KB를 "완결된 근거 단위" 기준으로 재구성(postgresql/spring 분리, session_vs_token 재구성)한 뒤의 최종 결과(ko-sroberta 기준). Judge Calibration Set의 Faithfulness(0.4412)와는 목적이 다른 별도 실험이며, reference(정답)를 기준으로 KB·Retrieval 자체의 품질을 측정 |
| Embedding 비교 (최종, 20문항) | ko-sroberta 100%/0.9708 > Gemini Embedding 95%/0.9500 | Retrieval Unit 재설계 이후 20문항 평가셋으로 재실행. 5문항 표본(Gemini 우세)과 정반대 결론으로, 표본 확대가 결론을 뒤집은 사례다. ko-sroberta-multitask를 최종 임베딩으로 채택 |

## 4. 핵심 설계 변경 이력 (요약, 상세는 아래 설계 이력 참고)

- **Structured Output 도입**: Gemini의 자유 텍스트 출력이 API 계약과 안 맞아 `with_structured_output()` + Pydantic 스키마로 전환
- **RAGAS 적용 대상 재설정**: 초기 계획은 Chain A(질문 생성)에 Faithfulness를 적용하는 것이었으나, 면접 질문은 "주장"이 아니라 "질의"라 지표 전제와 안 맞음을 발견. Faithfulness 적용 대상을 Chain B(사용자 답변 + retrieved context)로 재설정
- **Calibration Set 재설계**: Judge 채점 실패를 Judge 성향이 아니라 Calibration Set 자체의 설계 결함(동일 답변에 서로 다른 기대치 부여)으로 진단, 재설계로 52.9% → 94.1% 향상
- **LCEL → LangGraph 마이그레이션**: 기존 LCEL 코드(`rag/chains.py`)는 보존한 채 StateGraph로 재구현. Calibration Set을 회귀 테스트로 재사용해 마이그레이션이 새로운 오분류를 만들지 않았음을 검증
- **Agent v1 → v2**: 조건부 분기(Followup만 생성)에서, Learning Tip 노드를 추가하고 병렬이 아닌 순차 구조로 설계 변경
- **KB 2개 → 11개 확장**: Context Precision과 Embedding 비교가 KB 2개 문서로는 변별력을 갖지 못함을 확인, 교차 언급 문서를 포함해 11개로 확장
- **requirements.txt → uv**: `pyproject.toml` + `uv.lock`으로 패키지 관리 전환
- **Retrieval Unit 재설계 (11개 → 18개)**: "chunk당 주제 하나" 원칙을 모든 문서에 동일하게 적용하는 대신, 독립 개념 나열 문서(postgresql, spring)는 하위 주제별로 분리하고 비교형 문서(session_vs_token)는 비교 근거를 한 chunk에 유지하도록 재구성. Retrieval 전용 평가셋(20문항)으로 검증해 Top-1 100%·Faithfulness 0.9708까지 개선
- **Embedding 비교 재검증 (20문항)**: 5문항 표본에서의 "Gemini Embedding이 더 안정적" 결론이 Retrieval Unit 재설계 후 20문항 재실행에서 뒤집힘. ko-sroberta-multitask가 Top-1 100%·Faithfulness 0.9708로 근소 우세해 최종 임베딩으로 채택
- **Agent v2 → v3 (점수 구간별 다중 분기)**: 단일 조건(`< 5`)으로 갈리던 구조에서 3구간 분기로 확장. "분기를 늘린다"가 아니라 "구간마다 필요한 코칭의 종류가 다르다"를 기준으로, 0~3점은 개념 설명, 4~6점은 기존 약점 보완 코칭, 7~10점은 심화 질문을 반환하도록 설계. 빈 경로가 사라져 모든 점수대에서 결과가 나온다

## 5. 한계와 다음 단계

- Embedding 비교는 20문항 세트로 재실행 완료(ko-sroberta 근소 우세로 최종 채택). 다만 Gemini의 실패 케이스(`http.md`→`cors.md` 혼동) 원인은 추가 분석하지 않고 보류(우선순위 낮음)
- **그래프에 사이클이 없음**: Phase 7에서 점수 구간별 3분기로 확장해 "점수가 높으면 아무 동작도 하지 않는" 빈 경로는 해소했으나, 여전히 모든 경로가 한 방향으로 흐르고 끝난다. "조건부 분기만 할 것이면 LCEL로도 가능하지 않은가"라는 반문에 답하려면 사이클이 필요하며, 멀티턴 루프(Future Work 최우선)로 대응 예정
- **Retrieval 지표의 변별력 재확인 필요**: Context Precision 1.0000은 KB 2개 시절 만점과 같은 "측정 조건 미충족"일 가능성이 있음 (KB 확장 후 재측정 항목으로 관리)
- 실배포(Docker, EC2, CI/CD)는 Phase 8에서 진행 예정
- PDF 지원은 Phase 9로 계획 (현재 `.md`, `.txt`만 지원)

세부 계획은 아래 [Roadmap](#roadmap)의 Phase 7 이후 항목 참고.

---

## 설계 이력 (v1.1부터 현재까지의 변경 과정)

> 아래는 시간순으로 남긴 설계 기록입니다. 지금 구현 기준으로 궁금하면 위 "1~5번 현재 상태 요약"을 참고하세요.

# AI Interview Coach with RAG - 프로젝트 명세서 v1.1

> **v1.1 (2026-06-24)**: Day 1~2 구현 결과를 반영해 Chain A 아키텍처와 모델 설정 결정을 업데이트. 원본 v1 설계와 실제 구현 사이에 생긴 차이를 동기화.

## 배경

- 메인 프로젝트(`korean-chatbot`)와 완전히 분리된 별도 미니 프로젝트
  - 메인: GPT-style Transformer를 PyTorch로 직접 구현 → 엔진을 만드는 능력
  - 미니: Gemini API 기반 RAG 시스템 구축·배포·평가 → 실서비스형 AI 시스템을 만들고 서빙하는 능력
- 멘토 피드백: "프론티어 모델(Gemini 등)과 비교해보라", "기능하는 에이전트를 만들고 서빙하는 능력도 키워야 한다"

## 목표

사용자가 이력서/자기소개서/포트폴리오/프로젝트 README를 업로드하면, 그 문서를 기반으로 개인화된 면접 질문을 생성하고, 사용자의 답변을 평가하는 RAG 기반 AI 면접 코치 서비스.

## MVP 범위

### 포함

- 문서 업로드 + 인덱싱
- Chain A: 사용자 문서 기반 질문 생성
- Chain B: 답변 평가

### 제외 (Future Work)

- 꼬리질문 생성
- 스트리밍 응답
- Docker 배포
- 멀티유저 / 인증
- LangGraph / 멀티턴 면접

## 아키텍처

### Collection 1 - User Docs

`resume.pdf`, `portfolio.pdf`, `README.md` 등 → Chunking → Embedding(`ko-sroberta-multitask`) → Chroma

### Collection 2 - Interview KB

AI/백엔드 취준생 기준으로 범위 한정: JWT, Spring, FastAPI, PostgreSQL, Docker 등 - md 문서 20~30개

### Chain A - 질문 생성

```
User Docs Retriever → Prompt Template → Gemini (Structured Output) → InterviewQuestions(questions: list[str])
```

> v1 설계는 `Retriever → Gemini → 면접 질문`로 단순화돼 있었으나, 실제 구현 과정에서 두 가지가 추가됨:
> 1. Prompt를 별도 단계로 분리해 단독 검증 가능하게 함 (`scripts/check_prompt.py`)
> 2. Gemini의 자유 텍스트 출력이 마크다운/설명이 섞여 나와 API 계약과 안 맞는 문제 발견 → `with_structured_output()` + Pydantic 스키마(`InterviewQuestions`)로 전환

### 모델 설정

- 모델: `gemini-3.5-flash` (명시적 버전 고정)
- `gemini-flash-latest` 같은 auto-update alias는 의도적으로 배제 - Google이 가리키는 모델을 바꾸면 코드 수정 없이도 평가 기준 모델이 바뀌어, Day 4 RAGAS 평가의 재현성이 깨질 수 있음
- 모델명은 코드에 하드코딩하지 않고 `.env`의 `GEMINI_MODEL`로 분리 (fallback: `gemini-3.5-flash`)

### Chain B - 답변 평가

```
면접 질문 + 사용자 답변 → Interview KB Retriever → Gemini Judge → 점수 + 피드백 (JSON)
```

## API 설계

| Endpoint | 역할 |
|---|---|
| `POST /documents` | 문서 업로드 + 인덱싱 (Collection 1) |
| `POST /generate-question` | Chain A 실행 |
| `POST /evaluate-answer` | Chain B 실행 |

## 평가 계획

### Retrieval (RAGAS)

| Chain | 지표 | 비고 |
|---|---|---|
| Chain A | Faithfulness, Context Precision | Context Recall은 reference set 부담으로 MVP에서 제외 |
| Chain B | Context Precision | Recall/Faithfulness보다 Judge 타당성이 핵심이라 최소만 측정 |

### Judge 신뢰성 - Calibration Set

- 면접 질문 5개 × 답변 수준(bad/average/good) 3단계 = 15개
- 각 항목에 `expected_range` 명시, 실제 Judge 점수와 비교

```json
{
  "question": "JWT란 무엇인가?",
  "answer": "모르겠습니다.",
  "answer_level": "bad",
  "expected_range": [0, 3]
}
```

## 재사용 자산 (메인 프로젝트 `korean-chatbot`에서)

- `rag/shared/`의 chunking, embedding 모듈 - 그대로 재사용 가능
- Chroma vectorstore 설정(cosine distance 명시) - 2-컬렉션 구조에 맞게 재작성 필요
- LCEL 체인 패턴(`retriever | format_docs`, `RunnablePassthrough`) - 그대로 적용 가능

## 다음 단계 (빌드 순서 - Retriever 먼저, LLM은 나중)

RAG 프로젝트는 LLM보다 문서 로딩/청킹/임베딩/검색 단계에서 더 자주 깨진다(FAISS segfault, Chroma distance function 사례 참고). 가장 큰 리스크는 "Source B(KB) 부족"이 아니라 "Retriever 자체가 안 맞음"이므로, KB는 최소 단위로 늦게 만든다.

**우선순위**: 1) User Docs Retrieval → 2) Question Generation(Chain A) → 3) Interview KB(최소 구성) → 4) Answer Evaluation(Chain B)

- **Day 1 (완료)**: 프로젝트 디렉토리 생성 + FastAPI 기동 확인 + `POST /documents`로 인덱싱 + Retriever 의미 기반 검색 검증(dedup 포함)
- **Day 2 (완료)**: Gemini 연동 4단계 검증(단독 → Prompt → Retriever+Prompt → 전체 체인) → Structured Output 적용 → `POST /generate-question` 엔드포인트
- **Day 3 (다음)**:
  1. `rag/vectorstore.py`에 `get_interview_kb_vectorstore()` / `get_interview_kb_retriever()` 추가 (Collection 1과 동일 패턴, cosine distance 포함)
  2. `kb/` 폴더에 `jwt.md`, `fastapi.md` 2개만 작성 (Day 1 발견 - 단일 주제로 짧게)
  3. KB는 API 업로드가 아니라 일회성 로드 스크립트로 인덱싱 (사용자가 올리는 게 아니라 직접 작성하는 고정 콘텐츠이므로)
  4. `retriever.invoke("JWT란 무엇인가?")`로 단독 검증
  5. `EvaluationResult` 스키마 설계 (technical_score, completeness_score 등 - 어떤 점수를 Calibration 기준으로 할지 미리 확정)
  6. Chain B(Question + Answer + KB Retriever → Gemini Judge) 구현
- **이후**: RAGAS + Calibration Set 적용

**Day 2에서 발견한 추가 이슈**: Gemini 3+ 모델은 `.content`가 plain string이 아니라 thought signature가 포함된 블록 리스트로 나옴 (`rag/llm_utils.py`의 `extract_text()`로 대응했으나, 최종적으로는 structured output 방식으로 해결).

## 추가 실험 계획 (구현 후, Future Work)

### 임베딩 모델 비교

MVP는 `ko-sroberta-multitask`로 시작하되, 구현 완료 후 비교 실험으로 확장:

| | Embedding A | Embedding B |
|---|---|---|
| 모델 | `ko-sroberta-multitask` | Gemini Embedding |
| 비교 지표 | Faithfulness, Context Precision | Faithfulness, Context Precision |

Gemini API 기반 서비스 구축 경험을 보여주는 게 이번 프로젝트의 목적이므로, README에 두 임베딩의 RAGAS 점수를 나란히 비교해두면 "왜 이 임베딩을 선택했는가"에 대한 근거가 생긴다.

## 포트폴리오 talking points

> GPT-style Transformer를 직접 구현하는 프로젝트를 수행한 후, 실제 서비스 구축 역량을 보여주기 위해 RAG 기반 AI 면접 코치 시스템을 개발하였다. 사용자 문서 기반 질문 생성과 기술 지식 기반 답변 평가를 분리하여 설계하였고, Retrieval 성능은 RAGAS로 평가하고 답변 평가는 LLM-as-a-Judge 방식을 사용하였다.

> (Chain B에 RAGAS를 깊게 적용하지 않은 이유) Chain B의 핵심 목표는 Retrieval 성능보다 사용자 답변 평가의 타당성이었기 때문에, RAGAS보다는 Judge Calibration에 집중했습니다.

> (왜 RAG를 썼나요?) 사용자마다 문서가 다르고 계속 바뀌기 때문에, 매번 파인튜닝하는 건 비용·시간 면에서 현실적이지 않다고 판단했습니다. 그래서 모델 가중치는 고정하고, 사용자의 이력서·README를 Vector DB에 저장한 뒤 검색해서 Gemini에 컨텍스트로 제공하는 구조를 설계했습니다. 이 구조는 사용자가 늘어나도 그대로 확장되고, 어떤 질문이 어떤 문서에서 나왔는지도 추적할 수 있다는 장점이 있습니다.

> (GPT-from-scratch 프로젝트와의 시너지) 프로젝트 1(`korean-chatbot`)에서는 LLM 내부 구조(Transformer, 토크나이저, 학습)를 직접 구현했고, 프로젝트 2(`ai-interview-coach`)에서는 기성 LLM을 활용해 실서비스형 AI 시스템(RAG, 서빙, 평가)을 구축했습니다. 두 프로젝트를 함께 설명하면 "모델 내부를 이해하는 능력"과 "실제 서비스를 만드는 능력"을 모두 보여줄 수 있습니다.

---

## v1.2 업데이트 (2026-07-14) - LangGraph 마이그레이션 + Agent 확장

### 배경
8주차 부트캠프 과제(LangChain RAG → LangGraph StateGraph 마이그레이션 → Agent 확장 → FastAPI 배포)를 진행하며, 강사님 상담 결과 `ai-interview-coach`가 메인 프로젝트로 확정됨.

### 아키텍처 변경
Chain A/B를 LCEL에서 LangGraph StateGraph로 마이그레이션. 기존 LCEL 코드(`rag/chains.py`)는 삭제하지 않고 보존 - Migration 과정 자체를 증명하기 위함.

```
InterviewState (TypedDict, total=False)
├── question, answer              # 입력
├── context, retrieved_sources    # Retrieval Node가 채움
├── generated_questions           # Chain A: Generation Node가 채움
├── evaluation_result             # Chain B: Judge Node가 채움
└── next_action, followup_question  # Agent 확장용 (조건부 분기)
```

**Chain A 그래프**: `START → Retrieval(User Docs) → Generation → END`
**Chain B + Agent 그래프**: `START → Retrieval(Interview KB) → Judge → [조건부: technical_score < 5 → Followup] → END`

Retrieval과 Judge/Generation을 별도 Node로 분리한 이유:
1. 문제 발생 시 Retrieval/Judge 중 어느 단계인지 그래프 단위로 바로 특정 가능
2. Agent 확장 시 조건부 분기를 노드 단위로 추가할 수 있도록 미리 구조를 맞춤

Chain A/B를 하나의 그래프로 합치는 것은 보류 - 두 체인이 서로 다른 시점(질문 생성 시점, 답변 제출 시점)에 독립적으로 호출되어 지금 시점에 합칠 실익이 없다고 판단. 필요성이 명확해지면(예: 세션 전체를 하나의 그래프로 표현) 재검토.

### Agent 확장
`decide_followup()` 조건부 엣지로 `evaluation_result.technical_score < 5`일 때 `followup_node`로 분기, 아니면 즉시 종료. Judge Node의 `improvements`(약점)를 프롬프트에 전달해 그 약점을 겨냥한 꼬리질문 1개를 생성.

**검증**: bad 답변(technical_score=0) → 꼬리질문 생성 확인, good 답변(technical_score=10) → `followup_question: null`로 정상 스킵 확인.

**추가 발견**: 꼬리질문 생성 시에도 Chain A/B에서 봤던 Faithfulness 패턴 재현 - 프롬프트에서 "Weak Points를 겨냥하라"고 명시했음에도, KB context에 있는 다른 내용(예: 저장 위치 관련)까지 끌어다 쓰는 경우 관찰. 향후 RAGAS를 꼬리질문 생성에도 적용할 근거로 기록.

### Calibration Set을 활용한 마이그레이션 검증 (Regression Test)
Day 4에서 완성한 Calibration Set(17개, 최종 94.1%)을 LCEL에서 Graph로 옮긴 뒤 그대로 재실행:

| 버전 | 결과 | 비고 |
|---|---|---|
| LCEL (최종) | 16/17 (94.1%) | Case 17만 경계선 변동 |
| LangGraph | 15/17 (88.2%) | Case 16, 17만 실패 - 둘 다 LCEL 반복 실행에서도 경계선(±1점) 변동을 보였던 케이스 |

완전히 동일한 수치는 아니지만, 실패 케이스가 기존에 알려진 경계선 변동 케이스에 한정되어 마이그레이션이 새로운 오분류 패턴을 만들지 않았다고 판단.

### FastAPI 엔드포인트 갱신
`/generate-question`, `/evaluate-answer` 모두 내부 구현을 LCEL 체인에서 LangGraph 그래프 호출로 교체. 응답 스키마는 하위 호환 유지, `/evaluate-answer`에는 `followup_question` 필드 추가.

### 다음 단계
1. RAGAS 설치 및 적용 (Faithfulness, Context Precision) - API 호출량이 많아 그래프/Agent/API 안정화 후 진행
2. Embedding 비교 실험 (`ko-sroberta-multitask` vs Gemini Embedding)
3. `uv` 패키지 매니저로 전환 (메인 프로젝트와 도구 통일, LangGraph 마이그레이션 이후로 미뤄둠)

---

## Roadmap

### Phase 1: Retrieval (완료)
- [x] 문서 업로드 API (`POST /documents`)
- [x] Chunking + Embedding + Chroma 인덱싱 (dedup 포함)
- [x] Semantic Retrieval 검증 (키워드 매칭이 아닌 의미 기반 검색 확인)

### Phase 2: Question Generation (완료)
- [x] Gemini API 연동 (단계별 검증: Gemini 단독 → Prompt 단독 → Retriever+Prompt → 전체 체인)
- [x] Structured Output으로 응답 형식 고정 (`InterviewQuestions`)
- [x] `POST /generate-question` 엔드포인트

### Phase 3: Answer Evaluation (완료)
- [x] Interview KB 구축 (`jwt.md`, `fastapi.md`)
- [x] Chain B (Gemini Judge 기반 답변 평가, `retrieved_sources` 코드 추출)
- [x] `POST /evaluate-answer` 엔드포인트
- [x] Judge Calibration Set 17개 자동화 및 반복 개선 (52.9% → 94.1%)

### Phase 4: LangGraph Migration & Agent (완료)
- [x] Chain A/B를 StateGraph(Retrieval Node + Generation/Judge Node)로 마이그레이션
- [x] Calibration Set을 회귀 테스트로 재사용해 마이그레이션 검증 (88.2%)
- [x] technical_score 기반 조건부 분기(Agent v1), 낮은 점수 시 꼬리질문 자동 생성
- [x] Agent v2: Learning Tip 노드 추가, Followup이 topic을 이어받는 순차 설계로 확장
- [x] Agent 분기 경계값(threshold=5)을 0점/5점/10점 세 지점에서 실행 검증
- [x] FastAPI 엔드포인트를 새 그래프로 교체

### Phase 5: Evaluation (완료)
- [x] RAGAS Faithfulness 적용 (Calibration Set 17개 기준 평균 0.4412)
- [x] RAGAS Context Precision 적용 (KB 확장 후 재측정, 평균 0.8000)
- [x] Embedding 비교 실험 (`ko-sroberta-multitask` vs Gemini Embedding, KB 확장 후 유의미한 차이 관찰)
- [x] Interview KB를 2개에서 11개 문서로 확장, 교차 언급 문서로 Retrieval 난이도 조정
- [x] `uv`로 패키지 매니저 전환

### Phase 6: Retrieval Unit 재설계 (완료)
- [x] Retrieval 평가 전용 질문 세트 20문항 구축 (`tests/fixtures/retrieval_eval_set.json`)
- [x] `postgresql.md` 분리(인덱스/트랜잭션), Top-1 80%→85%
- [x] `expected_sources`(복수) 라벨로 평가셋 재설계, Top-1 100%
- [x] `spring.md` 분리(DI/Boot/계층구조/Bean Scope), Bean Scope 질문 Faithfulness 0→1.0000
- [x] `session_vs_token.md` retrieval unit 재구성(비교 근거 유지) + `jwt_logout_invalidation.md` 분리, 최종 Top-1 100%, Faithfulness 0.9708, Context Precision 1.0000
- [x] Embedding 비교(ko-sroberta vs Gemini)를 이 20문항 세트로 재실행, ko-sroberta 100%/0.9708 > Gemini 95%/0.9500로 최종 채택 (기존 5문항 결론이 뒤집힘)

### Phase 7: Agent 다중 분기 (완료)
v2까지는 `technical_score < 5` 하나로만 갈리고 점수가 높으면 아무 동작도 하지 않아 분기가 단조로웠다. 구간별로 서로 다른 종류의 코칭을 제공하도록 확장.

- [x] `decide_next_step()`을 3구간 분기로 확장 (`FUNDAMENTALS_THRESHOLD=4`, `ADVANCED_THRESHOLD=7`)
  - 0~3점: `fundamentals_node`, 개념 자체를 설명 (`ConceptExplanation`)
  - 4~6점: 기존 `learning_tip_node` → `followup_node` 유지
  - 7~10점: `advanced_question_node`, 심화 질문 (`AdvancedQuestion`)
- [x] 분기 로직 0~10점 전 구간 전수 검증 (순수 함수라 LLM 호출 없이 검증 가능)
- [x] 그래프 구조 검증 (노드 6개, 조건부 엣지 3갈래, 빈 경로 제거 확인)
- [x] 실제 실행 검증 (`scripts/check_score_branches.py`, 세 경로 PASS + 경로 간 State 누수 없음)
- [x] API 응답에 `next_action` 노출 (실행된 경로 확인 및 이후 분기별 성능 측정용)

### Phase 8: 배포 및 인프라

**① Docker 컨테이너 패키징 + Docker Compose 실행 (완료)**
- [x] Dockerfile 작성 및 Compose로 로컬 실행 확인
- [x] 임베딩 모델을 빌드 시점에 미리 받아 런타임 다운로드 제거 (`HF_HOME`을 이미지 안으로 고정)
- [x] `chroma_db/`, `data/uploads/` volume 영속화 (재시작 시 재인덱싱 건너뛰는 것까지 확인)
- [x] `GEMINI_API_KEY`는 이미지에 굽지 않고 Compose `env_file`로 런타임 주입
- [x] entrypoint에서 KB 컬렉션이 비어 있을 때만 일회성 인덱싱 수행 (최초 기동 자동화)
- [x] **이미지 크기 10.9GB → 3.79GB 감축**: 실측 결과 CUDA 스택(nvidia 2.9GB + triton 652MB)이 포함되어 있었으나 배포 대상에 GPU가 없어 전부 불필요했음. Dockerfile 안에서만 CPU 전용 torch를 쓰도록 처리(로컬 macOS와 Colab GPU 환경에 영향이 가지 않도록 `pyproject.toml`은 수정하지 않음)
- [x] **arm64/amd64 양쪽 검증 완료**: 로컬은 arm64(Apple Silicon) 3.79GB, CI 러너(linux/amd64)는 2.7GB. 두 아키텍처 모두 CUDA 패키지 0개로, CPU torch 설정이 amd64에서도 유효함을 ②의 CI 실행으로 확인. EC2 표준 인스턴스(x86_64) 사용 가능하며, 2.7GB이므로 기본 EBS 볼륨(8GB)에도 여유가 있다

**② GitHub Actions (CI) (완료)**
- [x] 푸시/PR 시 자동 실행되는 워크플로 구성 (`.github/workflows/ci.yml`), 배포는 하지 않음
- [x] `test` job: pytest 22개. 분기 로직·그래프 구조·chunking 등 **API 키가 필요 없는 계층**만 검증하도록 설계해 비밀값을 CI에 노출하지 않음
- [x] `docker-build` job: Dockerfile이 깨끗한 환경(linux/amd64 러너)에서 빌드되는지 확인
- [x] CUDA 패키지 재유입 검사: 이미지에 nvidia/triton이 포함되면 빌드 실패 처리. ①에서 최적화가 **에러 없이 조용히 풀렸던 전례**가 있어 자동 검사로 고정
- [x] 스모크 테스트: 컨테이너를 실제로 띄워 헬스체크 응답까지 확인 (KB 인덱싱은 임베딩만 쓰므로 더미 키로 가능)
- [x] 프로덕션 이미지에서 dev 의존성 제외 (`uv sync --no-dev`)

**③ AWS EC2 수동 배포**
- [ ] 인스턴스 아키텍처 확정 후 그에 맞는 플랫폼으로 이미지 빌드
  - x86_64(t2/t3): ②의 CI가 amd64 러너에서 빌드·검증을 이미 통과했으므로 그대로 사용 가능 (2.7GB, CUDA 0개)
  - Graviton(t4g): 로컬 arm64 이미지를 그대로 사용 가능 (3.79GB)
- [ ] EC2 인스턴스에 배포하고 외부에서 접근 가능하도록 구성
  - 리스크: 프리티어 `t2.micro`(RAM 1GB)는 로컬 임베딩 모델 로딩만으로 OOM 가능. 대응안은 (a) 상위 인스턴스, (b) swap 설정, (c) 배포 환경에 한해 Gemini Embedding API로 전환(`get_gemini_embeddings()`가 이미 구현되어 있음)
  - 참고: 이미지 3.79GB이므로 기본 EBS 볼륨(8GB) 용량도 함께 고려 필요

**④ GitHub Actions (CD)**
- [ ] ②의 파이프라인에 배포 단계를 연결해 푸시 시 자동 배포되도록 확장
  - 여기까지 완료하면 "빌드·배포 CI/CD 파이프라인" 과제 요건 충족

**⑤ API 성능 측정**
- [ ] 배포된 서버를 대상으로 엔드포인트별 응답 시간 및 리소스 사용량 측정
  - 핵심 관찰 대상: `/evaluate-answer`는 분기에 따라 Gemini 호출 횟수가 달라진다. `technical_score >= 5`면 Judge 1회, `< 5`면 Judge → Learning Tip → Followup 3회 순차 호출이라 같은 엔드포인트인데도 지연이 크게 갈린다.
  - 이 측정으로 Agent 순차 설계의 트레이드오프(일관성 확보 vs 지연 증가)를 정성적 설계 근거가 아니라 정량 데이터로 뒷받침할 수 있다.
  - 함께 확인할 것: `/documents` 인덱싱 소요 시간, 동시 요청 시 동작, 메모리 사용량(③의 OOM 리스크 검증)
  - 여유가 되면 로컬과 EC2를 각각 측정해 하드웨어 및 Gemini API까지의 네트워크 거리 차이를 비교

**⑥ 유닉스 환경 프로세스·스레드·메모리 분석**
- [ ] 리눅스 표준 도구로 상태를 조회하고 분석 보고서 작성
  - ⑤에서 확인한 지연 구간을 소재로 삼는다. Gemini API 응답 대기는 전형적인 I/O 바운드 블로킹이라, 그 시점의 프로세스·스레드 상태를 관찰하기에 적합하다.
  - EC2(실제 리눅스) 환경에서 진행. 현재 개발 환경은 macOS라 `/proc`이 없어 조회 방식이 제한된다.

**⑦ WireShark 통신 캡처**
- [ ] HTTP/HTTPS 통신 캡처 및 분석
  - 클라이언트(로컬 노트북)와 서버(EC2)가 물리적으로 다른 컴퓨터이므로 과제 조건이 자연히 충족된다.
  - ⑤에서 느리게 측정된 구간이 네트워크 지연인지 서버 처리 시간인지 캡처로 구분해볼 수 있다.

### Phase 9: 입력 형식 확장 (진행 예정)
- [ ] PDF 업로드 지원 (현재 `.md`, `.txt`만 지원)
  - `rag/loader.py`에 PDF 로더 추가 + `api/documents.py`의 `SUPPORTED_EXTENSIONS` 확장으로 대응 가능
  - 실사용 이력서는 대부분 PDF이므로 제품 가치가 높음

### Future Work / 선택
- [ ] **멀티턴 면접 루프**: 생성된 꼬리질문에 사용자가 다시 답하고 Judge로 되돌아가는 사이클 구조. 종료 조건(점수 도달 / 최대 턴 수 / 개선 없음) 설계 필요.
  - 현재 그래프에는 사이클이 없어 "조건부 분기만 할 것이면 LCEL로도 가능하지 않은가"라는 반문에 답하기 어렵다. 루프를 도입하면 LangGraph 채택 근거가 명확해지므로, Future Work 중 우선순위가 가장 높다.
- [ ] **KB 확장 (18개 → 25~30개) 및 전체 재측정** (선택)
  - 배경: 현재 Context Precision 1.0000, Faithfulness 0.9708이지만, KB 2개 문서 시절에도 같은 이유로 만점이 나왔다가 "측정 조건 미충족"으로 판명된 전례가 있다. 18개(chunk 29개)에 `k=3`이면 여전히 변별력이 부족할 가능성이 있다.
  - 주의: KB 변경은 Retrieval 평가·임베딩 비교 결과를 모두 무효화하므로, 과제 진행 중에는 착수하지 않고 baseline을 유지한다. 확장 시 20문항 평가셋 전체 재실행이 필요하다.
  - 참고: 11개 → 18개는 기존 문서 재구성이었으므로, 실제로 다루는 주제 수를 늘리려면 신규 문서 작성이 필요하다.
- [ ] **Agent v3: Knowledge Search 노드** (선택)
  - Judge가 진단한 약점(`improvements`)을 검색어로 KB를 재검색해 Learning Tip에 더 정확한 근거를 제공하는 구상. v2 설계 시 "이미 검색했는데 왜 또 검색하는가"라는 반문 때문에 보류했으나, Learning Tip 도입 후 "Learning Tip 품질 개선"이라는 명분이 확보되어 v3 확장 여지로 남겨둠.
  - 다만 현재 KB 규모에서는 개선 여지가 크지 않을 수 있고, 오히려 context가 넓어져 Faithfulness가 낮아질 위험도 있다(기존에 관찰된 문제는 근거 부족이 아니라 과잉 인용이었음). KB 확장 이후 20문항 평가셋으로 전후 비교해 검증할 것.
- [ ] **프론트엔드 화면** (선택)
  - 멀티턴 루프 구현 이후에 붙이면 대화형 UI와 시너지가 크다.