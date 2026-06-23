# AI Interview Coach with RAG — 프로젝트 명세서 v1

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

### Collection 1 — User Docs

`resume.pdf`, `portfolio.pdf`, `README.md` 등 → Chunking → Embedding(`ko-sroberta-multitask`) → Chroma

### Collection 2 — Interview KB

AI/백엔드 취준생 기준으로 범위 한정: JWT, Spring, FastAPI, PostgreSQL, Docker 등 — md 문서 20~30개

### Chain A — 질문 생성

```
User Docs Retriever → Gemini → 면접 질문
```

### Chain B — 답변 평가

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

### Judge 신뢰성 — Calibration Set

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

- `rag/shared/`의 chunking, embedding 모듈 — 그대로 재사용 가능
- Chroma vectorstore 설정(cosine distance 명시) — 2-컬렉션 구조에 맞게 재작성 필요
- LCEL 체인 패턴(`retriever | format_docs`, `RunnablePassthrough`) — 그대로 적용 가능

## 포트폴리오 talking points

> GPT-style Transformer를 직접 구현하는 프로젝트를 수행한 후, 실제 서비스 구축 역량을 보여주기 위해 RAG 기반 AI 면접 코치 시스템을 개발하였다. 사용자 문서 기반 질문 생성과 기술 지식 기반 답변 평가를 분리하여 설계하였고, Retrieval 성능은 RAGAS로 평가하고 답변 평가는 LLM-as-a-Judge 방식을 사용하였다.

> (Chain B에 RAGAS를 깊게 적용하지 않은 이유) Chain B의 핵심 목표는 Retrieval 성능보다 사용자 답변 평가의 타당성이었기 때문에, RAGAS보다는 Judge Calibration에 집중했습니다.

> (왜 RAG를 썼나요?) 사용자마다 문서가 다르고 계속 바뀌기 때문에, 매번 파인튜닝하는 건 비용·시간 면에서 현실적이지 않다고 판단했습니다. 그래서 모델 가중치는 고정하고, 사용자의 이력서·README를 Vector DB에 저장한 뒤 검색해서 Gemini에 컨텍스트로 제공하는 구조를 설계했습니다. 이 구조는 사용자가 늘어나도 그대로 확장되고, 어떤 질문이 어떤 문서에서 나왔는지도 추적할 수 있다는 장점이 있습니다.

> (GPT-from-scratch 프로젝트와의 시너지) 프로젝트 1(`korean-chatbot`)에서는 LLM 내부 구조(Transformer, 토크나이저, 학습)를 직접 구현했고, 프로젝트 2(`ai-interview-coach`)에서는 기성 LLM을 활용해 실서비스형 AI 시스템(RAG, 서빙, 평가)을 구축했습니다. 두 프로젝트를 함께 설명하면 "모델 내부를 이해하는 능력"과 "실제 서비스를 만드는 능력"을 모두 보여줄 수 있습니다.

## 다음 단계 (빌드 순서 — Retriever 먼저, LLM은 나중)

RAG 프로젝트는 LLM보다 문서 로딩/청킹/임베딩/검색 단계에서 더 자주 깨진다(FAISS segfault, Chroma distance function 사례 참고). 가장 큰 리스크는 "Source B(KB) 부족"이 아니라 "Retriever 자체가 안 맞음"이므로, KB는 최소 단위로 늦게 만든다.

**우선순위**: 1) User Docs Retrieval → 2) Question Generation(Chain A) → 3) Interview KB(최소 구성) → 4) Answer Evaluation(Chain B)

- **Day 1**: 프로젝트 디렉토리 생성(`app/`, `rag/`, `api/`, `data/`, `chroma_db/`, `tests/`, `docs/`) + FastAPI 기동 확인 + `POST /documents`로 `README.md` 1개만 인덱싱 + `retriever.invoke("JWT")`로 chunk 출력 확인. 문서가 나오는지뿐 아니라 chunk 경계에서 필요한 내용이 잘리지 않았는지도 함께 확인.
- **Day 2**: Chain A 구현 — README 기반 질문 생성 성공
- **Day 3**: `kb/`에 `jwt.md`, `fastapi.md` 2개만 추가 — Source B 최소 구성으로 시작
- **이후**: Chain B 구현 → KB를 20~30개로 확장 → RAGAS + Calibration Set 적용

**오늘 목표(Day 1)**: `docs = retriever.invoke("JWT")` → `print(docs[0].page_content)`가 정상 출력되는 것까지.

## 추가 실험 계획 (구현 후, Future Work)

### 임베딩 모델 비교

MVP는 `ko-sroberta-multitask`로 시작하되, 구현 완료 후 비교 실험으로 확장:

| | Embedding A | Embedding B |
|---|---|---|
| 모델 | `ko-sroberta-multitask` | Gemini Embedding |
| 비교 지표 | Faithfulness, Context Precision | Faithfulness, Context Precision |

Gemini API 기반 서비스 구축 경험을 보여주는 게 이번 프로젝트의 목적이므로, README에 두 임베딩의 RAGAS 점수를 나란히 비교해두면 "왜 이 임베딩을 선택했는가"에 대한 근거가 생긴다.