# 실험 로그

## 2026-06-23 - Semantic Retrieval 검증

### 가설
임베딩 기반 검색이 키워드 일치가 아니라 의미로 작동하는지 확인.

### 방법
`scripts/test_semantic_retrieval.py` - "JWT", "인증" 단어를 전혀 포함하지 않은 쿼리("로그인한 사용자를 어떻게 식별하나요?")로 인증 관련 chunk와 무관한(pytest/CI) chunk를 구분할 수 있는지 테스트.

### 결과
- 무관한 chunk(pytest/CI)는 정확히 최하위로 밀려남 → 최소한의 의미 구분은 작동.
- 다만 여러 주제가 섞인 긴 chunk(README 전체)가, 주제 하나로 깨끗한 짧은 chunk(doc_auth)보다 더 높은 유사도를 받는 경우가 있었음.

### 결론
**Chunk는 주제 하나당 짧고 포커스 있게 유지해야 한다.** 혼합 주제 chunk는 의도와 다르게 부풀려진 유사도 점수를 받을 수 있음.

### Action Item
- Interview KB(`jwt.md`, `fastapi.md` 등)는 파일당 주제 하나로 작성
- Collection 1(User Docs)은 실사용 시 이력서/포트폴리오가 길어지면 자연히 여러 chunk로 쪼개지므로 별도 조치 불필요

---

## 2026-06-24 - Chain A Faithfulness 이슈 발견

### 가설
Retriever가 적절한 문서를 검색해오면, Chain A가 생성하는 질문도 항상 그 문서 내용에 근거할 것이다.

### 방법
`POST /generate-question`으로 실제 README 기반 면접 질문 5개 생성 후, 각 질문이 원문에 근거하는지 확인.

### 결과
5개 중 4개는 원문(FastAPI, JWT, bcrypt, PostgreSQL, RAG 청킹)에 정확히 근거했으나, 1개는 latency/SSE·WebSocket/Celery 관련 질문으로 원문에 전혀 없는 내용이었음.

### 결론
**Retriever 성공 ≠ Faithfulness 보장.** 검색이 정확해도 생성 모델이 컨텍스트 밖 내용을 추가할 수 있음을 직접 확인.

### Action Item
- Day 4 RAGAS 평가에 Faithfulness를 반드시 포함
- Chain B Judge 설계 시에도 KB 범위를 벗어난 응답을 생성하지 않는지 동일한 관점으로 점검

---

## 2026-07-06 - Judge Calibration 자동화 및 completeness 프롬프트 개선

### 가설
Judge의 채점이 Calibration Set(bad/average/good 3단계 + 비대칭 케이스 2개, 총 17개)의 기대 범위 안에 들어오는지 자동으로 확인한다.

### 방법
`scripts/run_calibration.py`로 17개 케이스를 Chain B에 전부 돌리고, 각 케이스의 `technical_score`/`completeness_score`가 `expected` 범위 안에 들어오는지 자동 비교.

### 1차 실행 결과 (프롬프트 수정 전)
9/17 통과 (52.9%). 실패 8건 중 7건이 `completeness_score`만 실패, 그것도 대부분 기대보다 낮게 나옴.

### 원인 분석
실패한 Case 2, 3, 8의 Judge `improvements` 피드백을 직접 확인한 결과, 매번 "Access Token/Refresh Token", "저장 위치 보안", "토큰 무효화" 3종 세트가 반복 등장. Judge가 질문 범위가 아니라 `kb/jwt.md` 문서 전체를 커버리지 체크리스트처럼 사용해 completeness를 채점하고 있음을 확인.

### 프롬프트 개선
`rag/prompts.py`의 `EVALUATION_PROMPT`에 completeness 기준을 다음과 같이 명시:
> [Question]에서 직접 묻고 있는 내용에 한정하여 평가하며, [Reference]에는 있지만 질문이 요구하지 않은 배경지식을 언급하지 않았다는 이유로 감점하지 않는다.

### 2차 실행 결과 (프롬프트 수정 후)
10/17 통과 (58.8%). **bad(5/5), good(5/5) 카테고리는 전부 통과** - 특히 good 케이스의 completeness가 기존 5~6점대에서 9~10점대로 개선됨.

실패는 average(5/5 전부 실패) + 비대칭 케이스(2/2 실패)에 집중됨.

### 추가 발견 - Calibration Set 자체의 설계 결함

실패 원인을 Judge 성향 문제로 단정하기 전에, 실패 케이스의 답변 원문을 다시 확인함. 그 결과 **Case 5(average)와 Case 16(technically_correct_but_brief)의 답변 텍스트가 완전히 동일**함이 드러남:

```
"Access Token은 인증에 사용되고 Refresh Token은 Access Token을 재발급할 때 사용됩니다."
```

- Case 5 기대값: technical [4,7], completeness [4,7]
- Case 16 기대값: technical [7,10], completeness [0,4]

동일한 답변에 서로 다른 두 기대치가 부여되어 있었음. 실제 Judge 점수(Case 5: technical=10/completeness=6, Case 16: technical=9/completeness=5)는 서로 거의 일치해 Judge는 일관되게 채점하고 있었고, **Calibration Set 쪽의 설계 결함**으로 확인됨.

같은 관점에서 Case 2("JWT는 토큰입니다. 사용자 인증에 씁니다"), Case 14("DB 연결 같은 거 할 때 씁니다")도 재검토한 결과, 이들 모두 "average"가 아니라 구조적으로 Case 16과 같은 "짧지만 틀리지 않은 답변" 유형임을 확인. 즉 현재 Calibration Set의 "average" 카테고리는 전부 "부분적으로 틀리거나 애매한 답변"이 아니라 "정확하지만 짧은 답변"으로 잘못 설계되어 있었음.

Case 17(verbose_but_technically_wrong)의 기대값(completeness [5,10])도 재검토 필요 - "틀린 내용을 길게 설명한 답변"에 높은 completeness를 기대한 것 자체가 비합리적이라는 지적. Judge가 completeness=2로 낮게 준 것이 오히려 합리적인 채점으로 판단됨.

### 결론
1. **completeness 프롬프트 개선은 성공적으로 검증됨** (bad/good 전 항목 통과, README/포트폴리오에 근거로 활용 가능)
2. **Calibration Set을 Judge 성향에 맞춰 조정하는 것은 지양** - Judge를 맹신하지 않기 위해 만든 안전장치이므로, 먼저 실패 케이스의 답변 원문을 재검토해 Calibration Set 자체의 설계 결함부터 확인하는 절차를 따름
3. "average" 카테고리를 진짜 부분 정답(일부만 맞거나 애매한 내용)으로 재설계 필요 - 상세 원인은 다음 로그(2026-07-07)에서 다룸
### Action Item
- Calibration Set의 average 5개 항목을 "짧지만 정확함"이 아니라 "일부만 맞거나 부정확한 설명"으로 교체
- Case 17의 completeness 기대값을 하향 조정 (예: [0,4])
- 재설계 후 17개(또는 조정된 문항 수)로 재실행하여 재검증

---

## 2026-07-07 (계속) - Calibration Set 재설계 및 최종 검증

### 배경
1차 실행(52.9%) → completeness 프롬프트 개선 후 2차 실행(58.8%)까지 진행한 결과, 실패가 average 카테고리 5개 전부와 비대칭 케이스 2개에 집중됨. Judge 성향에 맞춰 기대치를 조정하기 전에, 실패 케이스의 답변 원문을 먼저 재검토함.

### 결정적 발견 - Calibration Set 자체의 설계 결함
Case 5(average)와 Case 16(technically_correct_but_brief)의 답변 텍스트가 완전히 동일함을 발견:
> "Access Token은 인증에 사용되고 Refresh Token은 Access Token을 재발급할 때 사용됩니다."

동일 텍스트에 서로 다른 기대치(average: [4,7]/[4,7] vs technically_correct_but_brief: [7,10]/[0,4])가 부여되어 있었음. 실제 Judge 점수는 두 케이스에서 거의 일치해(technical 9~10, completeness 5~6) Judge는 일관되게 채점하고 있었고, 문제는 Calibration Set 설계 쪽에 있었음이 확인됨.

같은 관점에서 재검토한 결과, 기존 average 5개 전부가 "일부만 맞거나 애매한 답변"이 아니라 "짧지만 틀리지 않은 답변"으로 잘못 설계되어 있었음이 드러남. → **Judge 문제가 아니라 Calibration Set 설계 문제로 원인을 재분류.**

### 재설계
- average 5개(Case 2, 5, 8, 11, 14)를 "일부는 맞고 일부는 명백히 틀린" 답변으로 전면 교체 (예: "Refresh Token은 비밀번호 대신 쓰는 토큰" 등 실제로 흔한 오개념 반영)
- Case 17의 completeness 기대값을 [5,10] → [0,4]로 수정 (틀린 내용을 길게 설명했다고 완성도가 높다고 볼 수 없다는 논리)

### 반복 실행 결과
| 실행 | 정확도 | 비고 |
|---|---|---|
| 1차 | 9/17 (52.9%) | 프롬프트 수정 전 |
| 2차 | 10/17 (58.8%) | completeness 프롬프트 개선 후, bad/good 전항목 통과 |
| 3차 | 13/17 (76.5%) | average 재설계 후, Case 5/16 중복 발견 |
| 4차 | 15/17 (88.2%) | Case 5 재작성 후, Case 7·16 경계값 조정 |
| 5차 | 16/17 (94.1%) | Case 17만 경계선 변동성으로 잔존 |

**프롬프트 개선과 Calibration Set 재설계를 반복 적용하면서 Judge Calibration 정확도를 52.9%에서 94.1%까지 향상시켰다.**

### 마지막 실패 케이스에 대한 판단
Case 17의 technical_score가 세 번의 반복 실행에서 3, 4, 3으로 나타남 - 기대 범위 [0,3]을 1점 초과하는 경우가 간헐적으로 발생하나, 이는 명백한 오분류가 아니라 LLM 응답의 자연스러운 경계선 변동으로 판단. 범위를 추가로 넓혀 100%를 맞추는 것은 지양함 - 지나치게 넓은 허용 범위는 Calibration Set의 변별력을 떨어뜨리므로, 94.1%(16/17)를 최종 결과로 채택.

### 결론
1. Judge의 일관성을 검증하는 과정에서, Judge보다 Calibration Set 자체의 기대값 정의가 문제였음을 확인함
2. completeness 프롬프트 개선(질문 범위 한정)과 Calibration Set 재설계(average를 진짜 부분 오류로 정의)라는 두 가지 독립적 개선이 합쳐져 52.9% → 94.1%로 향상
3. 완벽한 100%를 추구하기보다, 경계선의 자연스러운 변동과 실제 오분류를 구분해 적절한 시점에 멈추는 것도 중요한 판단으로 기록

### 활용
최종 Calibration Set(v2)은 일회성 실험 자산이 아니라, LangGraph 마이그레이션 이후에도 동일한 Judge 로직이 유지되는지 확인하는 회귀 테스트(regression test)로 재사용한다.

### Action Item
- Calibration Set v2(17개, average 재설계 반영)를 최종본으로 확정
- LangGraph 마이그레이션 시, 이 Calibration Set을 그대로 재사용해 "그래프로 옮긴 후에도 Judge 판단 로직이 그대로인지" 30초 내 재확인하는 안전망으로 활용

---

## 2026-07-08 - Agent 조건부 분기 경계값(threshold=5) 검증

### 가설
`decide_followup()`의 분기 조건(`technical_score < 5`)이 실제로 경계값에서도 정확히 동작하는지 확인한다. 기존에는 0점(꼬리질문 생성)과 10점(생성 안 함) 두 극단만 확인했고, 경계값(5점) 자체는 코드 리딩으로만 확인한 상태였다.

### 방법
`technical_score = 5`가 정확히 나오는 답변을 반복 조정하며 탐색. 답변에 포함된 오류의 종류와 강도를 하나씩 바꿔가며 점수 변화를 관찰:

| 시도 | 답변 특징 | technical_score |
|---|---|---|
| 1 | "인증 토큰"만 언급, 오류 없음 | 8~10 |
| 2 | 핵심 오류(stateless 부정) 포함 | 2 |
| 3 | 경미한 오류("자동 갱신")만 포함 | 4 |
| 4 | 경미한 오류 + 검증 메커니즘 설명 추가 | 4 |
| 5 | 경미한 오류 + 구조 3요소(Header/Payload/Signature) 모두 언급 | 6 |
| 6 | 경미한 오류 + 구조 1요소(Payload)만 언급 | **5** |

### 결과
시도 6의 답변("JWT는 Payload에 사용자 정보를 담은 토큰으로, 서버가 이 토큰을 검증해서 사용자를 인증합니다. 다만 토큰이 만료되면 자동으로 갱신됩니다.")에서 technical_score=5, followup_question=None 확인. PASS.

### 결론
분기 로직 3개 지점(0점→생성, 5점→미생성, 10점→미생성) 모두 실행 결과로 검증 완료. `technical_score < 5`라는 코드상 조건과 실제 동작이 일치함을 확인. 이 과정에서 Judge가 "오류의 강도"(핵심 개념을 부정하는 오류 vs 지엽적인 오류)와 "정답 커버리지"(구조 요소를 몇 개 언급했는가)를 함께 고려해 점수를 매긴다는 것도 부수적으로 관찰됨 - Day 4의 Calibration 설계 원칙(부분 오류 답변 설계 시 오류의 강도를 조절해야 한다)과 일치하는 패턴.

### Action Item
- README에 "technical_score가 낮으면"이 아니라 "technical_score가 5 미만이면"으로 정확한 임계값 명시
- 4점/6점 등 인접 값까지 전수 테스트는 하지 않음 - 양 극단과 경계값 확인으로 분기 로직 검증 목적은 충분히 달성했다고 판단

---

## 2026-07-08 (계속) - Agent v2: Learning Tip 노드 추가 (순차 설계)

### 배경
8주차 과제 요구사항(LangGraph 기반 Agent로 확장)을 더 발전시키기 위해, 단순 조건부 분기(Followup만 생성) 위에 학습 추천 기능을 추가하기로 함. GPT와 두 가지 확장 방향(Knowledge Search 재검색 vs Learning Tip)을 비교 검토.

### 설계 결정 - Knowledge Search 대신 Learning Tip 채택
Knowledge Search(Judge 이후 KB를 한 번 더 검색)는 "이미 Retrieval Node에서 검색했는데 왜 또 검색하는가"라는 자연스러운 반박에 미리 답을 마련해야 하는 위치였음. 반면 Learning Tip은 Judge(평가)와 역할이 명확히 분리되고("평가" vs "코칭"), "AI Interview Coach"라는 프로젝트 이름과 기능이 직접 맞아떨어져 설계 근거가 더 명확함. Knowledge Search는 v3 이후(Learning Tip을 보강하는 목적으로) 확장 여지로 남겨둠.

### 검증
- Bad 답변(technical_score=0): `learning_tip.topic`("Access/Refresh 토큰의 역할 분리")과 `followup_question`("이 두 토큰의 역할과 만료 시간은...")이 동일 주제를 겨냥함을 확인 - topic 공유가 실제로 작동함
- Good 답변(technical_score=10): `learning_tip`, `followup_question` 모두 `None` - "점수가 좋은데 학습 팁을 준다"는 모순 없이 정확히 스킵
- `/evaluate-answer` API 레벨에서도 동일하게 확인

### 결론
Agent의 확장 방향을 "더 복잡한 도구를 붙이는 것"이 아니라 "프로젝트 목적에 맞는 새 역할을 추가하고, 기존 노드와의 관계를 순차 흐름으로 명확히 하는 것"으로 설계함. 병렬보다 순차를 택한 이유도 "빠르게 만드는 것"보다 "두 출력이 서로 모순되지 않게 하는 것"을 우선한 결과.

### Action Item
- v3 확장 시 Learning Tip 앞에 Knowledge Search(KB 재검색)를 추가해 "Learning Tip이 더 정확한 근거로 topic을 정하도록" 개선 가능 - 이 시점에는 "왜 두 번째 검색이 필요한가"에 대한 답이 자연스럽게 "Learning Tip 품질 개선을 위해"로 정리되어, v2 시점에 우려했던 중복 검색 문제가 해소됨

---

## 2026-07-13 (계속) - RAGAS Faithfulness 적용

### 배경
Day 2에서 정성적으로 발견했던 "Retriever 성공 ≠ Faithfulness 보장" 문제를 RAGAS로 정량화하기 위해 라이브러리를 도입.

### 환경 이슈 및 해결
- `ragas` 최신 버전(0.4.x)이 `langchain_community.chat_models.vertexai` 경로(이미 `langchain-google-vertexai`로 이전됨)를 참조해 import 자체가 실패 - 알려진 버그. `ragas<0.4`로 다운그레이드했으나 동일 에러 재현.
- 근본 원인은 `ragas`가 아니라 `langchain-community`가 최신(0.4.2)이었던 것 - `ragas==0.3.9`가 기대하는 `langchain-community<0.4`로 함께 낮춰서 해결.
- Gemini/`ko-sroberta-multitask`를 RAGAS의 judge·embedding으로 재사용: `LangchainLLMWrapper(ChatGoogleGenerativeAI)`, `LangchainEmbeddingsWrapper(get_embeddings())` - 별도 OpenAI 키 불필요.
- `context_precision`은 `reference` 컬럼을 요구해 이번 라운드에서는 보류, `faithfulness`만 우선 적용.

### 설계 오류 발견 및 수정 - Chain A가 아니라 Chain B에 적용해야 했음
최초 시도는 Chain A(질문 생성)에 Faithfulness를 적용하려 했으나, `answer` 자리에 "생성된 면접 질문"을 넣는 것은 지표의 전제(주장이 context에 근거하는가)와 맞지 않음을 지적받음. 면접 질문은 "주장"이 아니라 "질의"라 Faithfulness가 측정하려는 대상이 아니었음.

Chain B(질문 + 사용자 답변 + context)는 이미 완전한 QA 형태라 Faithfulness 적용이 자연스러움. **"사용자 답변이 KB에 근거하는가"**를 측정하는 것으로 목적을 재정의.

또한 최초 코드는 `build_interview_agent_graph()`(Retrieval→Judge→Learning Tip→Followup 전체)를 실행해놓고 `context`만 사용해, Faithfulness 계산에 불필요한 Gemini 호출(Judge, Learning Tip, Followup)이 발생하고 있었음. `build_retrieval_only_graph()`로 교체해 필요한 호출만 남김.

### 검증 순서 (Day 1~4와 동일 패턴 적용)
1. 단일 케이스(good)로 정상 동작 확인 → faithfulness = 1.0000
2. bad/average/good 3개 비교 → 0.0000 / 0.5000 / 1.0000, 기대한 단조 증가 패턴 확인
3. `eval_result` 반환 타입 확인(`EvaluationResult`, `["faithfulness"]`는 `list`) - repr이 스칼라처럼 보여 인덱싱 방식을 사전에 명확히 확인
4. Calibration Set 필드명(`answer_level`) 실제 존재 여부 확인
5. `LIMIT=3`으로 자동화 스크립트(`run_ragas.py`) 먼저 시험 실행 → 정상
6. `LIMIT=None`으로 17개 전체 실행

### 17개 전체 실행 결과

| 카테고리 | 평균 Faithfulness | n |
|---|---|---|
| bad | 0.1333 | 5 |
| average | 0.1667 | 5 |
| good | 1.0000 | 5 |
| technically_correct_but_brief | 1.0000 | 1 |
| verbose_but_technically_wrong | 0.0000 | 1 |

전체 평균: 0.4412

### 발견 1 - good / verbose_but_technically_wrong에서 방향이 일치함
`verbose_but_technically_wrong`(틀린 내용을 길게 설명한 답변)의 Faithfulness가 0.0000으로 나옴. Judge Calibration에서 이 답변의 completeness_score 기대값을 낮게(≤4) 잡았던 판단과 같은 방향의 결과. 다만 Judge(기술적 정확성·완성도를 봄)와 Faithfulness(주장이 context에 근거하는가를 봄)는 서로 다른 기준으로 평가하는 독립적인 지표이므로, "서로를 검증했다"기보다는 **서로 다른 기준에서도 일관된 방향의 결과를 보였다**는 정도로 해석하는 것이 정확함.

### 발견 2 - bad와 average의 평균이 예상보다 가까움 (0.1333 vs 0.1667)
3개 축소 테스트에서는 bad=0.0, average=0.5로 뚜렷이 구분됐으나, 17개 전체에서는 두 카테고리 평균이 근접함.

개별 점수를 보면:
- bad 5개: [0.0, 0.6667, 0.0, 0.0, 0.0] - Case 4("둘 다 토큰이라 비슷합니다")만 0.6667로 이례적으로 높음
- average 5개: [0.5, 0.0, 0.0, 0.3333, 0.0] - 3/5가 0.0으로, 카테고리 전체가 예상보다 낮음

즉 두 평균이 가까워진 원인은 **Case 4의 이례적 상승과 average 카테고리 자체의 전반적인 낮음이 함께 작용한 결과**로 판단됨. Case 4 하나만으로 설명하기엔 average 카테고리 자체도 이미 낮은 값들로 구성되어 있어, 원인을 단일 요인으로 단정하지 않음.

Faithfulness는 답변을 개별 주장(claim) 단위로 쪼개 각각의 근거 여부를 판정하는 방식이라, 짧고 얕은 주장이라도 완전히 틀리지는 않으면 점수가 올라갈 수 있다는 가설은 유효하나, 아직 claim 단위 분석은 하지 않아 확정적이지 않음. 결론적으로 **Faithfulness("주장이 근거 있는가")와 Judge의 technical_score("기술적 정확성과 완성도")는 서로 다른 것을 측정하는 지표**이며, 두 지표가 항상 같은 순서로 카테고리를 구분해줄 것이라는 가정은 성립하지 않음을 확인.

### 결론
1. RAGAS 적용 대상은 Chain A가 아니라 Chain B로 재설정하는 것이 지표 의미상 정확함
2. Faithfulness와 Judge Calibration은 서로 다른 기준에서도 일부 일관된 결과를 보였으나(발견 1), 항상 같은 판단을 내리는 것은 아님(발견 2) - 두 지표를 같은 목적으로 혼용하지 않도록 유의
3. RAGAS도 Judge Calibration과 동일하게 "프로토타입(3개) → 자동화(17개)"의 발전 과정을 거침

### Action Item
- `context_precision`은 `reference` 데이터 설계를 별도로 진행한 뒤 추가 적용
- README/Project Outcomes에 "RAGAS Faithfulness 평균 0.4412" 정량 결과 반영
- Case 4(bad, faithfulness=0.6667)를 claim 단위로 분석해 어떤 주장이 "근거 있음"으로 판정됐는지 확인
- Faithfulness 카테고리별 결과가 재현 가능한지(변동성 여부) 필요시 재실행으로 확인

---

## 2026-07-13 (계속) - RAGAS Context Precision 적용

### 배경
Faithfulness에 이어 명세서에 계획된 두 번째 지표인 Context Precision을 적용. `reference` 컬럼이 필요해 보류했던 부분을, Calibration Set의 "good" 답변(질문당 1개, 5개)을 reference로 재사용하는 방식으로 해결 - 새로운 데이터를 만들지 않고 기존 자산을 그대로 활용.

### 검증 순서
1. 단일 질문("JWT란 무엇인가?")으로 정상 동작 확인 → 1.0000
2. Calibration Set에서 질문 5개(JWT 정의, Access/Refresh Token, JWT 저장 위치, FastAPI 비동기, FastAPI DI) 각각의 good 답변을 reference로 삼아 `run_context_precision.py`로 자동화

### 결과
5개 질문 전체 context_precision = 1.0000 (전체 평균 1.0000)

### 결과 해석
Interview KB(Collection 2)가 현재 `jwt.md`, `fastapi.md` 2개 문서뿐이라 chunk 수가 매우 적음(Day 1에서 이미 확인된 사실 - k=3 요청 시 사실상 KB 전체가 반환됨). 이 조건에서는 무관한 chunk가 상위로 올라올 가능성 자체가 거의 없어, Context Precision이 "Retriever가 진짜로 관련도를 잘 구분하는가"를 변별하기 어려운 상태.

질문 표본을 5개에서 늘리는 것으로는 이 문제가 해결되지 않음 - 변별력 부족의 원인은 질문 개수가 아니라 KB 문서 수 자체에 있음. 선택할 수 있는 문서가 2개뿐이면 질문을 아무리 늘려도 오답 후보가 늘지 않음.

**이번 실험의 실제 목적은 Retriever 성능을 입증하는 것이 아니라, Context Precision 평가 파이프라인을 구축하고 현재 적용 조건의 한계를 확인하는 것이었다.**

### 결론
1. Context Precision 자동화 파이프라인(`run_context_precision.py`) 자체는 정상 작동 확인
2. 현재 KB 규모에서 나온 만점은 "완벽한 검색"이 아니라 "측정 조건 미충족"으로 판단 - 성급한 긍정적 결론을 피함
3. KB 확장은 Retrieval·Faithfulness·Learning Tip·Followup·Agent 전반에 영향을 주는 큰 변경이므로, "한 번에 하나만 바꾼다"는 원칙에 따라 이번 실험 범위에서 분리하고 별도 Future Work로 남김

### Action Item (Future Work로 분리)
- KB를 20~30개 문서로 확장한 뒤 Context Precision 재측정 - 다음 우선순위(Embedding 비교, README 정리, uv 전환, GitHub 정리)를 마친 뒤 진행
- KB 확장 전까지는 README/Project Outcomes에 Context Precision 수치를 "파이프라인 구축 완료, 현재 KB 규모의 한계로 조건부 결과"로 표기

---

## 2026-07-13 (계속) - Embedding 비교 실험 (ko-sroberta-multitask vs Gemini Embedding)

### 배경
명세서에 계획된 임베딩 비교 실험. `ko-sroberta-multitask`와 Gemini Embedding(`gemini-embedding-001`)으로 동일한 KB를 각각 인덱싱한 뒤, Calibration Set의 good 답변 5개를 기준으로 Faithfulness/Context Precision을 나란히 측정.

### 방법
- `rag/embeddings.py`에 `get_gemini_embeddings()` 추가, `rag/vectorstore.py`에 별도 컬렉션(`interview_kb_gemini_embedding`) 추가 - 기존 `ko-sroberta` 컬렉션은 그대로 두고 완전히 독립적으로 비교
- 동일 KB(`jwt.md`, `fastapi.md`)를 두 임베딩으로 각각 인덱싱
- `scripts/compare_embeddings.py`로 질문 5개 × 임베딩 2개 = 10회 RAGAS 평가 자동화

### 환경 이슈
`GoogleGenerativeAIEmbeddings` 초기화 시 API 키 인식 실패 - `rag/embeddings.py`가 `rag.config`(`.env` 로딩)를 import하지 않고 있어 `GEMINI_API_KEY`가 스크립트 실행 시점에 환경변수로 존재하지 않았음. `google_api_key` 파라미터에 `rag.config.GEMINI_API_KEY`를 명시적으로 전달해 해결.

### 결과
두 임베딩 모두 5개 질문 전부 faithfulness=1.0000, context_precision=1.0000 - 완전히 동일.

### 결과 해석 - 이번에도 KB 규모가 측정을 무의미하게 만듦...........
Context Precision 단독 실험(직전 로그)에서 이미 확인했던 것과 동일한 구조적 한계가 재현됨: KB가 2개 문서, chunk 4개뿐이라 `k=3` 검색 시 사실상 KB 전체가 반환됨. 이 조건에서는 어떤 임베딩 모델을 쓰든 관련 chunk가 상위로 나올 수밖에 없어, 임베딩 간 차이가 드러날 여지 자체가 없음.

즉 이번 결과는 "두 임베딩이 동등한 성능을 보였다"가 아니라 **"현재 KB 규모에서는 임베딩 선택이 결과에 영향을 줄 수 없는 조건"**이라는 뜻. Context Precision 단독 실험과 Embedding 비교 실험, 서로 다른 두 실험에서 같은 구조적 제약이 반복 확인됨.

### 결론
1. KB 규모 확장 없이는 Retrieval 관련 지표(Context Precision, Embedding 비교)로 의미 있는 판단을 내릴 수 없다는 것이 두 차례에 걸쳐 재현됨 - 우연이 아니라 구조적 제약으로 판단
2. 이번 실험은 "두 임베딩 중 어느 쪽이 더 나은가"에 답을 주지 못했다 - 결과가 동일했던 것은 임베딩 성능이 같아서가 아니라 측정 조건 자체가 변별력을 갖지 못했기 때문. 따라서 임베딩 선택을 이번 결과로 정당화할 수 없으며, 이 질문은 KB 확장 후 재실험 전까지 열린 상태로 남긴다
3. KB 확장은 이제 Context Precision 재측정뿐 아니라 Embedding 비교 재실행의 전제 조건이기도 함 - 두 Future Work가 동일한 선행 작업에 의존

### Action Item
- KB 20~30개 확장 후 Context Precision과 Embedding 비교를 함께 재실행 (동일 KB 확장 작업으로 두 실험을 한 번에 재검증 가능)
- README/Project Outcomes에는 "임베딩 비교 파이프라인 구축 완료, 현재 KB 규모의 한계로 유의미한 비교는 KB 확장 이후로 보류"로 기록

---

## 2026-07-14 (계속) - KB 확장 후 Context Precision / Embedding 비교 재실행

### 배경
직전 실험(Context Precision 단독, Embedding 비교)에서 KB가 2개 문서(jwt.md, fastapi.md)뿐이라 두 지표 모두 변별력을 갖지 못했음을 확인. GPT와 함께 "관련 있지만 핵심은 아닌" 문서를 의도적으로 섞어 KB를 재설계.

### KB 확장
기존 2개에 8개 문서(spring, postgresql, docker, http, oauth, caching, session_vs_token, async_sync) + cors 1개, 총 11개로 확장. 설계 원칙:
- 여전히 "파일당 주제 하나" 유지 (Day 1 원칙)
- 완전히 무관한 문서뿐 아니라, 의도적으로 교차 언급 문장을 삽입해 "관련은 있지만 핵심은 아닌" 케이스를 만듦 - 예: `oauth.md` 끝에 JWT와의 관계 문단 추가, `http.md`에 Authorization 헤더 언급, `caching.md`에 JWT 블랙리스트 언급, `spring.md`에 FastAPI Depends() 비교
- 두 컬렉션(`ko-sroberta`, Gemini Embedding) 모두 동일하게 11개로 재인덱싱

### Retriever 단독 재검증
`retriever.invoke("JWT")` 결과, 상위 2개는 `jwt.md`, 3위는 (예전처럼 무관한 `fastapi.md`가 아니라) `oauth.md`의 "JWT와의 관계" 문단이 랭킹됨 - KB 확장이 의도한 대로 "관련도에 따른 순위"를 만들어냈음을 확인.

### Context Precision 재실행 결과
5개 질문 평균 0.8000 (기존 1.0000에서 하락). 특히 Q2("Access Token과 Refresh Token의 차이")에서 0.0000 - `jwt.md`와 `oauth.md`가 동시에 "Access Token"을 언급해 검색 결과가 흔들린 것으로 추정.

### Embedding 비교 재실행 결과 - 처음으로 유의미한 차이 확인

| | Faithfulness | Context Precision |
|---|---|---|
| ko-sroberta-multitask | 0.8400 | 0.8000 |
| Gemini Embedding | 1.0000 | 1.0000 |

5개 질문 중 4개는 두 임베딩 모두 만점으로 동일했으나, Q2("Access Token과 Refresh Token의 차이")에서만 `ko-sroberta`가 faithfulness=0.2000, context_precision=0.0000으로 크게 하락한 반면 Gemini Embedding은 1.0000을 유지함.

### 해석
Q2는 `jwt.md`(정답)와 `oauth.md`("JWT와의 관계" 문단)가 모두 "Access Token"이라는 표면적 어휘를 공유하는, KB 내에서 가장 구분이 어려운 케이스. `ko-sroberta`는 `oauth.md`를 더 높은 순위로 검색했는데, 이는 두 문서가 공유하는 "Access Token" 등의 용어가 영향을 준 것으로 추정된다(내부 판단 근거를 직접 확인한 것은 아님). Gemini Embedding은 이 케이스에서 더 적절한 Retrieval 결과를 반환한 것으로 해석할 수 있다.

이전 실험(KB 2개 문서)에서는 이런 "헷갈리는 케이스" 자체가 KB에 존재하지 않아 두 임베딩이 항상 동일한 결과를 냈음. KB를 의도적으로 확장해 구분이 어려운 케이스를 포함시키자, 두 임베딩의 관측 가능한 성능 차이가 처음으로 드러남.

### 결론
1. 이전 실험에서 "실험 결과로 임베딩을 선택할 수 없다"고 정리했던 결론을 정정할 근거가 마련됨. 다만 이는 이전 결론이 틀렸다는 뜻이 아니라, 당시 KB 조건(2개 문서)에서는 그 판단이 타당했고 이번에 실험 조건(KB 11개, 구분이 어려운 케이스 포함)이 달라졌기 때문에 결론도 함께 업데이트된 것으로 봐야 함. 현재 표본은 1개 케이스(Q2)뿐이라 일반화하기는 이르며, "구분이 어려운 조건에서는 Gemini Embedding이 ko-sroberta보다 안정적이었다"는 관찰 수준으로 정리함
2. **이번 프로젝트에서 Retrieval 관련 실험(Day 1 semantic retrieval, Context Precision 단독, 첫 Embedding 비교, 이번 재실험)은 모두 "KB의 품질과 규모가 Retrieval 성능 평가의 전제 조건"이라는 동일한 결론으로 수렴했다.** 이는 개별 실험 각각의 발견이 아니라, 네 차례의 독립적인 실험이 반복적으로 도달한 공통 패턴이라는 점에서 신뢰도가 높음
3. 다만 현재 표본(질문 5개, 그중 차이가 드러난 건 1개)은 결론을 확정하기엔 작음 - Retrieval 평가에 특화된 질문 세트를 별도로 확장하면 더 신뢰할 수 있는 결과를 얻을 수 있음

### Action Item
- Retrieval 평가 전용 질문 세트를 새로 구성해 표본 확대 (Calibration Set은 Judge 평가용으로 목적이 다르므로 재사용하지 않음) - 예: JWT, OAuth, Session, Docker, Spring, HTTP, CORS, Cache 등 KB 11개 주제를 고르게 커버하는 질문들로 별도 세트 작성
- README/Key Findings에 "Retrieval 관련 실험들이 공통적으로 KB 규모·구성의 중요성을 가리켰다"는 발견을 핵심 항목으로 반영
- Project Outcomes에는 "KB 확장 후 재실험 결과, 구분이 어려운 케이스에서 Gemini Embedding이 더 안정적인 경향을 관찰함(표본 제한적, 추가 검증 필요)"으로 조건부 반영

---

## 2026-07-14 - Retrieval 평가 전용 질문 세트 구축 및 실행

### 배경
Context Precision/Embedding 비교의 기존 표본(Calibration Set 재사용, 5개 질문)이 결론을 일반화하기엔 작다는 한계를 인식. KB 11개 주제를 고르게 커버하고, KB에 실제로 심어둔 교차 언급(oauth-jwt, session_vs_token-jwt, async_sync-fastapi, spring-fastapi, http-jwt, caching-jwt, cors-jwt)을 겨냥한 혼동 질문을 포함한 전용 평가셋을 새로 구축.

### 구성
`tests/fixtures/retrieval_eval_set.json`, 20문항. 각 항목은 `question`, `expected_source`(검증용, RAGAS에는 미사용), `reference`(Context Precision 계산용 이상적 답변)로 구성. KB 11개 주제 기본 질문 + 혼동 질문 조합.

### 실행 결과
`scripts/run_retrieval_eval.py`로 20문항 전체를 Top-1 source 정확도, Faithfulness, Context Precision 세 지표로 동시 측정.

- Top-1 source 정확도: 16/20 (80.0%)
- 평균 Faithfulness: 0.8125
- 평균 Context Precision: 0.8500

이전 5문항 표본(모두 만점)보다 훨씬 풍부한 분포가 나타남, 표본을 늘린 효과가 실제로 확인됨.

### MISS 4건 분석

| 질문 | expected | 실제 top-1 | faithfulness/precision | 판정 |
|---|---|---|---|---|
| FastAPI 비동기 처리 | fastapi.md | async_sync.md | 1.0000/1.0000 | 라벨 설계 문제(주제가 겹침) |
| 트랜잭션 ACID | postgresql.md | oauth.md | 0.0000/0.0000 | 실제 검색 실패 |
| JWT 블랙리스트 저장소 | caching.md | jwt.md | 1.0000/1.0000 | 라벨 설계 문제(jwt.md에도 관련 문장 있음) |
| JWT 쿠키 저장과 CORS | cors.md | jwt.md | 1.0000/1.0000 | 라벨 설계 문제(질문이 JWT를 먼저 언급) |

4건 중 3건은 검색 실패가 아니라, 질문 자체가 두 문서 모두에 걸쳐 있는데 `expected_source`를 하나로만 좁게 설계한 결과였음. 이는 faithfulness/context_precision이 해당 3건에서 모두 만점이라는 사실로 뒷받침됨. 진짜 문제는 "트랜잭션 ACID" 1건뿐 - 의미상 무관한 oauth.md가 검색된 것은 재현성 확인이 필요한 이상 사례.

### 결론
1. 질문 세트를 5개에서 20개로 확대하자 그동안 가려져 있던 KB 설계의 미묘한 문제(정답이 하나가 아닌 질문에 단일 라벨을 부여한 것)가 드러남
2. Top-1 source 정확도만으로 판단하면 80%로 낮아 보이지만, 실제 검색 실패는 20건 중 1건(트랜잭션 ACID)뿐이었음 - 단일 지표만으로 결론 내리지 않고 faithfulness/context_precision을 함께 봐야 하는 이유를 실증
3. "트랜잭션 ACID → oauth.md" 사례는 KB 규모가 여전히 크지 않은 상태에서 발생한 이상 검색으로, 원인 규명 및 재현 여부 확인이 필요

### Action Item
- "트랜잭션 ACID → oauth.md" 케이스 재현 여부 확인 (동일 질문 재실행, 안 되면 임베딩 유사도 직접 확인)
- expected_source가 실제로는 복수 문서에 걸쳐 있는 3개 질문(FastAPI 비동기, JWT 블랙리스트, JWT-CORS)은 `expected_sources`(복수) 필드로 재설계하거나, 해당 질문을 더 명확히 한 문서만 가리키도록 수정
- 이 세트로 임베딩 비교(ko-sroberta vs Gemini)를 재실행해 표본 확대 효과를 Embedding 비교에도 반영

---

## 2026-07-15 (계속) - "트랜잭션 ACID" 검색 오류 재현 확인

### 가설
직전 실험에서 발견한 "트랜잭션의 ACID 속성은 무엇인가요?" 질문이 postgresql.md가 아닌 oauth.md를 1순위로 반환한 것이 우연인지, 재현되는 문제인지 확인한다.

### 방법
동일 질문으로 `retriever.invoke()`를 3회 연속 실행, 매번 상위 3개 결과를 비교.

### 결과
3회 모두 동일하게 재현됨: 1순위 oauth.md, 2순위 http.md, 3순위 postgresql.md(단, 정답 chunk가 아닌 "트랜잭션 고립 수준" chunk).

### 원인 분석
postgresql.md의 정답 chunk(트랜잭션 정의, ACID 속성 설명)는 상위 3위 안에도 들지 못함. 3순위로 나온 것은 같은 파일의 다른 chunk(고립 수준 관련)였음. 즉 postgresql.md 자체가 완전히 무관하게 취급된 게 아니라, 파일 내부에서도 정답 chunk보다 다른 chunk가 우선 검색됨.

postgresql.md는 Day 1 원칙("파일당 주제 하나")을 지켰다고 판단했으나, 실제로는 "인덱스"와 "트랜잭션"이라는 두 개의 하위 주제를 한 파일에 담고 있었음. 이는 KB 확장 시 주제 분리 기준을 파일 단위로만 적용했고, 파일 내 chunk 단위의 주제 응집성은 별도로 검토하지 않았던 데서 비롯된 것으로 판단됨.

### 결론
1. 이 오류는 일시적 변동이 아니라 재현 가능한 Retrieval 문제임을 확인
2. Day 1에서 확립한 "파일당 주제 하나" 원칙이, 실제로는 "chunk당 주제 하나"까지 세밀하게 적용되지 않으면 불완전할 수 있음을 새로 발견
3. oauth.md가 왜 이 질문에 높은 유사도를 받았는지(표면적 문장 구조 유사성 추정)는 임베딩 벡터를 직접 비교하지 않는 한 확정할 수 없어, 추정 수준으로만 기록

### Action Item
- `postgresql.md`를 인덱스 전용 파일과 트랜잭션 전용 파일로 분리하고, 재인덱싱 후 ACID 단일 질문 및 20문항 평가셋으로 개선 전후를 비교
- KB 전체 문서에 대해 “파일당 주제 하나”뿐 아니라 “chunk당 주제 하나”까지 점검하는 절차를 추가할지 검토
- 나머지 3개는 top-1 exact-match 기준에서는 MISS였지만, 검색된 top-k context가 reference를 충분히 뒷받침했다. 단일 `expected_source`가 지나치게 좁았을 가능성이 높으므로 `expected_sources` 복수 라벨로 재설계

---

## 2026-07-15 (계속) - postgresql.md 분리 및 개선 전후 비교

### 배경
"트랜잭션 ACID" 질문 검색 오류가 3회 재현되어 우연이 아님을 확인. 원인 분석 결과, postgresql.md가 "인덱스"와 "트랜잭션"이라는 두 개의 하위 주제를 한 파일에 담고 있어 chunk 단위 주제 응집성이 떨어졌던 것으로 판단. 이를 단일 변수 변경 실험(문서 분리)으로 검증.

### 가설
postgresql.md를 인덱스 전용 파일과 트랜잭션 전용 파일로 분리하면, ACID 질문의 검색 순위가 개선되고 다른 문항에는 영향이 없을 것이다.

### 방법
1. postgresql.md를 postgresql_index.md, transaction.md 두 파일로 분리, 원본은 삭제
2. 두 벡터스토어 컬렉션(ko-sroberta, Gemini Embedding) 모두에서 기존 postgresql.md chunk를 수동으로 제거 (파일 삭제만으로는 로드 스크립트가 자동 삭제하지 못함을 확인 후 조치)
3. 재인덱싱 후 ACID 단일 질문을 3회 반복 실행해 재현성 확인
4. Retrieval 평가 세트(20문항) 전체 재실행, 라벨(`expected_source`)을 새 파일명에 맞게 갱신 후 baseline과 비교

### 결과

**ACID 단일 질문**: 개선 전 순위(oauth.md → http.md → postgresql.md 내 Isolation chunk, 정답 chunk는 top-3 밖) → 개선 후 순위(transaction.md가 1순위, 3회 재현). oauth.md는 여전히 2순위로 남아, 두 문서 간 표면적 유사성 자체는 사라지지 않았으나 정답이 최우선으로 검색되는 상태로 개선됨.

**20문항 전체**:

| 지표 | 개선 전 | 개선 후 |
|---|---|---|
| Top-1 정확도 | 16/20 (80%) | 17/20 (85%) |
| 평균 Faithfulness | 0.8125 | 0.8500 |
| 평균 Context Precision | 0.8500 | 0.9500 |

ACID 질문 1건이 MISS에서 OK로 전환됐고, 나머지 19개 문항 중 검색 순위 또는 평가 지표가 악화된 항목은 없었다. 평가 도중 라벨 갱신 스크립트가 관련 없는 “PostgreSQL 인덱스” 질문의 `expected_source`까지 잘못 치환해 일시적으로 새로운 MISS가 발생했으나, 실제 top-1 검색 결과는 `postgresql_index.md`로 정확했다. 이는 검색 오류가 아닌 평가셋 라벨 오류로 확인해 즉시 수정했다.

### 결론
1. "chunk당 주제 하나"라는 새 원칙이 실제로 Retrieval 품질을 개선한다는 것이 단일 변수 변경 실험으로 검증됨. 문서를 분리한 것 외에 다른 조건은 바꾸지 않았고, 개선이 ACID 질문에 국한되고 다른 문항에는 부작용이 없었다는 것으로 인과관계를 뒷받침함
2. oauth.md와의 표면적 유사성은 문서 분리로 해소되지 않았음. 근본 원인(왜 ACID/트랜잭션 설명과 OAuth 설명이 임베딩 공간에서 유사하게 취급되는지)은 여전히 불확실하며, 문서 분리는 "정답이 상위로 올라오게" 만든 것이지 "혼동 자체를 없앤" 것은 아님
3. Retrieval 평가 세트 구축 과정에서 라벨 설계 실수가 반복적으로 발생함(이번 오작동 포함, 이전 3개 MISS도 동일한 패턴). 평가 세트의 라벨 정확성 자체도 별도로 관리가 필요한 자산임을 확인

### Action Item
- KB의 다른 문서들도 "chunk당 주제 하나" 기준으로 재점검 (특히 여러 하위 개념을 다루는 문서가 있는지)
- Retrieval 평가 세트의 나머지 3개 MISS(FastAPI/async_sync, JWT/caching, JWT/cors)는 `expected_sources`(복수) 필드로 재설계
- 임베딩 비교(ko-sroberta vs Gemini)를 이 20문항 세트로 재실행해 이전 5문항 기준 결과와 비교

---

## 2026-07-15 (계속) - expected_sources 복수 라벨 재설계 및 KB baseline 확정

### 배경
직전 실험에서 MISS로 분류됐던 3건(FastAPI 비동기, JWT 블랙리스트, JWT-CORS)은 검색 실패가 아니라 "정답이 하나가 아닌 질문에 단일 라벨을 부여한" 평가 설계 문제로 판단됨. `expected_source`(단수) 필드를 `expected_sources`(리스트)로 전면 교체.

### 방법
- 3개 항목은 실제로 정답으로 인정할 문서 2개씩을 명시 (예: FastAPI 비동기 → `["fastapi.md", "async_sync.md"]`)
- 나머지 17개 항목도 필드명을 통일해 `expected_sources`(원소 1개 리스트)로 변경
- 판정 로직을 `top_source == expected_source`에서 `top_source in expected_sources`로 변경

### 결과
20문항 전체 Top-1 in expected_sources 정확도: 20/20 (100%). 평균 Faithfulness 0.8625, 평균 Context Precision 0.9000.

### 해석 - 100%를 "Retrieval이 완벽하다"로 해석하지 않음
이번 100%는 검색 결과가 개선된 것이 아니라, **판정 기준을 완화한 결과**다. 19, 20번 문항은 여전히 이전과 동일하게 `jwt.md`가 검색됐고, 검색 자체는 바뀌지 않았다. 즉 이 지표는 "라벨 설계가 이제 실제 정답 범위를 정확히 반영한다"는 것을 보여주는 것이지, "Retriever 성능이 향상됐다"는 근거가 아니다.

### 새로 발견한 문제 - source는 맞는데 낮은 근거 점수 (4번, 11번)
- 4번("세션 vs 토큰 인증 차이"): top-1 source는 정확(session_vs_token.md)하지만 faithfulness=0.1667, context_precision=0.0000
- 11번("Spring Bean 기본 스코프"): top-1 source는 정확(spring.md)하지만 faithfulness=0.0000, context_precision=0.0000

두 케이스 모두 Top-1 source 정확도만 보면 완전히 가려지는 문제. source는 맞지만 retrieved chunk 안에 reference 문장을 뒷받침할 근거가 충분치 않거나, chunk 분할 경계 때문에 관련 내용이 다른 chunk에 있을 가능성. (별도의 추가적인 원인 분석이 필요)

### 결론
1. Top-1 source 정확도는 "어느 파일에서 검색됐는가"만 보는 지표라, source가 맞아도 근거 품질(Faithfulness, Context Precision)이 낮을 수 있다는 것을 이번에 직접 확인함. 두 지표를 함께 봐야 하는 이유가 다시 한 번 실증됨
2. 이번 KB(12개 문서) + 평가셋(20문항, expected_sources 복수 라벨) 구성을 이후 실험의 baseline으로 확정. 이 상태를 고정한 채로 Embedding 비교를 진행함

### Action Item
- 4번, 11번 케이스의 retrieved chunk 원문을 직접 확인해 원인 규명 (chunk 분할 문제인지, reference 문장 자체가 chunk 내용과 표현이 달라서인지)
- 이 baseline(KB 12개, 평가셋 20문항)을 고정한 채로 ko-sroberta vs Gemini Embedding 비교 실행

---

## 2026-07-15 (계속) - 4번/11번 저근거점수 케이스 원인 규명: Chunking 문제

### 가설
Top-1 source는 정확한데 Faithfulness/Context Precision이 낮은 4번(session_vs_token), 11번(Spring Bean) 케이스의 원인이 무엇인지 확인한다.

### 방법
두 질문에 대해 retriever가 실제로 반환한 chunk 원문을 직접 출력해 확인.

### 결과

**4번(session_vs_token.md)**: 1순위 chunk의 전체 내용이 다음과 같음.
```
# 세션 기반 인증 vs 토큰 기반 인증
```
제목 한 줄만 있고 본문이 전혀 없는 chunk. reference 문장(세션/토큰 정의)이 이 chunk에 없어 Faithfulness/Context Precision이 낮게 나온 것으로 확인. 원인은 임베딩이나 라벨 문제가 아니라, chunking 과정에서 제목과 본문이 서로 다른 chunk로 분리된 것으로 추정.

**11번(Spring Bean)**: 상위 3개 chunk(spring.md 2개, fastapi.md 1개) 어디에도 "싱글톤 스코프"라는 표현이 등장하지 않음. reference 문장이 담긴 chunk가 검색 결과에 아예 포함되지 않은 것으로 확인.

### 결론
두 케이스 모두 Retrieval의 순위 문제(엉뚱한 문서를 가져옴)가 아니라, Chunking 설계 문제(맞는 문서를 가져왔지만 필요한 문장이 그 chunk에 없거나 다른 chunk로 밀려남)로 확인됨. 이는 이전 postgresql.md 분리 실험에서 다룬 "chunk당 주제 하나" 문제와는 다른 층위의 문제 - 이번엔 주제가 섞인 게 아니라, chunk 경계 자체가 문장을 불완전하게 잘랐거나 필요한 문장이 검색 범위(k=3) 밖으로 밀려난 경우.

### Action Item
- session_vs_token.md의 실제 chunk 분할 상태를 확인해, 제목만 담긴 chunk가 생기는 원인(chunk_size, 문단 구분자) 점검
- spring.md도 동일하게 chunk 분할 상태 확인, "싱글톤 스코프" 문장이 어느 chunk에 속하는지 확인
- 이 문제는 postgresql.md 분리와 달리 "주제 분리"로 해결되지 않을 수 있음 - chunk_size 조정이나 문서 내 문단 구성 방식 자체를 재검토해야 할 가능성

---

## 2026-07-15 (계속) - spring.md/session_vs_token.md 분리 결과: 성공과 실패가 갈림

### 배경
4번(session_vs_token), 11번(Spring Bean) 저근거점수 문제의 원인이 chunking(제목만 담긴 chunk)으로 확인됨에 따라, 두 문서를 하위 주제 단위로 분리하는 실험을 진행.

### 방법
- `spring.md` -> `spring_di.md`, `spring_boot.md`, `spring_layered_architecture.md`, `spring_bean_scope.md` (4개)
- `session_vs_token.md` -> `session_auth.md`, `token_auth.md`, `session_vs_token_scaling.md` (3개)
- 원본 파일 삭제, 두 컬렉션(ko-sroberta, Gemini)에서 유령 chunk 수동 제거 후 재인덱싱
- 평가 세트의 관련 라벨을 새 파일명으로 갱신 후 20문항 재실행

### 결과 - 결과가 문서별로 반대 방향으로 갈림

**Spring 분리: 성공**
- 11번(Spring Bean 기본 스코프): faithfulness 0.0000->1.0000, context_precision 0.0000->1.0000
- Bean Scope를 독립된 짧은 chunk로 분리한 것이 정확히 의도한 효과를 냄

**Session vs Token 분리: 실패 (역효과)**
- 4번(세션 vs 토큰 차이): 분리 전 top-1은 session_vs_token.md(원본, faithfulness 0.1667)였으나, 분리 후 top-1이 oauth.md로 바뀌어 MISS 발생
- 5번(JWT 로그아웃 처리): 분리 전 top-1은 session_vs_token.md(faithfulness 0.3333)였으나, 분리 후 top-1이 session_auth.md(관련은 있으나 틀린 하위 문서)로 MISS 발생

전체 지표는 Top-1 정확도 20/20(100%)->18/20(90%)로 하락했으나, 평균 Faithfulness는 0.8625->0.9175로 상승, Context Precision은 0.9000->1.0000으로 상승. 즉 Top-1 exact-match 지표와 Faithfulness/Context Precision 지표가 서로 다른 방향을 가리키는 상황 발생.

### 원인 분석
postgresql.md, spring.md는 "서로 무관한 여러 하위 주제"가 한 파일에 섞여 있어 분리가 자연스러웠음. 반면 session_vs_token.md는 애초에 "두 개념의 비교"가 문서의 본질적 주제였음. 이를 세 조각으로 쪼개자 "비교"라는 문맥 자체가 사라지고, 각 조각이 독립된 정의문으로만 남아 질문(비교를 묻는 질문)과의 매칭이 오히려 약해진 것으로 판단. ACID/OAuth 혼동과 유사하게, 표면적으로 정의문 구조가 비슷한 oauth.md가 끼어드는 현상이 재현됨.

### 결론
1. "chunk당 주제 하나" 원칙은 무조건 옳은 것이 아니라, 문서의 본질이 "여러 독립 주제의 나열"인지 "여러 개념의 비교"인지에 따라 다르게 적용해야 함을 확인. 비교형 문서는 분리보다 하나의 chunk에 비교 대상을 함께 담는 것이 더 나을 수 있음
2. Top-1 exact-match 정확도만으로 개선 여부를 판단하면 오도될 수 있음이 이번에도 재확인됨(Faithfulness/Context Precision은 상승했으나 Top-1은 하락) - 단일 지표에 의존하지 않는다는 원칙이 재확인됨

---

## 2026-07-18 (계속) - 비교형 질문의 retrieval unit 재구성

### 배경
session_vs_token.md를 세션·토큰·확장성 문서로 분리한 결과, 단일 개념 질문과 달리 비교형 질문에서 필요한 근거가 여러 문서로 흩어져 Top-1 정확도가 20/20에서 18/20으로 하락했다.

### 가설
비교형 질문은 세션과 토큰의 정의·차이·확장성 비교를 하나의 완결된 retrieval unit에 함께 유지해야 검색 품질이 개선될 것이다. JWT 로그아웃은 별도의 무효화 전략 문서로 분리하는 것이 적절하다.

### 방법
- `session_vs_token.md`를 비교형 질문에 필요한 정의와 확장성 차이를 포함하는 문서로 재구성
- JWT 로그아웃·무효화 전략은 `jwt_logout_invalidation.md`로 분리
- 재인덱싱 후 20문항 평가셋 재실행

### 결과
- 세션/토큰 비교: `oauth.md` 1위, Faithfulness 0.3333 → `session_vs_token.md` 1위, Faithfulness 1.0000
- JWT 로그아웃: `session_auth.md` 1위 → `jwt_logout_invalidation.md` 1위
- Top-1 in expected_sources: 20/20 (100.0)
- 평균 Faithfulness: 0.9708
- 평균 Context Precision: 1.0000

### 결론
문서 분리의 적절한 단위는 파일 크기나 개념 개수가 아니라, 질문 하나에 완결된 근거를 제공하는 retrieval unit이다. 독립 개념이 나열된 문서는 분리가 유리했지만, 비교·트레이드오프 질문은 비교 대상을 함께 유지하는 편이 효과적이었다.

---

## 2026-07-18 (계속) - JWT 로그아웃 문서의 근거 범위 보완

### 발견
`jwt_logout_invalidation.md`는 1위로 정확히 검색됐고 Context Precision도 1.0000이었지만, Faithfulness는 0.6667이었다. Reference의 “Refresh Token을 통한 Access Token 재발급”이 문서에 명시적으로 포함되지 않았기 때문이다.

### 조치
문서에 “만료된 Access Token은 Refresh Token 검증 후 재발급한다”는 근거 문장을 추가하고 단일 문항으로 재검증한다.

### 결론
검색 순위가 맞더라도, reference의 모든 핵심 주장을 KB가 명시적으로 뒷받침해야 Faithfulness가 높아진다. 이는 retrieval failure가 아니라 content coverage 문제다.

### Retrieval 설계 원칙
- 독립 개념 나열 문서: 하위 주제 분리가 유리
- 비교·트레이드오프 질문: 비교 근거를 한 retrieval unit에 유지
- 정확한 source 검색만으로 충분하지 않음
- top-k context가 reference의 모든 핵심 주장을 뒷받침해야 함
- 평가셋 라벨도 코드처럼 검증·관리해야 함

---

## 2026-07-20 (계속) - Embedding 비교 재실행 (Retrieval 평가셋 20문항 기준)

### 배경
기존 임베딩 비교(2026-07-14)는 Calibration Set의 good 답변 5개 표본으로 진행됐고, "구분이 어려운 케이스에서 Gemini Embedding이 더 안정적"이라는 결론을 냈으나 표본이 작아 일반화하기는 이르다고 스스로 명시했었음. Retrieval Unit 재설계로 KB baseline(18개 문서)을 확정한 뒤, 이 baseline을 고정한 채로 20문항 평가셋을 이용해 Embedding 비교를 재실행.

### 가설
표본을 5개에서 20개로 늘리면, 이전에 관찰됐던 "Gemini Embedding이 더 안정적"이라는 경향이 재현되거나 강화될 것이다.

### 방법
`scripts/compare_embeddings_retrieval_eval.py`를 새로 작성(기존 `compare_embeddings.py`의 이중 리트리버 비교 구조 + `run_retrieval_eval.py`의 20문항 `expected_sources` 기반 평가 로직을 결합). 실행 전 ko-sroberta·Gemini 두 컬렉션 모두 현재 KB(18개 문서, 29개 chunk)와 이미 동기화돼 있음을 확인(재인덱싱 불필요). 20문항 전체를 두 리트리버 각각에 대해 Top-1 정확도·Faithfulness·Context Precision으로 평가.

### 결과

| | Top-1 정확도 | Faithfulness | Context Precision |
|---|---|---|---|
| ko-sroberta-multitask | 100.0% (20/20) | 0.9708 | 1.0000 |
| Gemini Embedding | 95.0% (19/20) | 0.9500 | 1.0000 |

두 임베딩의 top-1 source가 갈린 질문 3개 중 2개("FastAPI 비동기 처리", "JWT 쿠키+CORS")는 둘 다 `expected_sources`에 포함되는 정답이라 실질적 문제 없음. 진짜 오답은 1건: "JWT를 HTTP 요청에 실어 보낼 때 어떤 헤더를 사용하나요?" 질문에서 Gemini Embedding이 `http.md`(정답) 대신 `cors.md`를 1순위로 반환(Faithfulness 0.5000).

### 결론 - 기존 결론이 뒤집힘
1. **가설 기각.** 표본을 5개→20개로 늘리자 정반대 결과가 나왔다. 5문항 표본에서는 Gemini Embedding이 더 안정적으로 관찰됐으나, 20문항에서는 ko-sroberta가 Top-1·Faithfulness 모두 더 높고, Gemini는 새로운 실패 사례(`http.md` 질문을 `cors.md`로 혼동)를 보임.
2. 이는 "표본이 작아 일반화하기는 이르다"고 스스로 명시했던 이전 결론의 한계가 실제로 확인된 사례. 작은 표본에서 관찰된 패턴을 그대로 일반화하면 안 된다는 것을 직접 증명함.
3. 다만 20문항도 절대적으로 큰 표본은 아니므로, 이번 결과 역시 최종 진리로 단정하지 않는다. 현재까지 공정한 요약은 "이 KB·이 평가셋 기준으로는 ko-sroberta-multitask가 Gemini Embedding보다 근소하게 우세하다" 정도.

### Action Item
- Gemini Embedding이 `http.md` 질문에서 `cors.md`로 혼동한 원인(임베딩 벡터 유사도 직접 비교)은 추가 분석하지 않음. 현재 결론(ko-sroberta 채택)을 바꿀 정도의 문제가 아니라 우선순위 낮음으로 판단
- README/명세서의 Embedding 비교 서술을 "20문항 기준 최종 결과(ko-sroberta 채택)"로 갱신하고, 기존 5문항 결론은 "초기 소표본에서의 관찰이었으며 이후 뒤집힘"으로 명확히 구분해 남김

---

## 2026-07-21 - Agent v3: 점수 구간별 다중 분기

### 배경
Agent v2까지의 분기는 `technical_score < 5` 하나뿐이었고, 점수가 5 이상이면 아무 노드도 실행되지 않고 즉시 종료됐다. 즉 두 갈래 중 한쪽이 비어 있어 분기가 단조로웠고, "잘 답한 사용자에게는 아무것도 돌려주지 않는" 상태이기도 했다. 면접 코치라는 제품 목적에 비추어 점수대별로 필요한 코칭의 종류가 다르다고 보고 세 갈래로 확장했다.

### 설계 결정 - 구간별로 "다른 종류의" 응답을 준다
단순히 갈래 수만 늘리는 것이 아니라, 각 구간이 서로 다른 성격의 결과를 내도록 설계했다.

| 구간 | 노드 | 반환 | 설계 근거 |
|---|---|---|---|
| 0~3점 | `fundamentals_node` | `ConceptExplanation` | 개념 자체를 모르는 상태에서는 "무엇을 공부하라"(Learning Tip)보다 개념 설명이 먼저 필요하다고 판단 |
| 4~6점 | `learning_tip_node` → `followup_node` | `LearningTip` + 꼬리질문 | 기존 v2 경로 유지 (부분 이해 상태에는 약점 보완 코칭이 적합) |
| 7~10점 | `advanced_question_node` | `AdvancedQuestion` | 보완할 약점이 없으므로 코칭 대신 한 단계 깊은 질문으로 이해의 깊이를 확인 |

경계값은 `FUNDAMENTALS_THRESHOLD = 4`, `ADVANCED_THRESHOLD = 7`로 상수 분리. 기존 `FOLLOWUP_THRESHOLD = 5`는 두 상수로 대체됐다.

### 검증 1 - 분기 로직 전수 검증 (LLM 호출 없이)
`decide_next_step()`은 순수 함수이므로 Gemini 호출 없이 단독 검증이 가능하다. `EvaluationResult`를 직접 만들어 0~10점 **11개 값 전부**를 넣고 라우팅 결과를 확인, 전 구간 통과.

Day 4의 경계값 검증(0/5/10 세 지점만 확인, 인접값은 미검증)보다 촘촘한 전수 검증이다. 당시에는 경계값 답변을 만들어내기 위해 실제 LLM 호출이 필요했지만, 이번에는 분기 함수를 State 입력만으로 직접 호출할 수 있어 비용 없이 전 구간을 덮을 수 있었다. 노드를 순수 함수로 분리해둔 구조의 이점이 드러난 사례.

### 검증 2 - 그래프 구조
`build_interview_agent_graph()`를 컴파일해 노드와 엣지를 직접 조회. 노드 6개(`retrieval`, `judge`, `fundamentals`, `learning_tip`, `followup`, `advanced`), `judge`에서 나가는 조건부 엣지 3갈래, 세 경로 모두 END로 수렴하는 것을 확인. **END로 직행하는 빈 경로가 사라졌다.**

### 검증 3 - 실제 실행 (`scripts/check_score_branches.py`)
구간별로 해당 점수가 나오도록 설계한 답변 3개를 실제 그래프에 통과시켜 확인.

| 케이스 | technical_score | next_action | 결과 필드 | 판정 |
|---|---|---|---|---|
| "잘 모르겠습니다." | 0 | `fundamentals_explained` | `concept_explanation` | PASS |
| 경미한 오류 포함 답변 | 5 | `followup_generated` | `learning_tip` | PASS |
| 정확한 답변 | 10 | `advanced_question_generated` | `advanced_question` | PASS |

세 케이스 모두 **다른 경로의 State 키가 채워지지 않는 것**까지 확인(경로 간 누수 없음).

출력 품질도 의도대로 나왔다.
- 0점: 학습 방향이 아니라 개념 자체를 설명(`Header, Payload, Signature 세 부분으로 구성된...`)
- 5점: 답변에 의도적으로 심어둔 오류("토큰이 만료되면 자동으로 갱신됩니다")를 정확히 지목
- 10점: 이미 답한 내용을 되묻지 않고 트레이드오프를 묻는 심화 질문 생성. 프롬프트의 "이미 답한 내용을 다시 묻지 마세요" 지시가 실제로 반영됨

### 부수 결정 - `next_action`을 API 응답에 노출
State의 `next_action`을 응답 필드로 내보내도록 했다. 어느 경로가 실행됐는지 클라이언트가 알 수 있고, 이후 API 성능 측정 시 분기별 지연 시간을 구분해 집계할 수 있다(`/evaluate-answer`는 경로에 따라 Gemini 호출이 1~3회로 달라짐).

### 결론
1. "분기를 늘린다"가 아니라 "구간마다 필요한 코칭의 종류가 다르다"를 기준으로 설계해, 모든 점수대에서 결과가 나오도록 함
2. 순수 함수로 분리된 라우팅 로직은 LLM 호출 없이 전수 검증이 가능하다는 것을 확인. 노드/라우팅 분리 구조의 실질적 이점
3. 다만 이번 확장으로도 **그래프에 사이클은 여전히 없다.** "조건부 분기만 할 것이면 LCEL로도 가능하지 않은가"라는 반문에 답하려면 멀티턴 루프가 필요하며, 이는 Future Work로 유지

### Action Item
- README/명세서의 Agent 구조도, State 스키마, API 응답 스펙을 v3 기준으로 갱신
- 멀티턴 루프(사이클 도입)는 Future Work 최우선 항목으로 유지

---

## 2026-07-21 (계속) - Docker 패키징: 이미지 크기 10.9GB에서 3.79GB로

### 배경
Phase 8(배포) 첫 단계로 Docker 이미지를 만들고 Compose로 로컬 실행을 확인. 최적화를 미리 추측해서 적용하기보다, **일단 `uv.lock` 그대로 빌드해 크기를 실측한 뒤 그 데이터로 판단**하는 순서를 택했다(이 프로젝트에서 반복해온 방식).

### 1차 빌드 결과 - 10.9GB
빌드 자체는 성공했으나 이미지가 10.9GB. `docker history`로 레이어를 보니 의존성 설치 레이어 하나가 6.04GB였고, 컨테이너 내부를 조회한 결과 원인이 명확했다.

| 패키지 | 크기 | 실제 필요 여부 |
|---|---|---|
| `nvidia` (CUDA 라이브러리) | 2.9GB | 불필요 (배포 대상에 GPU 없음) |
| `triton` (GPU 커널 컴파일러) | 652MB | 불필요 |
| `torch` | 914MB | 필요 |
| 기타(pyarrow, scipy, transformers 등) | ~1.2GB | 필요 |

`uv.lock`이 `sys_platform == 'linux'` 조건으로 torch에 CUDA 스택 전체(`cuda-toolkit`, `nvidia-cudnn-cu13` 등)를 딸려오게 잡고 있었다. **3.55GB가 전혀 쓰이지 않는 용량이었다.**

### 설계 결정 - CPU torch 설정을 pyproject.toml이 아니라 Dockerfile에만 둠
처음에는 `pyproject.toml`에 `sys_platform == 'linux'` 마커로 CPU torch를 지정하려 했으나 철회했다. **Google Colab도 Linux**이므로, 프로젝트 레벨에 이 설정을 박으면 Colab에서 GPU를 쓰려 할 때 CPU torch가 설치되는 부작용이 생긴다(메인 프로젝트 `korean-chatbot` 학습에 Colab GPU를 사용 중). CPU 전용 제약이 필요한 대상은 EC2로 갈 이미지 하나뿐이므로 Dockerfile 안에서만 처리했다.

### uv 동작 관련 발견 - 첫 시도 (실패)
Dockerfile에서 `tool.uv.sources`로 torch를 CPU 인덱스로 지정하고 `uv lock`을 실행했으나, **재빌드 후에도 nvidia/triton이 그대로 남아 있었다.** 빌드는 에러 없이 성공했고 이미지 크기도 10.9GB로 동일해, 성공 여부를 크기로 확인하지 않았다면 놓쳤을 실패다.

전체 재빌드를 반복하지 않고 원인을 찾기 위해, 설치는 생략하고 **의존성 해결(resolve)만 컨테이너에서 반복 실행**하며 확인했다. 그 결과 두 가지를 알게 됐다.

1. **`tool.uv.sources`는 직접 의존성에만 적용된다.** `torch`는 `sentence-transformers`를 통한 전이 의존성이라 지정이 무시됐다. torch를 `[project.dependencies]`에 직접 추가해야 적용된다.
2. **인덱스는 `explicit = true`로 제한해야 한다.** 그러지 않으면 `requests` 같은 무관한 패키지까지 pytorch 인덱스에서 찾으려다 resolve가 실패한다(실제로 `uv add --index`로 시도했을 때 이 에러가 발생).

두 조건을 함께 적용하자 `torch 2.13.0` → `2.13.0+cpu`로 바뀌고 nvidia 15개 패키지와 triton이 모두 제거됐다.

### 2차 빌드 결과

| | 1차 | 2차 |
|---|---|---|
| 이미지 크기 | 10.9GB | **3.79GB** |
| `.venv` | 5.7GB | 1.9GB |
| nvidia/triton | 존재 | 없음 |

### 실행 검증
- Compose 기동 확인
- 최초 기동 시 entrypoint가 빈 컬렉션을 감지해 KB 자동 인덱싱(18개 문서, 29 chunk)
- 재시작 후 "chunk 29개 확인, 인덱싱 건너뜀" 로그 확인 → **volume 영속화 정상 동작**
- `GET /` 200, `POST /evaluate-answer`로 0점 답변 전송 시 `next_action: fundamentals_explained` 정상 분기

### 추가 발견 - 아키텍처 불일치 (EC2 단계 선행 확인 필요)
빌드된 이미지가 **arm64**(Apple Silicon)다. EC2 표준 인스턴스(t2.micro, t3.small)는 x86_64라 **이 이미지는 그대로 실행되지 않는다.** 배포 시 `--platform linux/amd64`로 빌드하거나 Graviton(t4g) 인스턴스를 선택해야 한다. 또한 amd64로 빌드하면 CUDA 스택이 다시 개입할 수 있으므로, CPU torch 설정이 amd64에서도 동작하는지 재확인이 필요하다.

### 결론
1. "일단 만들고 재본 뒤 최적화한다"는 순서가 유효했다. 미리 추측했다면 CUDA가 3.55GB를 차지한다는 것도, 첫 최적화 시도가 조용히 실패했다는 것도 알 수 없었다
2. 빌드 성공 여부만으로 최적화 적용을 확인하면 안 된다. 1차 최적화는 에러 없이 빌드됐지만 실제로는 적용되지 않았고, **이미지 크기를 측정했기 때문에** 발견할 수 있었다
3. 전체 재빌드 대신 resolve 단계만 분리해 반복 실행한 것이 원인 규명 시간을 크게 줄였다. 검증 단위를 작게 쪼개는 접근이 여기서도 유효

### Action Item
- EC2 인스턴스 아키텍처 확정 후 `--platform linux/amd64` 빌드 검증 (Phase 8 ③)
- 이미지에 포함된 실험용 의존성(`ragas`, `datasets`, `pyarrow` 등)은 서빙에 불필요하므로, 추가 경량화가 필요하면 런타임/실험용 의존성 분리를 검토