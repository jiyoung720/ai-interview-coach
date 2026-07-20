# ai-interview-coach

사용자의 이력서·포트폴리오 문서를 기반으로 개인화된 기술 면접 질문을 생성하고, 답변을 평가하는 RAG 기반 AI 면접 코치 서비스입니다.

> 단순히 RAG를 구현하는 데 그치지 않고, Retrieval·Faithfulness·Judge Calibration을 실험으로 검증하며 설계를 반복 개선했습니다. LangGraph 기반 Agent로 확장한 뒤에도 동일한 검증 방식을 유지했습니다. (자세한 진행 상황은 [Project Outcomes](#project-outcomes) 참고)

## Why this project?

이 프로젝트는 GPT-style Transformer를 PyTorch로 직접 구현한 [`korean-chatbot`](https://github.com/jiyoung720/korean-chatbot) 프로젝트의 후속작입니다.

- **`korean-chatbot`**: LLM 엔진 내부(Transformer, 토크나이저, 학습 루프)를 직접 구현하는 경험
- **`ai-interview-coach`**: 기성 LLM(Gemini API)을 활용해 실제 서비스를 설계·구축·서빙·평가하는 경험

두 프로젝트를 함께 보면 "모델 내부를 이해하는 능력"과 "실제 서비스를 만드는 능력"을 둘 다 보여줄 수 있도록 의도적으로 분리했습니다.

### Why RAG, not fine-tuning?

사용자마다 업로드하는 문서가 다르고 계속 바뀌기 때문에, 매번 파인튜닝하는 건 비용·시간 면에서 현실적이지 않습니다. 그래서 모델 가중치는 고정하고, 사용자 문서를 Vector DB에 저장한 뒤 검색해서 Gemini에 컨텍스트로 제공하는 구조로 설계했습니다. 이 구조는 사용자가 늘어나도 그대로 확장되고, 어떤 질문이 어떤 문서에서 나왔는지도 추적할 수 있습니다.

## Example Output

**질문 생성**
```bash
curl -X POST http://127.0.0.1:8000/generate-question \
  -H "Content-Type: application/json" \
  -d '{"query": "JWT 관련 경험"}'
```
```json
{"questions": ["FastAPI의 비동기(async/await) 처리 방식이 ...", "JWT를 이용한 사용자 인증을 구현할 때 ...", "..."]}
```

**답변 평가 + Agent 분기 (technical_score가 5 미만이면 Learning Tip → Followup 순차 생성)**
```bash
curl -X POST http://127.0.0.1:8000/evaluate-answer \
  -H "Content-Type: application/json" \
  -d '{"question": "JWT란 무엇인가?", "answer": "잘 모르겠습니다."}'
```
```json
{
  "technical_score": 0,
  "completeness_score": 0,
  "improvements": ["JWT의 개념과 구성 요소에 대한 학습이 필요합니다.", "..."],
  "retrieved_sources": ["jwt.md", "oauth.md"],
  "learning_tip": {
    "topic": "JWT의 기본 구조 및 Access/Refresh 토큰의 역할 분리",
    "reason": "JWT의 핵심 정의와 구성 요소를 파악하고, 토큰 역할 분리 개념을 보완해야 하기 때문입니다.",
    "recommended_sections": ["JWT (JSON Web Token)"]
  },
  "followup_question": "보통 토큰 기반 인증 시스템에서는 ... Access Token과 Refresh Token을 나누어 사용하는 보안상의 핵심적인 이유는 무엇인가요?"
}
```

`learning_tip.topic`과 `followup_question`이 같은 주제를 겨냥합니다. Learning Tip이 먼저 핵심 약점을 정하고 Followup이 그 결과를 이어받는 순차 구조이기 때문입니다.

Faithfulness 문제(컨텍스트에 없는 내용을 생성하는 것)를 실측으로 발견한 뒤, RAGAS로 정량화했습니다. 자세한 수치는 [Key Findings](#key-findings) 참고.

## Architecture

```mermaid
flowchart TB
    subgraph ChainA["Chain A - 질문 생성"]
        A1[Retrieval Node<br/>User Docs] --> A2[Generation Node<br/>Gemini Structured Output]
    end
    subgraph ChainB["Chain B + Agent v2 - 답변 평가"]
        B1[Retrieval Node<br/>Interview KB] --> B2[Judge Node<br/>Gemini Structured Output]
        B2 --> BD{Decision<br/>technical_score?}
        BD -->|"< 5"| B3[Learning Tip Node<br/>약점 기반 학습 추천]
        B3 -->|"topic 전달"| B5[Followup Node<br/>Learning Tip의 topic을<br/>이어받아 꼬리질문 생성]
        BD -->|">= 5"| B4[End]
        B5 --> B4
    end
```

**technical_score가 5 미만이면 Agent가 Learning Tip → Followup을 순차로 생성합니다.** 고정된 파이프라인이 아니라, State(evaluation_result)에 따라 다음 행동이 갈리는 것이 이 프로젝트의 Agent 형태입니다. Learning Tip과 Followup을 병렬이 아닌 순차로 설계한 이유는 이렇습니다. 두 노드가 같은 약점(improvements)을 각자 독립적으로 해석하면 서로 다른 부분을 짚을 위험이 있어, Learning Tip이 먼저 핵심 주제(topic)를 정하고 Followup이 그 결과를 이어받도록 했습니다.

두 체인 모두 LangChain LCEL로 먼저 구현한 뒤, LangGraph StateGraph로 마이그레이션했습니다. Retrieval과 Judge/Generation을 별도 Node로 분리해 (1) 문제 발생 시 어느 단계인지 바로 특정할 수 있고, (2) 평가 점수에 따른 조건부 분기(Agent)를 Node 단위로 추가할 수 있도록 설계했습니다. 기존 LCEL 코드(`rag/chains.py`)는 삭제하지 않고 그대로 보존해, Migration 과정 자체를 코드로 증명할 수 있게 했습니다.

## Key Findings

코드를 짜는 과정에서 발견한 것들입니다. 단순히 "작동한다"가 아니라 "왜 그렇게 작동하는지"를 확인한 실험들입니다. 전체 내용은 [실험 로그](docs/experiment_log.md)에 있습니다.

- **Retrieval 관련 실험들이 모두 같은 결론으로 수렴함**: Semantic Retrieval 검증(Day 1), Context Precision 단독 실험, 첫 Embedding 비교, KB 확장 후 재실험까지 서로 다른 목적의 실험에서도 동일한 패턴이 반복적으로 관찰됨. KB가 2개 문서일 때는 Context Precision과 Embedding 비교가 항상 만점이라 변별력을 갖지 못했고, 11개로 확장한 뒤에야 Retrieval 관련 지표들이 실제 차이를 드러내기 시작함.
- **혼합 주제 chunk는 유사도 점수를 왜곡시킬 수 있음**: 여러 주제가 섞인 긴 chunk가 단일 주제의 짧은 chunk보다 더 높은 유사도를 받는 경우를 실측으로 확인. KB는 파일당 주제 하나로 작성하도록 반영.
- **문서 분리의 단위는 파일 크기가 아니라 "완결된 근거 단위(retrieval unit)"**: Retrieval 전용 평가셋(20문항)으로 재검증한 결과, 독립된 개념이 나열된 문서(`postgresql.md`, `spring.md`)는 하위 주제별로 분리할수록 검색 품질이 개선됐지만, 비교형 문서(`session_vs_token.md`)는 반대로 정의·차이·확장성 비교를 한 chunk에 유지해야 품질이 좋아짐을 확인. 이 원칙을 반영해 KB를 재구성한 뒤 Top-1 정확도 100%(20/20), Faithfulness 0.9708, Context Precision 1.0000까지 개선.
- **Retriever 성공이 Faithfulness를 보장하지는 않음**: 검색이 정확해도 생성 모델이 컨텍스트 밖 내용을 추가할 수 있음을 직접 확인. RAGAS로 정량화한 결과, Calibration Set 17개 케이스의 평균 Faithfulness는 0.4412. bad/average 카테고리에서 편차가 크게 나타나 Judge의 technical_score와는 다른 것을 측정하는 지표임을 확인.
- **임베딩 비교 결론이 표본 확대 후 뒤집힘**: KB가 2개 문서였을 때는 두 임베딩이 항상 동일했고, 11개로 확장한 뒤 5문항 표본에서는 Gemini Embedding이 더 안정적으로 관찰됐음(다만 표본이 작아 일반화는 보류). Retrieval Unit 재설계로 KB를 18개로 재구성한 뒤 20문항 평가셋으로 재실행하자 정반대로 `ko-sroberta-multitask`가 Top-1 100%(20/20)·Faithfulness 0.9708로 Gemini Embedding(95.0%·0.9500)보다 근소하게 우세했음. 작은 표본에서의 결론을 그대로 일반화하면 안 된다는 것을 직접 확인한 사례.
- **Judge Calibration으로 프롬프트/테스트 데이터 결함을 구분해냄**: Judge 채점을 그대로 신뢰하지 않고 Calibration Set(17개)으로 검증. 실패 원인을 분석한 결과 Judge가 아니라 Calibration Set 자체의 설계 결함(동일 답변에 서로 다른 기대치 부여)이 원인이었음을 발견, 재설계를 통해 정확도를 52.9%에서 94.1%로 향상시킴.
- **LangGraph 마이그레이션 검증에 Calibration Set을 회귀 테스트로 재사용**: LCEL에서 LangGraph로 Migration한 이후에도 기존 Judge 동작이 유지되는지 확인하기 위해, 그래프로 옮긴 뒤 동일한 Calibration Set을 재실행(88.2%)함. 실패 케이스가 LCEL 버전에서도 존재했던 경계선 변동과 동일함을 확인했고, 마이그레이션이 새로운 오분류를 만들지 않았음을 검증.
- **Agent 확장 시 병렬보다 순차가 나은 경우가 있음**: Learning Tip과 Followup을 처음엔 병렬 노드로 설계했으나, 두 노드가 같은 약점(improvements)을 각자 독립적으로 해석하면 서로 다른 부분을 짚을 위험을 발견. Learning Tip이 먼저 topic을 정하고 Followup이 그 결과를 이어받는 순차 구조로 변경해, 두 출력이 항상 같은 주제를 가리키도록 함.

## Tech Stack
 
- **Backend**: FastAPI
- **패키지 관리**: uv
- **Framework**: LangChain (LCEL) → LangGraph (StateGraph) 마이그레이션
- **Vector DB**: Chroma (`hnsw:space=cosine`), Interview KB 18개 문서 (retrieval unit 기준으로 재구성)
- **Embedding**: `ko-sroberta-multitask` (기본), Gemini Embedding(`gemini-embedding-001`, 비교 실험용)
- **LLM**: Gemini 3.5 Flash (structured output)
- **Evaluation**: Semantic Retrieval Test, Judge Calibration Set(94.1%), RAGAS Faithfulness(Calibration Set 기준 평균 0.4412), Retrieval 전용 평가셋(20문항: Top-1 100%·Faithfulness 0.9708·Context Precision 1.0000), Embedding 비교(20문항 기준: ko-sroberta 100%/0.9708 > Gemini Embedding 95%/0.9500, ko-sroberta 최종 채택)

## Project Outcomes

- Semantic Retrieval, Faithfulness, Judge Calibration을 실험으로 검증하며 설계를 반복 개선
- LangChain LCEL 기반 RAG(Retrieval → Generation/Judge)를 LangGraph StateGraph로 마이그레이션
- Judge Calibration Set(17개)으로 평가 로직을 검증하고, 이를 마이그레이션 회귀 테스트로 재사용
- Retrieval / Judge / Generation을 독립적인 Graph Node로 분리해 디버깅 가능성과 확장성 확보
- technical_score 기반 Agent를 구현하고, Learning Tip이 생성한 topic을 Followup이 이어받도록 설계하여 Agent 출력의 일관성을 확보
- RAGAS(Faithfulness, Context Precision)를 도입하고, KB 규모(2개에서 11개로)가 지표 변별력에 미치는 영향을 실험으로 확인
- 동일 KB에 두 임베딩(`ko-sroberta-multitask`, Gemini Embedding)을 각각 인덱싱해 비교 실험 파이프라인 구축
- Retrieval 전용 평가셋(20문항)을 구축하고, 문서 분리 전략을 "완결된 근거 단위" 기준으로 재설계해 Top-1 정확도 100%·Faithfulness 0.9708까지 개선
- Embedding 비교를 20문항 평가셋으로 재실행한 결과, 기존 5문항 표본(Gemini 우세) 결론이 뒤집혀 ko-sroberta-multitask가 Top-1 100%·Faithfulness 0.9708로 근소 우세해 최종 임베딩으로 채택

## API

### `POST /documents`
```bash
curl -X POST http://127.0.0.1:8000/documents -F "file=@tests/fixtures/sample_user_doc.md"
```

### `POST /generate-question`
```bash
curl -X POST http://127.0.0.1:8000/generate-question \
  -H "Content-Type: application/json" \
  -d '{"query": "JWT 관련 경험"}'
```
응답: `{"questions": ["...", "...", ...]}`

### `POST /evaluate-answer`
```bash
curl -X POST http://127.0.0.1:8000/evaluate-answer \
  -H "Content-Type: application/json" \
  -d '{"question": "JWT란 무엇인가?", "answer": "..."}'
```
응답: `{"technical_score": ..., "completeness_score": ..., "strengths": [...], "improvements": [...], "overall_feedback": "...", "retrieved_sources": [...], "learning_tip": {"topic": ..., "reason": ..., "recommended_sections": [...]} | null, "followup_question": "..." | null}`

`technical_score`가 5 미만이면 Agent가 `learning_tip`과 `followup_question`을 순차로 생성합니다 (점수가 충분하면 둘 다 `null`). `followup_question`은 `learning_tip.topic`을 이어받아 동일 주제를 겨냥합니다.

## 실행 방법
 
```bash
uv sync
cp .env.example .env  # GEMINI_API_KEY 채우기
uv run uvicorn app.main:app --reload
```

## 문서

- [프로젝트 명세서](docs/project_spec_v1.md): Phase별 상세 진행 상황(Roadmap) 포함
- [실험 로그](docs/experiment_log.md)