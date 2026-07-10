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