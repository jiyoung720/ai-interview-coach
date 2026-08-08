# AI Interview Coach with RAG - 프로젝트 명세서

> 현재 구현 기준의 문서입니다. 1-5번이 현재 상태 요약이고, 그 뒤는 Phase별 진행 기록입니다.
> 판단 근거와 시행착오는 [실험 로그](experiment_log.md)에 있습니다.

---

## 1. 프로젝트 목표와 현재 구현 범위

사용자가 이력서/자기소개서/포트폴리오/프로젝트 README(`.md`, `.txt`, `.pdf`)를 업로드하면, 그 문서를 기반으로 개인화된 면접 질문을 생성하고, 사용자의 답변을 평가하는 RAG 기반 AI 면접 코치 서비스.

메인 프로젝트(`korean-chatbot`, GPT-style Transformer 직접 구현)의 후속작으로, 기성 LLM(Gemini API)을 활용한 실서비스형 AI 시스템 구축·서빙·평가 역량을 보여주는 것이 목적.

**지원 파일 형식은 `.md`, `.txt`, `.pdf`이다.** PDF는 `pypdf`로 텍스트를 추출한다(Phase 9에서 추가). 스캔 이미지 PDF처럼 텍스트가 없는 경우는 422로 거부한다.

## 2. 현재 아키텍처

### Collection 1: User Docs
사용자가 업로드하는 이력서/포트폴리오. `POST /documents`로 업로드, Chunking → Embedding(`ko-sroberta-multitask`) → Chroma.

### Collection 2: Interview KB
운영자가 직접 작성하는 고정 콘텐츠. 현재 **29개 문서(chunk 54개)**. 인증(jwt, jwt_logout_invalidation, oauth, token_auth, session_auth, session_vs_token, authorization_header), HTTP·웹(http_method, http_status_code, http_idempotency, rest_api_design, cors, https_tls, tcp_udp, browser_rendering), 서버(fastapi, async_sync, spring_di, spring_boot, spring_bean_scope, spring_layered_architecture, docker, caching), DB(transaction, postgresql_index, db_normalization, db_n_plus_one, db_lock, db_execution_plan).

11 → 18개는 다루는 주제를 늘린 것이 아니라 "문서 분리 단위 = 완결된 근거 단위(retrieval unit)" 원칙에 따른 재구성이었고(Phase 6), 18 → 29개에서 처음으로 주제 자체가 늘었다(Phase 15).

`scripts/load_kb.py`로 인덱싱한다. **적재 대상은 앱이 실제로 검색하는 컬렉션을 따라간다.** 컬렉션을 지목해두면 임베딩을 바꿀 때 배포된 컨테이너가 빈 인덱스를 검색하게 되고, 크래시 없이 모든 질문이 "근거 없음"으로 빠진다(Phase 17에서 실제로 겪음).

### Chain A: 질문 생성
```
User Docs Retrieval Node → Generation Node (Gemini Structured Output) → InterviewQuestions
```
LangGraph StateGraph로 구현. `rag/graph.py`의 `build_chain_a_graph()`.

### Chain B + Agent v3: 답변 평가
```
Interview KB Retrieval Node → decide_scope
    → (근거 없음) Out of Scope Node     : 채점 보류. 점수를 만들지 않음
    → (근거 있음) Judge Node → Decision(technical_score 구간)
        → (0~3점)  Fundamentals Node        : 개념 자체를 설명
        → (4~6점)  Learning Tip Node → Followup Node : 약점 보완 코칭 + 꼬리질문
        → (7~10점) Advanced Question Node   : 심화 질문
```
`rag/graph.py`의 `build_interview_agent_graph()`. 조건부 분기 함수는 `decide_next_step()` (구현 초기에는 `decide_followup()`으로 불렀으나, Learning Tip 추가 후 이름을 바꿈).

v2까지는 `technical_score < 5` 하나로만 갈렸고 점수가 높으면 아무 노드도 실행되지 않아, 두 갈래 중 한쪽이 비어 있었다. v3에서는 **구간마다 필요한 코칭의 종류가 다르다**는 기준으로 세 갈래로 확장해 모든 점수대에서 결과가 나오도록 했다. 경계값은 `FUNDAMENTALS_THRESHOLD = 4`, `ADVANCED_THRESHOLD = 7`.

4-6점 경로에서는 Learning Tip이 먼저 실행되어 핵심 약점(topic)을 정하고, Followup이 그 topic을 이어받아 동일 주제의 꼬리질문을 생성한다 (병렬이 아닌 순차 설계. 두 노드가 같은 약점을 각자 다르게 해석하는 것을 막기 위함).

### 멀티턴 세션 그래프 (Phase 11)
```
START → Retrieval → decide_scope
  ↑                   ├ (근거 없음) Out of Scope → END   (점수를 만들지 않음. Phase 17)
  │                   └ (근거 있음) Judge → Decision
  │                            ├ (0~3점)  Fundamentals → END        (다음 질문이 없어 루프 제외)
  │                            ├ (4~6점)  Learning Tip → Followup ─┐
  │                            └ (7~10점) Advanced ────────────────┤
  │                                                        decide_continue
  │                                                          ├ "end"      → END
  └────────── await_answer (interrupt로 대기) ←──────────────┘
```
`decide_scope`는 채점보다 먼저 판단한다. 1순위 문서와의 거리가 임계값(`SCOPE_DISTANCE_THRESHOLD`, 현재 0.311) 이상이면 Judge를 아예 부르지 않는다. 검색은 근거가 없어도 항상 상위 3개를 돌려주므로, 걸러내지 않으면 엉뚱한 문서를 근거로 점수가 매겨진다.
`rag/graph.py`의 `build_interview_session_graph()`. 위 단발성 그래프와 **노드는 전부 공유하고 배선만 다르다.**

`await_answer` 노드가 `interrupt()`를 호출하면 실행이 그 자리에서 멈추고 State가 checkpointer에 저장된다. 사용자의 답변을 `Command(resume=답변)`으로 넘겨 재개하면 `retrieval`로 이어져 새 질문으로 다시 채점한다. **이 사이클이 LangGraph를 쓰는 근거다.** 조건부 분기까지는 LCEL의 `RunnableBranch`로도 가능하지만, 되돌아가는 흐름과 실행 중간에 멈췄다 재개하는 동작은 LCEL로 표현할 수 없다.

기존 `build_interview_agent_graph()`를 고치지 않고 따로 둔 이유는 `/evaluate-answer`와 Calibration 스크립트들이 그대로 동작해야 하기 때문이다(LCEL 코드를 보존한 것과 같은 방식).

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

    # 멀티턴 루프 (Phase 11). 세션 그래프에서만 채워진다
    turn: int                                   # 현재 턴 번호
    history: list[dict]                         # 지난 턴 요약 (질문/답변/점수/경로)
    next_question: str                          # 다음 턴에 물을 질문
    end_reason: str                             # 루프 종료 사유
```
점수 구간에 따라 셋 중 한 경로만 실행되므로 나머지 키는 State에 존재하지 않는다. API 레이어에서 `.get()`으로 조회해 없으면 `null`로 응답한다.

멀티턴에서는 `question`/`answer`/`evaluation_result`가 턴마다 덮어써지므로, 이전 턴의 내용은 `await_answer` 노드가 `history`에 옮겨 담는다.

### API
| Endpoint | 역할 |
|---|---|
| `GET /` | 데모 프론트엔드(`static/index.html`) 서빙 |
| `GET /health` | 헬스체크 (LLM 없는 기준선, healthcheck/CI/성능 측정에 사용) |
| `POST /documents` | User Docs 업로드 + 인덱싱 |
| `POST /generate-question` | Chain A 실행 |
| `POST /evaluate-answer` | Chain B + Agent 실행 (단발성). 점수 구간에 따라 `concept_explanation` / (`learning_tip` + `followup_question`) / `advanced_question` 중 하나가 채워지고, `next_action`으로 실행된 경로를 알 수 있다 |
| `POST /interview/start` | 멀티턴 세션 시작. 첫 질문·답변으로 1턴을 실행하고 `session_id`를 발급 |
| `POST /interview/answer` | `session_id`와 답변으로 다음 턴 진행. 종료된 세션은 409, 없는 세션은 404 |

### 프론트엔드
순수 HTML/CSS/JS 단일 페이지(`static/`). FastAPI가 정적 파일을 직접 서빙하므로 별도 프론트 서버·CORS 설정·빌드 단계가 없다. 단일 페이지 데모에 SPA 프레임워크(React 등)는 과하다고 판단해 의도적으로 배제.

업로드 → 질문 생성 → **면접 진행**의 3단계이며, 마지막 단계는 `/interview/*`를 호출하는 대화형이다. 턴마다 질문·내 답변 말풍선과 점수 뱃지, 코칭이 타임라인에 쌓이고, 다음에 답할 질문은 입력창 바로 위에 고정 표시된다. 코칭 블록에서는 꼬리질문·심화질문 본문을 빼서 같은 질문이 두 군데 보이지 않도록 했다.

세션이 끝나면 **요약 모달**이 뜬다. 상단에 턴별 점수 흐름(`턴1 8/7 › 턴2 6/5 › 턴3 10/9`)을 한 줄로 두어, 어느 턴에서 흔들렸는지 스크롤 없이 보이게 했다. 탭이나 화살표로 한 턴씩 넘기는 방식은 쓰지 않았다. 요약에서 가장 알고 싶은 것이 턴 간 비교인데 그 방식은 한 번에 하나만 보여줘 비교를 없앤다. 남은 턴을 채우지 않고 나갈 수 있도록 **면접 종료** 버튼을 두고, 되돌릴 수 없으므로 확인창을 거친다.

## 3. 검증 결과 요약

| 항목 | 결과 | 의미 |
|---|---|---|
| Judge Calibration (v1, 17개) | 최고 94.1% (LCEL 시절) / 재측정 88.2% | Gemini Judge의 채점이 사람이 정한 기대 범위와 얼마나 일치하는지의 비율. 94.1%는 LCEL 구현 당시 값이고, LangGraph 이전 후 같은 세트로 재측정하면 88.2%다. 실패 케이스는 모두 경계선 변동이었다 |
| Judge Calibration (v2, 44개) | 경로 정확도 88.4-93.0% (3회) | v1의 기대 범위가 분기 경계와 어긋나 있어 재설계한 세트. 점수가 맞았는지가 아니라 **올바른 코칭 경로로 갔는지**를 잰다. 3회 반복으로 확인한 **변동 폭은 약 5%p**이며, 이보다 작은 차이는 노이즈로 판단한다 |
| RAGAS Faithfulness | 평균 0.4412 | Calibration Set 17개 답변 각각이 Interview KB의 근거 문서에 실제로 부합하는 정도의 평균. bad/average 카테고리에서 편차가 크게 나타남. 이 역시 서비스 전체 정확도가 아니라, Calibration Set이라는 특정 표본에 대한 근거성 점수 평균임 |
| RAGAS Context Precision | 0.8000 (KB 11개 기준) | Retriever가 검색한 chunk 중 실제로 관련 있는 chunk가 상위에 오는 정도. KB가 2개 문서였을 때는 항상 1.0000이라 변별력이 없었고, 11개로 확장한 뒤에야 의미 있는 값이 나옴 |
| Embedding 비교 (초기, 5문항) | Gemini Embedding이 헷갈리는 케이스 1건에서 더 안정적 | KB 11개 기준, 표본이 작아 일반화 보류로 남겨뒀던 초기 결과. 이후 20문항 재실행에서 결론이 뒤집힘(아래 행 참고) |
| Retrieval 평가셋 (20문항, reference 기반) | Top-1 100% (20/20), Faithfulness 0.9708, Context Precision 1.0000 | KB를 "완결된 근거 단위" 기준으로 재구성(postgresql/spring 분리, session_vs_token 재구성)한 뒤의 최종 결과(ko-sroberta 기준). Judge Calibration Set의 Faithfulness(0.4412)와는 목적이 다른 별도 실험이며, reference(정답)를 기준으로 KB·Retrieval 자체의 품질을 측정 |
| Embedding 비교 (20문항, KB 18개) | ko-sroberta 100%/0.9708 > Gemini Embedding 95%/0.9500 | Retrieval Unit 재설계 이후 20문항 평가셋으로 재실행. 5문항 표본(Gemini 우세)과 정반대 결론으로, 표본 확대가 결론을 뒤집은 사례다. 이 시점에는 ko-sroberta를 채택했다 |
| Embedding 비교 (30문항, KB 29개) | **Gemini 100%/0.9702 > ko-sroberta 86.7%/0.8931** | KB를 29개로 늘리자 결론이 **또 뒤집혔다.** ko-sroberta가 틀린 4문항은 전부 신규 DB 주제였고, "N+1 문제"를 `http_status_code.md`로 보내는 등 저빈도 전문용어를 벡터로 구분하지 못했다. KB가 작을 때는 주제가 서로 멀어 드러나지 않던 한계다. Gemini Embedding으로 교체 (Phase 15) |
| 채점 정확도 (임베딩 교체 후) | 경로 정확도 90.9% | 검색이 13.3%p 좋아졌는데 채점 정확도는 노이즈 범위(5%p) 안에서 그대로였다. Judge가 답변 자체를 보고 채점하기 때문이다. **중간 지표와 최종 지표를 구분해서 말해야 한다** |
| 범위 밖 판정 (65문항, group 5-fold) | 재현율 100%, 정밀도 93.8%, 범위 안 통과 93.3% | 임계값 0.311. 전체 데이터로는 오탐 1건이지만 fold 4에서 범위 안 통과가 75%로 떨어져, 일반화 성능이 더 낮음을 교차 검증이 드러냈다. 같은 주제를 표현만 바꾼 문항이 train/test에 걸치지 않도록 `topic` 단위로 묶어 나눴다 (Phase 17) |

## 4. 핵심 설계 변경 이력

- **Structured Output 도입**: Gemini의 자유 텍스트 출력이 API 계약과 안 맞아 `with_structured_output()` + Pydantic 스키마로 전환
- **RAGAS 적용 대상 재설정**: 초기 계획은 Chain A(질문 생성)에 Faithfulness를 적용하는 것이었으나, 면접 질문은 "주장"이 아니라 "질의"라 지표 전제와 안 맞음을 발견. Faithfulness 적용 대상을 Chain B(사용자 답변 + retrieved context)로 재설정
- **Calibration Set 재설계**: Judge 채점 실패를 Judge 성향이 아니라 Calibration Set 자체의 설계 결함(동일 답변에 서로 다른 기대치 부여)으로 진단, 재설계로 52.9% → 94.1% 향상
- **LCEL → LangGraph 마이그레이션**: 기존 LCEL 코드(`rag/chains.py`)는 보존한 채 StateGraph로 재구현. Calibration Set을 회귀 테스트로 재사용해 마이그레이션이 새로운 오분류를 만들지 않았음을 검증
- **Agent v1 → v2**: 조건부 분기(Followup만 생성)에서, Learning Tip 노드를 추가하고 병렬이 아닌 순차 구조로 설계 변경
- **KB 2개 → 11개 확장**: Context Precision과 Embedding 비교가 KB 2개 문서로는 변별력을 갖지 못함을 확인, 교차 언급 문서를 포함해 11개로 확장
- **requirements.txt → uv**: `pyproject.toml` + `uv.lock`으로 패키지 관리 전환
- **Retrieval Unit 재설계 (11개 → 18개)**: "chunk당 주제 하나" 원칙을 모든 문서에 동일하게 적용하는 대신, 독립 개념 나열 문서(postgresql, spring)는 하위 주제별로 분리하고 비교형 문서(session_vs_token)는 비교 근거를 한 chunk에 유지하도록 재구성. Retrieval 전용 평가셋(20문항)으로 검증해 Top-1 100%·Faithfulness 0.9708까지 개선
- **Embedding 비교 재검증 (20문항)**: 5문항 표본에서의 "Gemini Embedding이 더 안정적" 결론이 Retrieval Unit 재설계 후 20문항 재실행에서 뒤집힘. ko-sroberta-multitask가 Top-1 100%·Faithfulness 0.9708로 근소 우세해 이 시점의 임베딩으로 채택 (이후 Phase 15에서 다시 뒤집힘, 아래 참고)
- **Agent v2 → v3 (점수 구간별 다중 분기)**: 단일 조건(`< 5`)으로 갈리던 구조에서 3구간 분기로 확장. "분기를 늘린다"가 아니라 "구간마다 필요한 코칭의 종류가 다르다"를 기준으로, 0-3점은 개념 설명, 4-6점은 기존 약점 보완 코칭, 7-10점은 심화 질문을 반환하도록 설계. 빈 경로가 사라져 모든 점수대에서 결과가 나온다
- **멀티턴 루프 도입 (그래프에 사이클 추가)**: 모든 경로가 한 방향으로 흐르고 끝나던 구조에서, `await_answer` 노드가 `interrupt()`로 멈췄다가 `Command(resume=...)`으로 재개하는 사이클을 추가. 조건부 분기까지는 LCEL로도 표현할 수 있어 "왜 LangGraph인가"에 답하기 어려웠는데, 되돌아가는 흐름과 실행 중단·재개는 LCEL로 만들 수 없어 채택 근거가 구조로 확보됨. 단발성 그래프는 그대로 두어 기존 API와 스크립트의 동작을 보존
- **채점 결과에 근거 추가 (Phase 12)**: 점수만 주면 사용자가 납득할 수 없다는 지적에 따라 감점 사유·감점 폭과 역량 수준을 함께 반환하도록 `EvaluationResult` 스키마 확장. 착수 시엔 채점 편차도 줄어들 것으로 봤으나 측정 결과 효과가 확인되지 않아 가설을 기각. 대신 Calibration Set을 44개로 재설계하며 판정 기준을 코칭 경로로 바꾸고 변동 폭(약 5%p)을 확보
- **KB 검색 임베딩 교체 (Phase 15)**: KB를 18개에서 29개로 늘리자 `ko-sroberta`가 "멱등성", "N+1 문제" 같은 저빈도 전문용어를 벡터로 구분하지 못하는 것이 드러나 Gemini Embedding으로 교체(30문항 기준 86.7% → 100%). **업로드 문서 검색은 ko-sroberta를 유지**했다. 이력서는 사용자가 올린 개인정보라 외부 API로 보내지 않는다. 어느 임베딩을 쓸지는 `get_interview_kb_retriever` 한 곳에서 정하도록 모아, 다음 교체 때 한 줄만 바꾸면 되게 했다
- **채점 전 범위 판정 추가 (Phase 17)**: 검색은 `k=3`이라 KB에 근거가 없어도 항상 문서 3개를 돌려주므로, 걸러내지 않으면 엉뚱한 문서로 점수가 매겨진다. `retrieval` 다음에 조건부 엣지를 두어 1순위 거리가 임계값 이상이면 Judge를 아예 부르지 않는다. **분기가 채점보다 앞에 생긴 첫 사례**이며, 점수·레벨·코칭을 만들지 않고 보류만 안내한다

## 5. 한계와 다음 단계

- **평가셋이 다시 천장에 닿았다**: Phase 17에서 범위 밖 문항을 넣어 변별력을 만들었으나, in-scope 38문항은 여전히 Top-1 100%·Context Precision 1.0000이다. KB 문서를 보강해도 효과를 측정할 수 없으므로, **보강에 앞서 in-scope 문항을 어렵게 만들어야 한다**
- **KB 문서 분량이 고르지 않다**: 평균 555자인데 `token_auth.md` 133자, `spring_boot.md` 185자 등 근거로 쓰기에 얇은 문서가 남아 있다. Phase 15에서 보강하려다 위 항목(측정 불가) 때문에 미뤘다
- **범위 밖 판정의 검증이 얕다**: 재현율 100%가 나왔지만 진짜 경계에 걸친 문항이 `프로세스와 스레드`(거리 0.321) 하나뿐이었다. 또 65문항에 주제가 47개라 그룹당 1.4문항이어서 group 5-fold의 효과가 제대로 나지 않는다
- **세션 상태가 서버 메모리에만 있음**: Phase 11의 멀티턴 루프는 `MemorySaver`로 세션을 보관한다. 컨테이너를 재시작하면 진행 중이던 세션이 사라지고, 인스턴스를 여러 개로 늘리면 세션이 특정 인스턴스에 묶인다. 실사용 규모에서는 `SqliteSaver`나 Postgres 기반 checkpointer로 교체해야 한다(단일 인스턴스 데모라 현재는 감수)
- **세션 도중 질문 변경 불가**: 면접이 진행 중이면 다른 질문으로 갈아탈 수 없다(그래프가 그 세션의 맥락을 들고 있어 중간에 바꾸면 흐름이 깨진다). 화면에서는 질문 목록을 잠근 모습으로 보여주고, 끝내려면 "면접 종료" 버튼을 쓴다. 단 근거가 없어 보류된 경우는 예외로 다시 고를 수 있다(채점 자체가 없었으므로 맥락이 끊기지 않는다)
- **채점 편차가 남아 있음**: Phase 12에서 루브릭을 도입했으나 편차 감소 효과는 확인되지 않았다. 같은 조건으로 반복 측정해도 약 5%p가 흔들리며, 특히 분기 경계(4점, 7점) 부근 케이스가 반복적으로 넘나든다. 프롬프트로는 해결되지 않았으므로, 필요하다면 경계 자체를 재검토하거나 경계 부근에서 복수 채점 후 다수결하는 방식을 검토해야 한다
- **응답 지연을 코드로는 줄일 수 없음**: Phase 8 ⑤-⑦에서 시간·프로세스 상태·패킷 세 각도로 측정한 결과, 지연의 대부분이 Gemini 응답 대기였다. 서버 연산도 네트워크도 병목이 아니므로 인스턴스 사양을 올려도 개선되지 않는다. 줄이려면 설계를 바꿔야 한다(스트리밍 응답, 병렬 호출, 캐싱). 현재는 순차 설계의 대가를 알고 유지하는 상태
- **HTTPS 미적용**: WireShark 캡처로 요청·응답 JSON이 평문으로 노출되는 것을 직접 확인했다. 데모 단계라 감수하고 있으나, 실사용자를 받으려면 TLS가 선행되어야 한다 (고도화 로드맵 Phase 14에서 해소 예정)

Phase 1-13, 15, 17은 완료됐다. 남은 것은 Phase 14(HTTPS·도메인, 도메인 미확보로 보류)와 Phase 16(채용공고 매칭)이다. 아래 [고도화 로드맵](#고도화-로드맵-2026-07-29-멘토링-반영) 참고.

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
- [x] Embedding 비교(ko-sroberta vs Gemini)를 이 20문항 세트로 재실행, ko-sroberta 100%/0.9708 > Gemini 95%/0.9500로 채택 (기존 5문항 결론이 뒤집힘. 이후 Phase 15에서 KB를 29개로 늘리자 다시 뒤집혀 Gemini로 교체)

### Phase 7: Agent 다중 분기 (완료)
v2까지는 `technical_score < 5` 하나로만 갈리고 점수가 높으면 아무 동작도 하지 않아 분기가 단조로웠다. 구간별로 서로 다른 종류의 코칭을 제공하도록 확장.

- [x] `decide_next_step()`을 3구간 분기로 확장 (`FUNDAMENTALS_THRESHOLD=4`, `ADVANCED_THRESHOLD=7`)
  - 0-3점: `fundamentals_node`, 개념 자체를 설명 (`ConceptExplanation`)
  - 4-6점: 기존 `learning_tip_node` → `followup_node` 유지
  - 7-10점: `advanced_question_node`, 심화 질문 (`AdvancedQuestion`)
- [x] 분기 로직 0-10점 전 구간 전수 검증 (순수 함수라 LLM 호출 없이 검증 가능)
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
- [x] `test` job: 분기 로직·그래프 구조·chunking 등 **API 키가 필요 없는 계층**만 검증하도록 설계해 비밀값을 CI에 노출하지 않음 (현재 35개)
- [x] `docker-build` job: Dockerfile이 깨끗한 환경(linux/amd64 러너)에서 빌드되는지 확인
- [x] CUDA 패키지 재유입 검사: 이미지에 nvidia/triton이 포함되면 빌드 실패 처리. ①에서 최적화가 **에러 없이 조용히 풀렸던 전례**가 있어 자동 검사로 고정
- [x] 스모크 테스트: 컨테이너를 실제로 띄워 헬스체크 응답까지 확인 (KB 인덱싱은 임베딩만 쓰므로 더미 키로 가능)
- [x] 프로덕션 이미지에서 dev 의존성 제외 (`uv sync --no-dev`)

**③ AWS EC2 수동 배포 (완료)**
- [x] 인스턴스 타입을 **측정 결과에 근거해** 선정: `t3.small`(RAM 2GB, x86_64, 서울 리전)
  - 로컬 컨테이너 메모리를 먼저 측정한 결과 유휴 757MB, 요청 처리 중 피크 **1.154GB**. 프리티어 `t2.micro`(RAM 1GB)는 피크만으로 전체 RAM을 초과해 OOM이 확실했으므로 배제
  - 대안이었던 (b) swap 설정, (c) 배포 환경만 Gemini Embedding API로 전환은 채택하지 않음. (c)는 이미지가 500MB 수준으로 줄지만 검증된 최적 구성(ko-sroberta, 20문항 Top-1 100%)을 배포용으로 바꿔야 해 트레이드오프가 큼
    - **후일담**: Phase 15에서 KB 검색이 실제로 Gemini Embedding으로 바뀌면서 이 트레이드오프는 사라졌다. 다만 업로드 문서 검색이 ko-sroberta를 유지하므로 torch는 이미지에 남아 있어, 여기서 기대했던 500MB 감축은 얻지 못했다
- [x] 보안 그룹: 22번은 내 IP만, 8000번은 0.0.0.0/0. 서비스 포트와 관리 포트를 분리해 공개 범위를 다르게 설정
- [x] EC2에서 직접 빌드 후 Compose로 기동, 외부(로컬 노트북)에서 `curl http://<퍼블릭IP>:8000/` 응답 확인
- [x] **EBS 볼륨 8GB → 20GB 확장**: 최초 8GB에서 빌드 중 `no space left on device`로 실패. 최종 이미지는 2.7GB지만 빌드 중간 레이어와 캐시가 훨씬 많은 공간을 요구한다. 확장 후 빌드 완료 시점 사용량은 11GB로, **빌드에만 약 8.6GB가 필요**했다
- 운영 참고: `t3.small`은 프리티어가 아니므로 미사용 시 인스턴스 중지 필요. 중지 후 재시작하면 퍼블릭 IP가 변경됨(Elastic IP 미적용)

**④ GitHub Actions (CD) (완료)**
- [x] `deploy` job 추가. `needs: [test, docker-build]`로 앞 두 job에 의존시켜 **테스트가 깨지면 배포되지 않도록** 구성. PR에서는 실행되지 않음
- [x] 배포 후 외부에서 헬스체크로 실제 응답 확인 (배포 명령 성공과 서비스 정상은 별개이므로 단계를 분리)
- [x] **Dockerfile 레이어 순서 개선**: 임베딩 모델 다운로드(449MB)가 코드 COPY 뒤에 있어 코드 한 줄만 바뀌어도 매 배포마다 모델을 다시 받는 구조였다. 모델명을 직접 지정해 코드 의존을 끊고 앞으로 이동, 코드만 변경한 재빌드가 1.6초로 단축
- [x] **보안 그룹 재조정**: 첫 배포가 `dial tcp <IP>:22: i/o timeout`으로 실패. ③에서 22번을 "내 IP만"으로 제한했는데 CD는 러너가 접속하므로 "사람만 접속"이라는 전제가 깨졌다. 키 인증만 허용되므로 포트를 열어도 `.pem` 없이는 접속 불가
- [x] **Docker Hub 경유 방식으로 전환 (2026-07-29)**: 초기에는 EC2에서 `git pull` 후 직접 빌드했으나, CI가 빌드해 Docker Hub에 올리고 EC2는 받아서 실행하는 구조로 바꿨다. EC2에 소스 코드가 필요 없어지고 `t3.small`의 CPU·디스크 부담이 사라진다. `latest`와 커밋 SHA 두 태그를 달아 특정 커밋으로 되돌릴 수 있게 함
  - 계기: 맥(arm64)에서 `--platform linux/amd64` 빌드가 QEMU 에뮬레이션 때문에 임베딩 모델 로드 단계에서 멈췄다(두 번 재현). 러너는 네이티브 amd64라 이 문제가 없다
  - 저장소가 private이라 EC2가 pull하려면 인증이 필요하다. 서버에 미리 로그인해두는 대신 배포마다 로그인하도록 해, 인스턴스를 새로 만들어도 사전 준비 없이 동작한다
- 여기까지로 "빌드·배포 CI/CD 파이프라인" 과제 요건 충족

**⑤ API 성능 측정 (완료)**
- [x] `scripts/measure_api_latency.py`로 분기별 응답 시간 측정 (로컬 + EC2 양쪽)
- [x] **가설 확인**: Gemini 호출이 3회인 4-6점 분기가 2회인 분기보다 일관되게 느림 (약 4-6초 추가)
- [x] **병목이 서버 연산도 네트워크도 아님을 확인**: 기준선(측정 당시 헬스체크였던 `GET /`)이 로컬 2.4ms / EC2 42.5ms로 전체의 0.2% 미만. t3.small이 맥북보다 CPU가 약한데도 응답 시간은 느리지 않았다. 인스턴스 사양을 올려도 응답 시간은 줄지 않는다는 뜻
- [x] **순차 설계의 비용을 수치화**: Learning Tip → Followup 순차 구조가 출력 일관성을 얻는 대신 약 4-6초를 지불하고 있음을 확인. 기존에는 설계 의도만 있었고 대가는 미측정 상태였음
- [x] 메모리 사용량은 ③ 인스턴스 선정 과정에서 선행 측정 (유휴 757MB, 피크 1.154GB)
- 같은 엔드포인트인데 지연이 갈리는 이유: 0-3점(Judge → Fundamentals)과 7-10점(Judge → Advanced)은 Gemini 호출이 2회지만, 4-6점은 Judge → Learning Tip → Followup 3회다

**⑥ 유닉스 환경 프로세스·스레드·메모리 분석 (완료)**
- [x] `/proc`, `top -H`, `docker stats`로 프로세스/스레드/메모리 상태 관찰 (EC2, slim 이미지라 `ps` 없이 진행)
- [x] 단일 요청의 상태 전이 관찰: 평상시 S → 처리 중 D(I/O 대기)·R(파싱 연산) → 종료 후 S. 스레드 9→20 증가 후 유지(스레드 풀)
- [x] **동시 요청 부하 실측으로 가설 반증**: vCPU 2개가 5개 요청을 거의 동시 처리(15-23초), 메모리 폭증·OOM 없음(`OOMKilled: false`). I/O 바운드라 CPU가 놀면서 다수의 대기를 떠안을 수 있음을 확인 (`kb/async_sync.md`의 내용을 서버에서 증명)
- [x] ⑤의 결론 정밀화: 대기(S)가 대부분이나 사이사이 짧은 R(응답 파싱)·D(I/O)가 낀다. 시간 측정만으로는 안 보이던 것을 상태 관찰로 확인
- [x] 관찰 데이터를 분석 보고서로 정리 (과제 제출물): [과제 1. 유닉스 프로세스·스레드·메모리 분석](reports/01_unix_process_analysis.md)

**⑦ WireShark 통신 캡처 (완료)**
- [x] 클라이언트(로컬 맥북)-서버(EC2) 간 `POST /evaluate-answer` 요청을 13패킷으로 캡처
- [x] 요청 하나의 생애 관찰: TCP 3-way handshake → HTTP 요청 → 17초 침묵 → HTTP 200 → FIN
- [x] **17.19초의 네트워크 침묵 확인**: 패킷 5-6 사이 데이터 없음 = 서버의 Gemini 대기. ⑤(시간)·⑥(프로세스 S 상태)·⑦(패킷 부재) 세 각도가 "지연은 LLM 대기"로 수렴
- [x] **HTTP 평문 노출 시연**: Follow HTTP Stream으로 요청·응답 JSON이 그대로 읽힘을 확인. HTTPS 필요성의 실측 근거
- [x] TCP 재전송 관측: 신뢰성 메커니즘이 실제로 동작하는 것을 캡처로 확인
- [x] **클라이언트를 스마트폰으로 바꿔 2차 캡처**: 폰 → 노트북 로컬 서버(동일 Wi-Fi)로 서비스 전 과정을 캡처해, 원격(EC2)·근거리(Wi-Fi) 두 구성에서 같은 프로토콜 동작이 나타남을 확인. 파일 업로드의 TCP 세그먼트 분할, 요청별 독립 세션(포트 56256/56258/56265), Keep-Alive를 추가 관측
- [x] 캡처 데이터를 분석 보고서로 정리 (과제 제출물): [과제 2. WireShark HTTP 통신 캡처·분석](reports/02_wireshark_http_capture.md)

### Phase 9: 입력 형식 확장 (완료)
- [x] PDF 업로드 지원 (`.md`/`.txt`/`.pdf`), `pypdf`로 텍스트 추출
- [x] PDF 파싱을 `load_pdf_file`로 격리하고 `load_document`가 확장자로 분기하도록 설계. 나중에 pdfplumber 등으로 교체해도 이 함수 몸통만 수정하면 됨(호출부·후단 불변)
- [x] 텍스트가 없는 PDF(스캔 이미지 등)는 빈 인덱싱 대신 422로 거부
- [x] 확장자 분기 회귀 테스트 추가, 실제 서버에 한글 PDF 업로드 후 질문 생성까지 end-to-end 검증
  - 실사용 이력서는 대부분 PDF이므로 제품 가치가 높음

### Phase 10: 프론트엔드 (완료)
- [x] 순수 HTML/CSS/JS 단일 페이지(`static/`) 추가, FastAPI가 정적 서빙(CORS·빌드·별도 서버 없음)
- [x] 업로드 → 질문 생성 → 답변 평가 3단계 흐름을 화면으로 연결, 점수 구간별 코칭을 뱃지·색상으로 구분 렌더링
- [x] `GET /`를 데모 페이지로, 헬스체크는 `/health`로 분리(compose/CI/성능 측정 함께 갱신), Dockerfile에 `static/` COPY 추가
- [x] 로컬 uvicorn과 Docker 컨테이너 양쪽에서 서빙 확인, 브라우저로 전체 흐름(업로드/질문생성/평가/코칭 분기) end-to-end 검증

### Phase 11: 멀티턴 면접 루프 (완료)
그래프가 한 방향으로 흐르고 끝나던 구조에 사이클을 도입. "조건부 분기만 할 것이면 LCEL로도 가능하지 않은가"라는 반문에 답하는 것이 목적이었다.

- [x] `await_answer` 노드에서 `interrupt()`로 실행을 멈추고, `Command(resume=답변)`으로 재개하는 구조 구현
- [x] `followup`/`advanced` → `await_answer` → `retrieval` 사이클 배선 (질문이 바뀌었으므로 검색부터 다시)
- [x] 0-3점(`fundamentals`)은 다음 질문을 만들지 않으므로 루프에서 제외. 개념을 모르는 상태에서 같은 주제를 재질문하는 것은 코칭으로 부적절하다고 판단
- [x] 종료 조건 `MAX_TURNS = 3`. `decide_continue()`도 순수 함수라 LLM 없이 경계값 검증
- [x] `build_interview_agent_graph()`(단발성)를 그대로 두고 세션 그래프를 따로 추가. `/evaluate-answer`와 Calibration 스크립트의 동작 보존
- [x] `POST /interview/start`, `POST /interview/answer` 추가. `thread_id`로 세션을 구분하고, 종료된 세션은 409·없는 세션은 404로 구분 응답
- [x] **노드를 가짜로 대체한 루프 회귀 테스트 10개**: judge 호출 횟수로 사이클을 증명하는 방식이라 API 키 없이 CI에서 실행 가능
- [x] checkpoint 직렬화 허용 타입을 명시(`JsonPlusSerializer(allowed_msgpack_modules=[...])`). 기본값이 "전체 허용 + 경고"이고 향후 버전에서 차단 예정이라 미리 고정
- [x] 실제 Gemini로 검증: 한 세션에서 8점 → 9점 → 10점으로 이어지며 심화 질문이 점점 깊어지는 것, 다른 실행에서 세 경로(fundamentals/followup/advanced)가 모두 나오는 것 확인

**프론트엔드 대화형 개편 (완료)**
- [x] STEP 3을 단발 평가에서 **턴이 쌓이는 타임라인**으로 재설계. 각 턴에 질문·내 답변 말풍선과 점수 뱃지, 코칭이 함께 남는다
- [x] 지금 답해야 할 질문을 입력창 바로 위에 고정 표시. 코칭 블록 안에서는 꼬리질문·심화질문 본문을 빼서 **같은 질문이 두 군데 보이지 않도록** 정리(어디에 답해야 하는지 헷갈리는 문제 예방)
- [x] 세션 진행 중에는 질문 변경을 막고 안내 표시. 종료 시 입력창을 숨기고 종료 사유별 메시지 + 재시작 버튼 노출
- [x] 브라우저에서 end-to-end 검증: 3턴 완주(9→10→9점, 각 턴 질문이 사이클로 교체), 0-3점 경로가 루프 없이 종료, 재시작 후 상태 초기화, 라이트/다크 양쪽 색상, 레이아웃 겹침 없음까지 확인

---

## 고도화 로드맵 (2026-07-29 멘토링 반영)

부트캠프 멘토링에서 받은 조언을 Phase로 정리했다. 순서를 정한 기준은 **의존 관계**다.
페르소나(Phase 13)가 정해져야 어떤 기능이 필요한지 판단할 수 있지만, 채점 개선(Phase 12)은
이미 계획이 서 있고 **효과를 수치로 증명할 수 있는 유일한 항목**이라 앞에 두었다.

| Phase | 내용 | 기간 | 선행 조건 | 상태 |
|---|---|---|---|---|
| 12 | 채점 고도화 (루브릭·감점 근거·레벨 판정) | 2-3일 | 없음 | **완료** |
| 13 | 페르소나 정의와 제품 방향 | 반나절 | 없음 (문서 작업) | **완료** |
| 14 | HTTPS와 도메인 연결 | 1일 | 도메인 확보 | 예정 |
| 15 | 지식베이스 출처 재설계 | 3-5일 | 저작권 검토 | **완료** |
| 16 | 채용공고 매칭 | 1-2주 | Phase 13 | 예정 |
| 17 | 범위 밖 질문 처리와 평가셋 강화 | 4-6일 | Phase 15 | **완료** |

### Phase 12: 채점 고도화 (완료, 2026-07-31)
사용자가 "왜 이 점수인지" 납득하지 못한다는 지적에서 출발했다. 착수 시점에는 **채점 편차도 함께 줄어들 것**으로 봤으나, 그 기대는 측정으로 기각됐다.

- [x] **루브릭(점수대별 판정 기준)을 프롬프트에 명시**
  - 기존 프롬프트는 `technical_score (0~10): 답변이 기술적으로 정확한가`가 전부라 9점과 10점을 가르는 기준이 없었다
  - 실측 사례: 같은 주제 답변에서 "이유를 한 줄 덧붙였는지"만으로 4점과 7점이 갈렸다. 분기 경계를 넘나들어 실행 경로 자체가 바뀐다
- [x] **감점 근거 제시**: `Deduction`(reason, points) 목록을 반환. `points` 합이 `10 - technical_score`와 일치하는지 검증해 **17개 전부 일치(100%)** 확인
- [x] **레벨 판정**: `junior` / `middle` / `senior`. 지원자의 연차가 아니라 그 답변이 보여준 수준이다
- [x] **스키마 확장으로 구현**: `judge_node`가 이미 structured output을 쓰므로 필드만 넓혔다. Gemini 호출 횟수는 그대로다. `deductions`를 `technical_score`보다 앞에 배치해 "깎을 것을 먼저 세고 합을 빼는" 순서를 유도했다
- [x] **프론트엔드 반영**: 감점 내역을 강점·개선점보다 앞에 두어 점수 직후에 근거가 이어지게 배치
- [ ] **모범답안 제공**: 이번에 넣지 않았다. `[Reference]` 밖에서 생성되면 환각이므로 생성 범위 제약과 RAGAS 재측정을 전제로 별도 진행할 것

**결과**
- 루브릭이 정확도를 올린다는 가설은 **기각**됐다. 동일 세트로 유무를 비교했으나 차이가 변동 폭(약 5%p) 안에 들어왔고, 레벨별 평균 점수도 거의 같았다
- 사용자가 점수 근거를 알게 된다는 목표는 달성했다. 원래 지적받은 문제가 그것이었다
- **부수 성과로 측정 도구가 개선됐다.** Calibration Set을 17개에서 44개(주제 5개 → 13개)로 확대하고, 판정 기준을 점수 범위에서 **코칭 경로 일치**로 바꿨다. 기존 세트는 기대 범위가 분기 경계와 어긋나 있어, 점수는 맞았다고 나오면서 엉뚱한 코칭이 나가는 경우를 잡지 못했다
- 3회 반복으로 **변동 폭 약 5%p**를 확보했다. 이제 이보다 작은 차이는 노이즈로 판정한다

측정 과정과 시행착오는 [실험 로그](experiment_log.md#2026-07-31---채점-루브릭-도입과-측정-도구-재설계-phase-12) 참고.

### Phase 13: 페르소나 정의와 제품 방향 (완료)
멘토 조언: "이 프로젝트의 사용자를 유추해 페르소나를 정하라. 서비스를 판매한다고 생각하고 만들어라."

#### 대상 사용자: 국내 백엔드 직군 신입 취업 준비자

부트캠프 수료생이나 전공자처럼 **직무 경험이 없는 상태에서 기술 면접을 준비하는 사람**이다. 1-3년차 이직 준비자는 이번 범위에서 제외한다.

이 선택은 추측이 아니라 **이미 만들어진 것에서 역으로 확인된다.**

| 구현된 것 | 가리키는 사용자 |
|---|---|
| KB 18개가 JWT·Spring·FastAPI·PostgreSQL·Docker 중심 | 백엔드 직군 |
| 업로드 형식이 `.md`, `.txt`, `.pdf` | 이력서·포트폴리오·GitHub README를 가진 사람 |
| 0-3점에 **개념 설명** 경로를 따로 둠 | 개념을 모를 수 있는 단계 |
| KB가 기초에서 중간 난이도 (아키텍처 설계나 대규모 트래픽 주제 없음) | 실무 경험이 전제되지 않음 |

특히 세 번째가 결정적이다. 경력자를 주 대상으로 삼았다면 "개념 자체를 설명해주는 경로"를 만들 이유가 없었다.

#### 이 사용자가 겪는 문제

1. **아는 것과 말할 수 있는 것이 다르다.** 공부는 했는데 면접에서 설명하려니 막힌다
2. **피드백을 줄 사람이 없다.** 혼자 준비하면 내 답변이 몇 점짜리인지 알 수 없다
3. **어디까지 파고들어야 할지 모른다.** "JWT를 안다"가 어느 수준을 뜻하는지 기준이 없다

#### 이 서비스가 해결하는 것과 하지 않는 것

**해결한다**
- 2번: 답변에 점수·감점 근거·역량 수준을 매겨 되돌려준다. Judge를 그대로 믿지 않고 Calibration Set으로 채점 신뢰도를 검증해뒀다
- 3번: 심화 질문이 직전 답변을 전제로 깊어지므로, 어디까지 알아야 하는지가 대화로 드러난다

**해결하지 않는다**
- 1번은 부분적으로만 다룬다. 글로 쓰는 답변이라 **말하기 훈련은 아니다.** 음성 입력이 없는 한 이 격차는 남는다
- 이력서 첨삭, 자소서 작성은 범위 밖이다

#### 페르소나 기준으로 본 기존 기능

| 기능 | 판단 |
|---|---|
| 점수 구간별 3분기 | **유지.** 신입은 실력 편차가 커서 같은 사람도 주제마다 0점과 10점을 오간다 |
| 멀티턴 루프 (3턴) | **유지.** "한 번 답하고 끝"이 아니라 되물어야 실제 면접에 가깝다 |
| `senior` 레벨 판정 | **애매하다.** 신입이 대상인데 senior 판정이 나올 일이 드물다. 실제로 v1 세트 측정에서 `junior` 13건, `middle` 4건이었고 `senior`는 0건이었다 |
| PDF 업로드 | **유지.** 실사용 이력서는 대부분 PDF다 |

#### 이 결정이 이후에 미치는 영향

- **Phase 15 (KB 재설계)**: 난이도를 기초에서 중간 수준으로 유지한다. 대규모 트래픽·분산 시스템 같은 주제는 넣지 않는다. 신입 면접에서 안 나오는 데다, 근거 없이 답하게 만들면 오히려 해롭다
- **Phase 16 (채용공고 매칭)**: **신입 공고**를 기준으로 한다. 신입 공고는 요구사항이 "우대사항" 중심이라 매칭 로직이 경력 공고와 다르다
- 난이도 분기(이직 준비자 대응)는 이 범위를 먼저 검증한 뒤 확장 항목으로 둔다

### Phase 14: HTTPS와 도메인 연결
멘토 조언: "포트 번호가 보이지 않게 하고 인증서를 붙여라."

- [ ] 도메인 확보 후 EC2에 연결
- [ ] Nginx 등 리버스 프록시를 두고 80/443으로 받아 내부 8000으로 전달 (주소에서 포트가 사라짐)
- [ ] Let's Encrypt로 TLS 인증서 발급 및 자동 갱신
- [ ] 보안 그룹에서 8000 직접 노출을 닫고 80/443만 개방
- 배경: 과제 2(WireShark)에서 **요청·응답 JSON이 평문으로 노출되는 것을 직접 캡처**했다. 그때 향후 과제로 적어둔 항목을 여기서 해소한다. 적용 후 같은 방식으로 다시 캡처하면 암호문으로만 보이는 것을 비교 자료로 남길 수 있다

### Phase 15: 지식베이스 출처 재설계 (완료, 2026-08-06)
멘토 조언: "답변에 대한 지식베이스를 무엇을 기반으로 할 것인가. 전공 도서나 교재를 넣는 방법도 있다."

- [ ] **저작권 검토 선행** (필수): 전공 도서 PDF나 부트캠프 교재는 개인 학습용이면 몰라도, **공개 저장소와 배포 서버에 담으면 저작권 문제가 된다.** 이 프로젝트는 GitHub 공개 저장소이고 EC2에 배포돼 있다
- [ ] 대안 검토: **RFC 문서**(JWT는 RFC 7519, OAuth는 RFC 6749), 공식 문서(FastAPI·Spring·PostgreSQL), 또는 교재를 읽고 **직접 요약해 작성**
  - RFC 기반으로 가면 "지식베이스 출처가 표준 문서"라고 말할 수 있어 근거의 권위가 오히려 올라간다
- [x] KB 확장 (18개 → **29개, chunk 54개**). DB 심화 4개, 웹/네트워크 3개를 신규 작성하고 `http.md`를 메서드·상태코드·REST 설계·멱등성·Authorization 헤더로 분리했다
- [x] **난이도는 기초에서 중간 수준으로 유지** (Phase 13의 페르소나 결정). 대규모 트래픽·분산 시스템 등 신입 면접 범위 밖 주제는 넣지 않는다
- [x] **전체 재측정**: 평가셋을 20 → 30문항으로 늘리고 재실행했다. **임베딩 비교 결론이 뒤집혀 Gemini Embedding으로 교체했다** (30문항 기준 Gemini 100%/0.9702 vs ko-sroberta 86.7%/0.8931). 채점 정확도는 90.9%로 노이즈 범위 안이라 변화 없음. 자세한 내용은 [실험 로그](experiment_log.md#2026-08-06---kb-확장이-임베딩-선택을-뒤집었다-phase-15)
- 배경: 현재 Context Precision 1.0000, Faithfulness 0.9708이지만, KB 2개 시절에도 같은 이유로 만점이 나왔다가 "측정 조건 미충족"으로 판명된 전례가 있다. 18개(chunk 29개)에 `k=3`이면 여전히 변별력이 부족할 가능성이 있다
- **남은 과제**: 우려가 현실이 됐다. 임베딩 교체 후 Top-1 100%·Context Precision 1.0000으로 **평가셋이 다시 천장에 닿았다.** KB 문서를 보강해도 효과를 측정할 수 없으므로, 보강에 앞서 평가셋을 어렵게 만들어야 한다 (저빈도 전문용어, 인접 주제 구분, 정의형/비교형/적용형)

### Phase 16: 채용공고 매칭
멘토 조언: "채용공고와 이력서를 매칭시켜 부합한 점, 부족한 점, 더하면 좋을 점을 제안하라."

- [ ] 공고 내용을 입력받아 인덱싱 (이력서와 별도 컬렉션). **신입 공고 기준** (Phase 13의 페르소나 결정). 신입 공고는 요구사항이 우대사항 중심이라 경력 공고와 매칭 로직이 다르다
- [ ] 이력서와 공고를 각각 검색해 비교하는 노드 추가
- [ ] 결과를 세 갈래로 반환: 부합하는 점 / 부족한 점 / 보완하면 좋을 점
- [ ] 부족한 점을 면접 질문 생성에 반영 (기존 Chain A와 연결)
- **입력 방식은 URL이 아니라 텍스트 붙여넣기로 한다.** 사람인·잡코리아·원티드 등은 스크래핑을 기술적으로 차단하고 이용약관으로도 금지한다. 기능의 본질(공고와 이력서 매칭)은 그대로면서 구현이 단순해지고, 기존 `POST /documents` 구조를 재사용할 수 있다
- 제품 관점에서 가장 차별화되는 기능이다. "이력서 기반 면접 질문"에서 **"이 회사에 지원하려면 무엇이 부족한가"** 로 나아가는 지점이라, 멘토가 말한 "판매할 수 있는 서비스"에 가장 가깝다

### Phase 17: 범위 밖 질문 처리와 평가셋 강화 (완료, 2026-08-06)

**결과 요약**: 평가셋 30 → 65문항 5유형, 임계값 `0.311` (group 5-fold 교차 검증: 재현율 100%, 정밀도 93.8%, 범위 안 통과 93.3%). `out_of_scope` 분기를 구현해 근거가 없으면 점수를 만들지 않는다. 과정과 이날 잡은 버그 세 개는 [실험 로그](experiment_log.md#2026-08-06-계속---근거가-없으면-채점하지-않는다-phase-17) 참고.


Phase 15에서 드러난 두 가지 문제를 함께 다룬다. **평가셋이 다시 천장에 닿았고**(Top-1 100%, Context Precision 1.0000), **KB에 근거가 없어도 시스템이 항상 문서 3개를 돌려주고 그것으로 채점한다.**

측정으로 확인한 사실이다.

| 질문 | 1순위 거리 | 1순위 문서 |
|---|---|---|
| 멱등성이란 무엇인가요? | 0.231 | `http_idempotency.md` |
| N+1 문제가 무엇이고 왜 발생하나요? | 0.213 | `db_n_plus_one.md` |
| Kubernetes에서 Pod 오토스케일링은? | 0.402 | `docker.md` |
| Kafka 컨슈머 그룹 리밸런싱은? | 0.405 | `async_sync.md` |
| 좋아하는 음식이 무엇인가요? | 0.424 | `async_sync.md` |

시연에서 생성된 면접 질문에도 "Redis TTL 전략", "Session Clustering"처럼 KB가 다루지 않는 주제가 실제로 있었다. 가상의 위험이 아니다.

#### 범위 밖 정책 (확정)

**이것은 검색 실패가 아니라 제품 정책이다.** 근거가 없으면 틀린 문서로 채점하지 않는다.

- **근거 충분**: 현재처럼 `retrieval -> judge`
- **근거 부족**: `out_of_scope`로 분기
  - 기술 점수·완성도 점수·`level`·학습 팁·꼬리질문을 **생성하지 않는다**
  - "현재 고정 지식에 검증 가능한 근거가 없어 정확한 평가를 보류한다"고 안내한다
  - 해당 경험을 평가받고 싶다면 관련 문서를 업로드하도록 유도한다

세부 결정이다.

- **판정 기준**: 1순위 거리. 가장 가까운 문서조차 멀면 범위 밖으로 본다
- **턴 카운트**: 범위 밖 턴은 `MAX_TURNS`에 포함하지 않는다. 채점받지 못한 턴을 면접 턴으로 세지 않는다
- **세션 처리**: 사용자가 "계속하기 / 종료하기"를 고른다. 계속하면 2단계에서 생성된 질문 목록 중 아직 쓰지 않은 것으로 넘어간다
- **상한**: 범위 밖이 반복될 때 무한히 늘어나지 않도록 별도 상한을 둔다. 질문 목록이 소진되면 종료한다

#### 구현 시 함께 바뀌어야 하는 것

`EvaluationResult`는 모든 필드가 필수라 "점수를 만들지 않는다"가 현재 스키마로는 표현되지 않는다.

- `rag/schemas.py`: 평가 결과가 없는 상태를 표현할 방법이 필요하다
- `api/interviews.py`: `values["evaluation_result"]`와 `evaluation.model_dump()`가 평가 결과의 존재를 가정한다
- `static/app.js`: `scoreBadges(data.evaluation)`에 null 처리가 없다

#### 평가셋 강화

정책을 정한 뒤, 그 정책이 지켜지는지 잴 수 있는 평가셋을 만든다.

| 유형 | 예시 | 측정값 |
|---|---|---|
| 지원 범위 내: 정의·비교·적용 | 멱등성 정의 / PUT과 PATCH 차이 / 중복 결제 방지 | Top-1, Recall@3 |
| 인접 주제 혼동 | N+1 vs 인덱스 / 인증 vs 인가 / JWT 무효화 vs 세션 로그아웃 | Top-1 |
| 복수 근거 질문 | JWT와 세션의 확장성 차이 | Recall@3, `expected_sources` 복수 |
| 범위 밖 질문 | Kafka, Redis 내부, Kubernetes | 범위 밖 판정의 정밀도·재현율 |
| 실제 표현 변형 | 키워드 없는 서술형, 이력서 문맥 포함 질문 | 위 지표 전체 |

- **정확도를 목표로 삼지 않는다.** "Gemini가 몇 % 나오게" 맞추면 평가셋이 특정 모델에 과적합된다. 좋은 평가셋의 기준은 모델을 곤란하게 만드는 것이 아니라 **실제 실패 유형을 안정적으로 잡는 것**이다. 포화는 사후에 진단할 신호이지 조정할 목표가 아니다
- **`key_evidence` 전수 검사**: 문항마다 정답 문서 안에 실제로 있는 짧은 근거 문구를 넣고 스크립트로 검사한다. Phase 15에서 정답 키가 `rest_api_design.md`로 잘못 매핑된 사고를 **API 비용 없이** 잡을 수 있다
- **임계값은 group 5-fold 교차 검증으로 정한다.** 같은 주제를 표현만 바꾼 문항이 train/test에 걸쳐 들어가면 임계값이 실제보다 좋아 보인다. 주제·템플릿 단위로 묶어 나눈다
- **거리 임계값의 불확실성은 LLM 채점의 변동과 다르다.** Phase 12에서 잰 변동 폭 5%p는 같은 입력에 LLM이 다르게 답해서 생긴 값이다. 거리 판정은 결정적이라 재실행 변동이 0이고, 남는 것은 표본오차뿐이다(정확도 0.9 근처에서 n=30이면 약 5.5%p, n=100이면 약 3.0%p). 둘을 섞어 판단하지 않는다

#### 판정 메커니즘 - 거리 기반으로 먼저 간다

| | 거리 임계값 | LLM 관련성 판정 |
|---|---|---|
| 비용 | 0 | 호출 1회 추가 |
| 지연 | 0 | 수 초 |
| 임베딩 교체 시 | 재보정 필요 | 영향 없음 |
| 근거 설명 | 불가 | 가능 |

첫 구현은 거리 기반으로 한다. 재보정이 필요하다는 단점은 있으나, **그 재보정이 버전 관리 가능한 명시적 절차**라는 장점도 된다. 평가셋을 먼저 고정해두면 이후에 두 방식을 같은 기준으로 공정하게 비교할 수 있다.

---

### Future Work / 선택
- [ ] **세션 영속화**: 현재 `MemorySaver`라 재시작 시 세션이 소실된다. `SqliteSaver`로 바꾸면 volume에 남길 수 있다(이미 `chroma_db`를 volume에 두고 있어 같은 방식으로 처리 가능).
- [ ] **종료 조건에 "개선 없음" 추가**: history에 턴별 점수가 쌓이므로 구현 자체는 간단하나, 몇 점 차이를 "개선 없음"으로 볼지 정할 근거가 아직 없어 보류.
- [ ] **Agent v3: Knowledge Search 노드**
  - Judge가 진단한 약점(`improvements`)을 검색어로 KB를 재검색해 Learning Tip에 더 정확한 근거를 제공하는 구상. v2 설계 시 "이미 검색했는데 왜 또 검색하는가"라는 반문 때문에 보류했으나, Learning Tip 도입 후 "Learning Tip 품질 개선"이라는 명분이 확보되어 v3 확장 여지로 남겨둠.
  - 다만 현재 KB 규모에서는 개선 여지가 크지 않을 수 있고, 오히려 context가 넓어져 Faithfulness가 낮아질 위험도 있다(기존에 관찰된 문제는 근거 부족이 아니라 과잉 인용이었음). Phase 15 이후 20문항 평가셋으로 전후 비교해 검증할 것.
- [ ] **Elastic IP 적용**: 인스턴스를 중지·재시작할 때마다 퍼블릭 IP가 바뀌어 GitHub Secret(`EC2_HOST`)을 매번 갱신해야 한다. 고정 IP를 붙이면 해소되지만 중지 상태에서 소액 과금된다.
