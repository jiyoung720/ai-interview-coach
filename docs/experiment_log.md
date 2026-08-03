# 실험 로그

> 시간순 기록입니다. 각 항목은 `가설 -> 방법 -> 결과 -> 결론` 순으로 되어 있습니다.
> 핵심 결론만 빠르게 보시려면 [README의 Key Findings](../README.md#key-findings)가 더 짧습니다.

## 목차

**Retrieval 품질** (14개) 검색이 의미로 작동하는가, 문서를 어떤 단위로 쪼갤 것인가

- [2026-06-23 - Semantic Retrieval 검증](#2026-06-23---semantic-retrieval-검증)
- [2026-06-24 - Chain A Faithfulness 이슈 발견](#2026-06-24---chain-a-faithfulness-이슈-발견)
- [2026-07-13 (계속) - RAGAS Context Precision 적용](#2026-07-13-계속---ragas-context-precision-적용)
- [2026-07-13 (계속) - Embedding 비교 실험 (ko-sroberta-multitask vs Gemini Embedding)](#2026-07-13-계속---embedding-비교-실험-ko-sroberta-multitask-vs-gemini-embedding)
- [2026-07-14 (계속) - KB 확장 후 Context Precision / Embedding 비교 재실행](#2026-07-14-계속---kb-확장-후-context-precision--embedding-비교-재실행)
- [2026-07-14 - Retrieval 평가 전용 질문 세트 구축 및 실행](#2026-07-14---retrieval-평가-전용-질문-세트-구축-및-실행)
- [2026-07-15 (계속) - "트랜잭션 ACID" 검색 오류 재현 확인](#2026-07-15-계속---트랜잭션-acid-검색-오류-재현-확인)
- [2026-07-15 (계속) - postgresql.md 분리 및 개선 전후 비교](#2026-07-15-계속---postgresqlmd-분리-및-개선-전후-비교)
- [2026-07-15 (계속) - expected_sources 복수 라벨 재설계 및 KB baseline 확정](#2026-07-15-계속---expected_sources-복수-라벨-재설계-및-kb-baseline-확정)
- [2026-07-15 (계속) - 4번/11번 저근거점수 케이스 원인 규명: Chunking 문제](#2026-07-15-계속---4번11번-저근거점수-케이스-원인-규명-chunking-문제)
- [2026-07-15 (계속) - spring.md/session_vs_token.md 분리 결과: 성공과 실패가 갈림](#2026-07-15-계속---springmdsession_vs_tokenmd-분리-결과-성공과-실패가-갈림)
- [2026-07-18 (계속) - 비교형 질문의 retrieval unit 재구성](#2026-07-18-계속---비교형-질문의-retrieval-unit-재구성)
- [2026-07-18 (계속) - JWT 로그아웃 문서의 근거 범위 보완](#2026-07-18-계속---jwt-로그아웃-문서의-근거-범위-보완)
- [2026-07-20 (계속) - Embedding 비교 재실행 (Retrieval 평가셋 20문항 기준)](#2026-07-20-계속---embedding-비교-재실행-retrieval-평가셋-20문항-기준)

**평가 체계** (4개) Judge를 믿을 수 있는가, 채점 기준을 어떻게 세울 것인가

- [2026-07-06 - Judge Calibration 자동화 및 completeness 프롬프트 개선](#2026-07-06---judge-calibration-자동화-및-completeness-프롬프트-개선)
- [2026-07-07 (계속) - Calibration Set 재설계 및 최종 검증](#2026-07-07-계속---calibration-set-재설계-및-최종-검증)
- [2026-07-13 (계속) - RAGAS Faithfulness 적용](#2026-07-13-계속---ragas-faithfulness-적용)
- [2026-07-31 - 채점 루브릭 도입과 측정 도구 재설계 (Phase 12)](#2026-07-31---채점-루브릭-도입과-측정-도구-재설계-phase-12)

**Agent 설계** (4개) 점수에 따라 무엇을 할 것인가, 왜 LangGraph인가

- [2026-07-08 - Agent 조건부 분기 경계값(threshold=5) 검증](#2026-07-08---agent-조건부-분기-경계값threshold5-검증)
- [2026-07-08 (계속) - Agent v2: Learning Tip 노드 추가 (순차 설계)](#2026-07-08-계속---agent-v2-learning-tip-노드-추가-순차-설계)
- [2026-07-21 - Agent v3: 점수 구간별 다중 분기](#2026-07-21---agent-v3-점수-구간별-다중-분기)
- [2026-07-27 (계속) - 멀티턴 면접 루프 (Phase 11)](#2026-07-27-계속---멀티턴-면접-루프-phase-11)

**배포와 인프라** (5개) 이미지 크기, 자동화, 인스턴스 선정

- [2026-07-21 (계속) - Docker 패키징: 이미지 크기 10.9GB에서 3.79GB로](#2026-07-21-계속---docker-패키징-이미지-크기-109gb에서-379gb로)
- [2026-07-21 (계속) - GitHub Actions CI 구성](#2026-07-21-계속---github-actions-ci-구성)
- [2026-07-22 - EC2 배포: 메모리 측정으로 인스턴스 타입 결정, 디스크 부족 대응](#2026-07-22---ec2-배포-메모리-측정으로-인스턴스-타입-결정-디스크-부족-대응)
- [2026-07-22 (계속) - CD 구성: 배포 자동화가 기존 설계를 되돌아보게 한 지점들](#2026-07-22-계속---cd-구성-배포-자동화가-기존-설계를-되돌아보게-한-지점들)
- [2026-07-22 (계속) - API 성능 측정: 순차 설계의 비용을 수치화](#2026-07-22-계속---api-성능-측정-순차-설계의-비용을-수치화)

**운영 관찰** (2개) 배포한 서버가 실제로 어떻게 동작하는가

- [2026-07-26 - 유닉스 프로세스·스레드·메모리 분석 (EC2에서 직접 관찰)](#2026-07-26---유닉스-프로세스스레드메모리-분석-ec2에서-직접-관찰)
- [2026-07-26 (계속) - WireShark HTTP 통신 캡처 (클라이언트-서버 분리)](#2026-07-26-계속---wireshark-http-통신-캡처-클라이언트-서버-분리)

**서비스 개발** (3개) 사용자가 쓸 수 있는 형태로 만들기

- [2026-07-27 - PDF 업로드 지원 (Phase 9)](#2026-07-27---pdf-업로드-지원-phase-9)
- [2026-07-27 (계속) - 프론트엔드 추가 (Phase 10)](#2026-07-27-계속---프론트엔드-추가-phase-10)
- [2026-07-28 - 프론트엔드 대화형 개편](#2026-07-28---프론트엔드-대화형-개편)

---

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

---

## 2026-07-21 (계속) - GitHub Actions CI 구성

### 배경
Phase 8 ②. CI(빌드·테스트)와 CD(배포)를 분리해, 배포 대상이 없는 지금 단계에서 CI부터 구성했다. 목적은 "로컬에서만 되는" 문제를 EC2 이전에 발견하는 것이다.

### 제약 - CI에는 Gemini API 키가 없다
비밀값을 CI에 넣지 않기로 하고, **API 키 없이 검증 가능한 계층이 어디까지인지**를 먼저 확인했다. 실행해본 결과 다음이 키 없이 가능했다.

- `decide_next_step()` 분기 로직: State만 받는 순수 함수
- 그래프 구조(노드·엣지): 컴파일 시 노드 함수를 등록만 하고 호출하지 않음
- `chunk_text()`: 외부 의존 없음
- 스키마 검증(`EvaluationResult`의 0~10 범위 제약)

즉 **Agent 확장에서 가장 회귀가 나기 쉬운 부분(분기 조건, 경로 연결)이 마침 키 없이 검증 가능한 영역**이었다. Phase 7에서 라우팅을 순수 함수로 분리해둔 구조가 여기서도 이득이 됐다.

### 구성
프로젝트에 테스트 코드가 없었으므로(fixture만 존재) pytest를 dev 의존성으로 추가하고 회귀 테스트 22개를 작성했다.

| 파일 | 검증 내용 |
|---|---|
| `tests/test_agent_routing.py` | 0~10점 전 구간 라우팅, 경계값과 상수의 일치, technical_score 범위 제약, 세 경로 연결, **judge에서 END로 가는 빈 경로가 없을 것**, learning_tip → followup 순차 연결, Chain A 구조 |
| `tests/test_loader.py` | source 메타데이터 부착, 짧은/긴 문서 분할, chunk 크기 상한, 빈 문서 처리 |

워크플로는 두 job으로 나눴다.
- `test`: `uv sync` 후 pytest 실행
- `docker-build`: 이미지 빌드 → CUDA 재유입 검사 → 컨테이너 기동 스모크 테스트

### 설계 결정 - CUDA 재유입을 CI에서 자동 검사
①에서 CPU torch 최적화가 **에러 없이 빌드에 성공했지만 실제로는 적용되지 않았던** 전례가 있다. 크기를 재보지 않았다면 놓쳤을 실패였다. 같은 일이 반복되지 않도록, 이미지 안에 `nvidia`/`triton` 패키지가 존재하면 CI를 실패시키는 검사를 넣었다. 사람이 매번 크기를 확인하는 대신 파이프라인이 대신 확인한다.

### 부수 발견 - dev 의존성이 프로덕션 이미지에 포함될 뻔함
pytest를 추가한 뒤 확인해보니 `uv sync`는 기본적으로 dev 그룹을 함께 설치한다. Dockerfile이 `uv sync --frozen`을 쓰고 있어 테스트 도구가 배포 이미지에 들어갈 상황이었다. `--no-dev`를 추가해 제외했다.

### 검증 (CI 단계를 로컬에서 미리 재현)
워크플로를 푸시해서 확인하기 전에, CI가 수행할 세 단계를 로컬에서 그대로 실행해 통과를 확인했다.

| 검사 | 결과 |
|---|---|
| pytest (API 키 없이) | 22 passed |
| 이미지 빌드 + 크기 | 3.79GB (dev 제외 후에도 동일) |
| nvidia/triton 포함 수 | 0 |
| pytest 포함 여부 | 0 (프로덕션 이미지에서 제외됨) |
| 더미 키로 컨테이너 기동 | 16초 만에 헬스체크 200 |

### 결론
1. "CI에 비밀값을 넣지 않는다"는 제약을 먼저 세우고 검증 범위를 정하자, 오히려 회귀에 가장 취약한 부분(분기 로직)이 그 범위 안에 들어왔다. 순수 함수로 분리된 설계가 테스트 용이성으로 이어진 사례
2. 한 번 겪은 실패(조용히 풀린 최적화)를 사람의 주의력이 아니라 CI 검사로 고정했다
3. CI 단계를 로컬에서 먼저 재현해보는 것이, 푸시하고 로그를 기다리며 디버깅하는 것보다 반복 속도가 빨랐다

### 첫 CI 실행 결과 - amd64 검증 통과
푸시 후 첫 실행에서 두 job 모두 통과했다(`test` 50초, `docker-build` 3분 56초, 캐시 0%).

`Verify CPU-only torch` 단계 출력:

| | arm64 (로컬 macOS) | amd64 (CI 러너) |
|---|---|---|
| 이미지 크기 | 3.79GB | **2.7GB** |
| nvidia/triton 패키지 수 | 0 | **0** |

두 가지를 확인했다.

1. **CPU torch 설정이 amd64에서도 유효하다.** 로컬에서는 arm64로만 검증한 상태였고, 아키텍처가 바뀌면 CUDA가 다시 개입할 가능성이 남아 있었는데 그렇지 않았다. EC2 표준 인스턴스(x86_64) 사용에 문제가 없다.
2. **amd64 이미지가 arm64보다 1GB 이상 작다.** 아키텍처별 wheel 크기 차이로 보인다. 2.7GB이므로 EC2 기본 EBS 볼륨(8GB)에도 여유가 있다.

**CI를 EC2보다 먼저 배치한 순서 선택이 실제로 이득을 냈다.** ③(EC2)의 선행 조건이었던 "amd64에서 CPU torch가 동작하는가"가, 별도 작업 없이 CI 첫 실행만으로 해결됐다. 반대 순서였다면 EC2에서 배포하다가 발견했을 문제다.

### Action Item
- Gemini 호출이 필요한 검증(Calibration, RAGAS)은 CI에 넣지 않는다. 실행 비용과 API 한도 문제가 있어 로컬/수동 실행 대상으로 유지
- `actions/checkout@v4`, `astral-sh/setup-uv@v5`의 Node.js 20 deprecation 경고는 실패와 무관하나, 추후 액션 버전 상향 시 함께 정리

---

## 2026-07-22 - EC2 배포: 메모리 측정으로 인스턴스 타입 결정, 디스크 부족 대응

### 배경
Phase 8 ③. 인스턴스 타입을 감으로 고르면 프리티어(`t2.micro`, RAM 1GB)를 선택했다가 배포 후 원인 모를 종료를 겪을 위험이 있었다. **EC2로 가기 전에 로컬 컨테이너 메모리를 먼저 측정**해 근거를 확보하는 순서를 택했다.

### 측정 1 - 컨테이너 메모리 (로컬)
`docker stats`로 0.5초 간격 샘플링하며 요청 3건을 순차 처리.

| 상태 | 메모리 |
|---|---|
| 유휴 (임베딩 모델 로드 완료) | 757 MB |
| 요청 처리 중 피크 | **1.154 GB** |

`t2.micro`는 전체 RAM이 1GB이므로 **피크만으로 이미 초과**한다. OS가 쓰는 200~300MB를 더하면 OOM이 확실했다. 측정하지 않았다면 배포 후에야 발견했을 문제다.

이 측정 중에 요청 3건이 각각 0점 → `fundamentals`, 3점 → `fundamentals`, 10점 → `advanced`로 분기된 것도 확인돼, Agent v3가 컨테이너 환경에서도 정상 동작함이 부수적으로 검증됐다.

### 결정
`t3.small`(RAM 2GB, x86_64, 서울 리전) 채택. 피크 1.15GB + OS 0.3GB = 약 1.5GB로 여유가 있다.

검토했으나 채택하지 않은 대안:
- **swap 설정**: 무료지만 임베딩 모델이 스왑에 걸리면 응답이 크게 느려진다
- **배포 환경만 Gemini Embedding API 사용**: 메모리 200~300MB, 이미지 500MB 수준으로 줄지만, 20문항 평가에서 ko-sroberta(Top-1 100%)가 Gemini(95%)보다 우세했던 검증 결과를 배포용으로 뒤집어야 한다. 트레이드오프가 커서 보류

리전은 서울(ap-northeast-2)로 지정했다. 기본값이 시드니로 잡혀 있었는데, 이후 ⑤ API 성능 측정에서 왕복 지연 150~200ms가 매 요청에 얹히면 "분기별 Gemini 호출 횟수 차이"라는 측정 목적이 오염된다.

### 문제 - EBS 8GB에서 빌드 실패
빌드 중 `no space left on device`로 실패했다. 최종 이미지가 2.7GB이므로 8GB면 충분하다고 판단했으나 **틀린 추정**이었다.

볼륨을 20GB로 확장(인스턴스 중지 없이 온라인 확장 가능)한 뒤 `growpart` + `resize2fs`로 파일시스템까지 확장해 해결. 빌드 완료 후 사용량은 11GB였고, 빌드 전 OS만 있을 때가 2.4GB였으므로 **빌드 과정에만 약 8.6GB가 필요**했던 셈이다.

**이미지 크기와 빌드에 필요한 공간은 전혀 다르다.** 중간 레이어와 빌드 캐시가 최종 이미지의 3배 이상을 차지했다.

### 보안 그룹 설계
- 22번(SSH): 내 IP만 허용
- 8000번(API): 0.0.0.0/0 허용

과제 요구사항인 "외부에서 접근 가능"은 서비스 포트에 해당하며, 관리 포트까지 공개할 이유는 없다. 서비스 포트와 관리 포트의 공개 범위를 분리했다.

### 검증
| 항목 | 결과 |
|---|---|
| 서버 내부 `curl localhost:8000/` | `{"status":"ok"}` |
| 외부(로컬 노트북) `curl <퍼블릭IP>:8000/` | `{"status":"ok"}` |

### 결론
1. 인스턴스 타입 선정에서 **측정이 추측을 대체했다.** 1.154GB라는 수치가 없었다면 프리티어를 골랐다가 실패했을 것이다
2. 반면 디스크는 측정 없이 "이미지 2.7GB니 8GB면 되겠지"라고 추정했다가 실패했다. **같은 배포 작업 안에서 측정한 항목은 성공하고 추정한 항목은 실패한** 대비가 분명하다
3. CI(②)를 EC2보다 먼저 배치한 덕분에 amd64 빌드 검증이 이미 끝나 있어, 이 단계에서는 아키텍처 문제를 겪지 않았다

### Action Item
- `t3.small`은 프리티어가 아니므로 미사용 시 인스턴스 중지. 재시작 시 퍼블릭 IP가 변경되는 점에 유의(Elastic IP 미적용)
- ⑤ API 성능 측정 시 이 인스턴스에서 분기별 지연 시간을 측정하고, ⑥ Unix 분석의 관찰 대상으로 재사용

---

## 2026-07-22 (계속) - CD 구성: 배포 자동화가 기존 설계를 되돌아보게 한 지점들

### 배경
Phase 8 ④. ②에서 만든 CI 파이프라인에 배포 단계를 연결해, main 푸시 시 EC2까지 자동으로 반영되도록 확장했다.

### 구성
`deploy` job을 추가하고 `needs: [test, docker-build]`로 앞의 두 job에 의존시켰다. **테스트가 깨지면 배포가 아예 시작되지 않는다.** CI와 CD를 나눠 만든 목적이 여기서 실현된다.

배포 후에는 별도 단계로 외부에서 헬스체크를 확인한다. `docker compose up -d`가 성공해도 컨테이너가 기동에 실패할 수 있어, "배포 명령이 성공했다"와 "서비스가 정상이다"를 구분했다.

### 발견 1 - 레이어 순서 때문에 매 배포마다 모델을 다시 받을 뻔함
CD를 붙이기 전 Dockerfile을 점검하다가, 임베딩 모델 다운로드(449MB) 레이어가 **코드 COPY 뒤에** 있는 것을 발견했다. 이 순서면 코드를 한 줄만 고쳐도 캐시가 무효화되어 배포할 때마다 모델을 다시 받는다. 수동 배포는 가끔 하니 티가 안 났지만, **자동 배포는 푸시할 때마다 도는 구조**라 그대로 두면 계속 누적될 낭비였다.

`rag.embeddings`를 import하던 것을 모델명 직접 지정으로 바꿔 코드 의존을 끊고, 코드 COPY보다 앞으로 옮겼다.

```
검증 1 (로컬): 코드 1줄 변경 후 재빌드
  - 모델 레이어 CACHED 확인
  - 전체 재빌드 1.6초 (기존에는 모델 재다운로드 포함 수 분)

검증 2 (실제 배포): CD 1회차 vs 2회차 deploy job 소요 시간
  - 1회차(Dockerfile 변경 포함, 모델 재다운로드) 약 10분
  - 2회차(코드/이미지 내용 동일) 45초
```

로컬 1.6초는 캐시가 모두 유효한 이상적 조건이고, 실제 배포 45초에는 SSH 접속·`git pull`·컨테이너 재시작·헬스체크가 포함된다. 레이어 순서 하나를 바꾼 것이 배포 시간에서 13배 차이로 나타났다.

### 발견 2 - CD 도입으로 보안 그룹 설계의 전제가 깨짐
첫 배포가 `dial tcp <IP>:22: i/o timeout`으로 실패했다. ③에서 **22번 포트를 "내 IP만"으로 제한**했는데, GitHub Actions 러너는 당연히 다른 IP에서 접속한다.

수동 배포 시점에는 "SSH는 사람(나)만 쓴다"는 전제가 타당했고, 그래서 서비스 포트(8000, 공개)와 관리 포트(22, 내 IP만)를 분리한 설계가 맞았다. 그런데 **CD는 기계가 SSH로 접속하는 방식**이라 그 전제가 무너졌다.

검토한 선택지:
- **(A) 22번 개방**: 채택. 우분투 AMI는 비밀번호 인증이 비활성이고 키 인증만 허용하므로 `.pem` 없이는 접속 불가. 스캔 트래픽이 유입되는 비용은 감수
- **(B) GitHub Actions IP 대역만 허용**: 대역이 수백 개이고 수시로 변경되어 관리 부담이 큼
- **(C) SSH 대신 AWS SSM Session Manager**: 22번을 열지 않아도 되어 가장 안전하나 IAM 역할 등 추가 구성 필요

실습 범위에서는 (A)를 택했으나, 실무 기준으로는 (C)가 적절하다는 점을 함께 기록해둔다.

### 결론
1. **자동화는 기존 설계의 전제를 검증하는 계기가 된다.** 보안 그룹도 레이어 순서도, 수동으로 가끔 할 때는 문제가 드러나지 않다가 "매번 자동으로 도는" 조건이 되자 둘 다 문제로 떠올랐다
2. 배포 실패가 곧 설계 재검토로 이어진 사례. "왜 막혔는지"를 이해하지 않고 무작정 열었다면, 무엇을 교환했는지 설명할 수 없었을 것이다
3. `needs`로 CI 통과를 배포의 전제 조건으로 묶은 것이 파이프라인의 핵심. 배포 자동화의 목적은 "빠르게 배포하는 것"이 아니라 "검증을 통과한 것만 배포되게 하는 것"에 가깝다

### Action Item
- 22번 개방으로 유입되는 접속 시도는 ⑥ Unix 분석에서 `/var/log/auth.log` 관찰 소재로 활용 가능
- 인스턴스 중지 후 재시작 시 퍼블릭 IP가 바뀌므로 `EC2_HOST` Secret도 함께 갱신해야 CD가 계속 동작함

---

## 2026-07-22 (계속) - API 성능 측정: 순차 설계의 비용을 수치화

### 배경
Phase 8 ⑤(과제 외 자체 추가). `/evaluate-answer`는 technical_score 구간에 따라 실행되는 노드가 달라지고, 그에 따라 Gemini 호출 횟수도 달라진다.

| 구간 | 실행 노드 | Gemini 호출 |
|---|---|---|
| 0~3점 | Judge + Fundamentals | 2회 |
| 4~6점 | Judge + LearningTip + Followup | **3회** |
| 7~10점 | Judge + Advanced | 2회 |

같은 엔드포인트인데 분기에 따라 지연이 달라질 것으로 예상했다. **Agent를 병렬이 아닌 순차로 설계한 대가를 정성적 설명이 아니라 수치로 확인**하는 것이 목적이다.

### 방법
`scripts/measure_api_latency.py` 작성. 구간별 점수가 나오도록 설계한 답변 3개(Phase 7 분기 검증에서 쓰던 것과 동일)를 반복 호출해 중앙값을 집계한다. LLM을 호출하지 않는 `GET /`를 기준선으로 함께 측정해, 순수 네트워크·서버 처리 비중을 분리했다.

로컬(macOS, Docker)과 EC2(t3.small, 서울 리전) 양쪽에서 측정했다. EC2 측정은 로컬 노트북에서 퍼블릭 IP로 호출해, 실제 사용자와 같은 경로를 거치게 했다.

### 결과

| 분기 | Gemini 호출 | 로컬 | EC2 |
|---|---|---|---|
| 기준선 `GET /` | 0회 | 2.4ms | 42.5ms |
| 7~10점 | 2회 | 14.92s | 15.50s |
| 0~3점 | 2회 | 16.78s | 15.64s |
| 4~6점 | **3회** | **22.74s** | **19.79s** |

### 발견 1 - 병목은 서버 연산도 네트워크도 아닌 LLM 대기
기준선이 로컬 2.4ms, EC2 42.5ms다. 전체 응답 시간(15~20초) 대비 **0.2% 미만**이며, 두 환경의 40ms 차이는 결과에 영향을 주지 않는다.

더 중요한 것은 **t3.small이 맥북보다 CPU가 훨씬 약한데도 응답 시간이 느리지 않았다**는 점이다(일부 케이스는 오히려 빨랐다). 응답 시간의 대부분이 Gemini API 응답 대기이므로 서버 연산 성능이 결과를 좌우하지 않는다.

**실무적 함의: 인스턴스 사양을 올려도 응답 시간은 줄지 않는다.** 지연을 줄이려면 LLM 호출 횟수나 호출 방식을 바꿔야 한다. 성능 개선 투자 방향을 정하는 근거가 된다.

### 발견 2 - 순차 설계의 비용은 약 4~6초
3회 호출 분기(4~6점)가 두 환경 모두에서 일관되게 가장 느렸다. 다만 배수는 로컬 1.52배, EC2 1.28배로 갈렸는데, 이는 환경 차이가 아니라 **LLM 응답 시간 자체의 변동성**으로 판단한다(EC2 0~3점 케이스에서 28.02초 이상치가 1건 발생). 표본이 케이스당 2~3회로 작아 배수를 특정 값으로 단정하지 않고, **"Gemini 호출이 1회 늘면 약 4~6초가 추가된다"** 수준으로 정리한다.

이로써 Agent v2에서 내린 설계 결정에 정량적 근거가 붙었다. Learning Tip과 Followup을 병렬이 아닌 순차로 둔 것은 "두 출력이 같은 주제를 겨냥하게" 하기 위함이었고, **그 일관성의 대가가 약 4~6초의 추가 지연**이다. 이전에는 설계 의도만 설명할 수 있었으나, 이제 무엇을 얻고 무엇을 지불했는지 함께 말할 수 있다.

### 결론
1. 병목을 측정 없이 추정했다면 "EC2가 약하니 사양을 올려야 한다"는 잘못된 결론에 도달했을 것이다. 실제로는 서버 성능과 무관했다
2. 순차 설계라는 과거의 결정에 사후적으로 비용을 붙였다. 설계 근거는 있었지만 대가는 몰랐던 상태였다
3. 표본이 작아 배수는 확정하지 않았다. 일관되게 관측된 방향(3회 호출이 가장 느림)만 결론으로 삼는다

### Action Item
- 지연을 줄이려면 병렬화(Learning Tip과 Followup 동시 실행)가 후보이나, 이는 v2에서 의도적으로 배제한 설계다. 일관성을 포기할 만한 가치가 있는지는 별도 판단 필요
- 스트리밍 응답을 도입하면 체감 지연을 줄일 수 있다(총 시간은 동일하나 첫 토큰까지의 시간이 짧아짐). 초기 명세서에서 Future Work로 분류했던 항목
- ⑥ Unix 분석에서 이 대기 구간을 관찰 대상으로 사용. 응답 시간의 99% 이상이 I/O 대기이므로 프로세스 상태 관찰에 적합한 소재

---

## 2026-07-26 - 유닉스 프로세스·스레드·메모리 분석 (EC2에서 직접 관찰)

### 배경
Phase 8 ⑥(부트캠프 과제). ⑤에서 "응답 시간의 대부분이 LLM 대기(I/O 바운드)"임을 시간으로 측정했으니, 그 대기 순간에 프로세스가 실제로 어떤 상태인지를 리눅스 표준 도구로 눈으로 확인한다. EC2(실제 리눅스)에서 진행. 컨테이너 이미지가 slim이라 `ps`가 없어, `/proc` 파일시스템과 호스트의 `top -H`를 주 도구로 사용(이 자체가 경량 이미지의 트레이드오프를 보여주는 소재).

### 환경
`t3.small` (vCPU 2, RAM 1.9GB, **swap 0B**). 평상시 컨테이너 메모리 약 575~719MB, free 메모리 약 211MB로 여유가 얇음.

### 관찰 1 - 프로세스/스레드 구조 (평상시)
`/proc/1/status`: `State: S (sleeping)`, `VmRSS: 557MB`, `Threads: 9`. `top -H`로 본 9개 스레드 전원 S, CPU 91~100% idle. 스레드 9개의 정체는 uvicorn 워커들 + jemalloc(메모리 할당자) 1개. 모든 스레드의 RES가 557840으로 동일한데, 이는 **스레드가 프로세스의 메모리를 공유**하기 때문(프로세스 vs 스레드의 핵심 차이를 육안 확인). `st`(steal time) 8.7% 관측: 공유 물리 서버 위 VM이라 다른 인스턴스에 CPU를 뺏긴 비율.

### 관찰 2 - 단일 요청 처리의 3국면
4~6점 케이스(Gemini 3회 호출) 요청을 보내며 `top -H`를 1초 간격으로 스냅샷.

| 국면 | Threads | State | CPU | 메모리 | 해석 |
|---|---|---|---|---|---|
| 평상시 | 9 | S | idle 100% | 557MB | 대기 |
| I/O 대기 | 18 | **D** | wa 35% | 725MB | 인터럽트 불가 대기(메모리 확보 등) |
| 연산 | 20 | **R** | 80% | 967MB | 응답 파싱·Pydantic 변환·다음 프롬프트 조립 |
| 종료 후 | 20 | S | idle 100% | 979MB | 다시 대기, 스레드는 안 줄어듦 |

세 가지를 확인했다.
1. **스레드가 9→20으로 늘고 처리 후에도 유지됨**: 매 요청마다 스레드를 생성·소멸하지 않으려는 스레드 풀. "안 줄이는 게 아니라 재사용하려고 남긴다".
2. **⑤의 결론 정밀화**: 전체 시간의 대부분은 S(대기)가 맞으나, 그 사이에 짧은 R(CPU 스파이크, 응답 파싱)과 D(I/O 대기)가 낀다. 순수 네트워크 대기만은 아니다. 시간 측정(⑤)만으로는 "대기"까지, 상태 관찰(⑥)을 해야 "대기 중 무슨 일이 있었는지"까지 보인다.
3. **메모리 피크 967MB**: 요청 1건이 컨테이너 한도(1.86GB)의 절반을 순간적으로 사용. swap이 0이라 동시 요청 시 OOM 위험을 예상.

### 관찰 3 - 동시 요청 부하 (가설이 반증됨)
요청 5개를 동시 발사. **예상: 메모리가 겹쳐 폭증하거나 순차 처리로 계단식 지연.**

결과: 5개가 15.5 / 17.6 / 18.3 / 19.3 / 22.9초로 **거의 동시에 완료**(순차였다면 15/30/45/60/75초 계단식이어야 함). 메모리는 589MB에서 거의 안 오름. `OOMKilled: false, RestartCount: 0`.

**가설 반증 → 더 정확한 결론**: vCPU 2개짜리 서버가 5개 요청을 동시 처리했다. CPU가 2개인데 5개가 가능한 이유는, 대부분의 시간이 CPU 연산이 아니라 네트워크 대기(S)라 CPU가 놀면서 5개의 "기다림"을 동시에 떠안을 수 있기 때문이다. **I/O 바운드 작업은 동시성으로 확장이 잘 된다**는 원리를 서버에서 실측. 967MB 피크가 5배로 겹치지 않은 것도, 파싱 스파이크의 시점이 서로 어긋났기 때문.

이는 `kb/async_sync.md`에 직접 작성한 "I/O 바운드에서 비동기가 유리하다"는 내용을, 그 KB를 서빙하는 서버에서 증명한 사례.

### 한계
5개 동시 시 가장 느린 요청이 22.9초로 단일(약 20초)보다 늘었다. 응답 파싱 순간엔 vCPU 2개를 두고 경합이 생기므로 완전 공짜는 아니다. 요청이 수십 개로 늘면 이 경합이 병목이 될 것.

### 결론
1. "swap 0 + 얇은 여유 메모리라 동시 요청 시 OOM"이라는 추정을 실측이 정정했다. 이 워크로드는 대기 중심이라 메모리를 거의 쓰지 않아 안전했다. ⑤⑥ 내내 반복된 "추정을 측정이 정정한다" 패턴의 또 다른 사례.
2. 프로세스/스레드/메모리 세 축과 R/S/D 상태 전이를 실제 서버에서 관찰했고, 예상을 뒤집는 발견(I/O 바운드의 동시성 확장)까지 나왔다.
3. macOS에는 없는 `/proc` 기반 조회를 EC2에서 수행. 배포를 먼저 한 것이 이 과제의 전제 조건이었음.

### Action Item (Phase 8 ⑦로 이어짐)
- WireShark로 클라이언트(로컬)-서버(EC2) HTTP 통신을 캡처해, 22.9초 중 네트워크 구간과 서버 처리 구간을 구분
- OOMKilled=false는 이 워크로드 기준. CPU 바운드 작업이거나 요청이 수십 개면 결과가 달라질 수 있음을 보고서에 명시

### 제출 보고서
이 관찰을 완결된 과제 보고서로 정리: [과제 1. 유닉스 프로세스·스레드·메모리 분석](reports/01_unix_process_analysis.md)

---

## 2026-07-26 (계속) - WireShark HTTP 통신 캡처 (클라이언트-서버 분리)

### 배경
Phase 8 ⑦(부트캠프 과제). 클라이언트(로컬 맥북, 사설 IP 192.168.0.16)와 서버(EC2, 54.180.96.17)가 물리적으로 다른 컴퓨터라 과제 조건이 자연히 충족됨. `host 54.180.96.17` 캡처 필터로 EC2와의 트래픽만 격리. `POST /evaluate-answer`(0~3점 케이스, 약 17초) 요청 1건의 전 과정을 13개 패킷으로 캡처.

### 관찰 1 - 요청 하나의 전체 생애 (13패킷)

| 패킷 | 시각 | 내용 |
|---|---|---|
| 1~3 | 0.000~0.009 | TCP 3-way handshake (SYN → SYN,ACK → ACK) |
| 4 | 0.009 | HTTP POST 요청 (JSON, 평문) |
| 5 | 0.016 | 서버의 요청 수신 ACK |
| (침묵) | 0.016~17.206 | **약 17.19초간 데이터 패킷 없음** |
| 6~8 | 17.206 | HTTP 200 OK 응답 (JSON, 평문) + TCP 재전송 |
| 9~13 | 17.206~17.214 | ACK, FIN (연결 종료) |

### 관찰 2 - ⑤⑥⑦ 세 각도가 같은 결론으로 수렴
패킷 5(0.016초)와 패킷 6(17.206초) 사이 **17.19초의 네트워크 침묵**이 핵심. handshake는 9ms로 순식간이었고, 응답 대기 구간에는 데이터가 흐르지 않았다. 세 계층의 관찰이 하나로 만난다.

- ⑤ (시간): 응답이 약 17초 걸린다
- ⑥ (프로세스 상태): 그 시간 동안 서버 프로세스는 S(대기)
- ⑦ (패킷): 그 시간 동안 네트워크에 데이터가 없다

결론: 지연의 원인은 네트워크도 서버 연산도 아닌 **Gemini API 응답 대기**. 네트워크가 병목이었다면 이 17초 동안 패킷이 계속 오갔을 것이나, 조용하다는 것이 곧 "네트워크는 할 일이 없었다"는 증거.

### 관찰 3 - HTTP 평문 노출 (과제 핵심 시연)
Follow HTTP Stream으로 요청·응답 전체가 평문으로 노출됨을 확인.
- 요청: `POST /evaluate-answer`, `Host`, `User-Agent: curl/8.4.0`, `Content-Type`, 그리고 body의 question/answer JSON
- 응답: `server: uvicorn`, `content-length: 2143`, 그리고 technical_score/improvements/concept_explanation 등 전체 JSON

한글이 ASCII 뷰에서 `.`으로 표시된 것은 암호화가 아니라 인코딩 표시 문제(UTF-8 뷰로 바꾸면 원문 노출)임을 확인. 즉 HTTP는 중간에서 캡처한 제3자가 요청·응답 내용을 그대로 읽을 수 있으며, 로그인 요청이었다면 자격증명이 노출됐을 것. HTTPS(TLS)가 필요한 이유를 실측으로 확인.

### 관찰 4 - TCP 재전송 (신뢰성 메커니즘 실동작)
응답 데이터 전송 중 `[TCP Retransmission]`(패킷 8)과 `[TCP Dup ACK]`(패킷 10) 발생. 패킷 유실/순서 어긋남을 TCP가 재전송으로 복구했으며, 애플리케이션 코드는 이를 전혀 인지하지 못함. "TCP는 신뢰성 있는 전송"이라는 개념이 실제 캡처에 나타난 사례.

### 결론
1. 서로 다른 세 도구(시간 측정, /proc 상태, 패킷 캡처)가 "지연 = LLM 대기"라는 동일 결론으로 수렴. 계층을 바꿔가며 같은 사실을 교차 검증한 셈
2. HTTP 평문 노출을 육안으로 확인해 HTTPS의 필요성을 실측 근거로 확보
3. 배포(EC2)가 선행됐기에 "클라이언트와 서버가 다른 컴퓨터" 조건이 자연히 성립. Phase 8 단계들이 서로의 전제가 됨

### 부수 기록 - IP 변경으로 인한 CD 단절
⑥ 진행을 위해 EC2를 중지·재시작하면서 퍼블릭 IP가 바뀌었고, GitHub Secrets의 `EC2_HOST`가 옛 IP를 가리켜 CD가 `dial tcp ***:22: i/o timeout`으로 실패. Secret을 새 IP로 갱신 후 정상화. 인프라 상태 변화(IP 변경)가 배포 파이프라인을 끊는 실제 사례로, 실무에서는 Elastic IP나 도메인으로 해소함.

### 추가 캡처 - 스마트폰(외부 기기) → 노트북 로컬 서버
"클라이언트가 서버와 다른 컴퓨터" 조건을 두 번째 방식으로도 충족: 스마트폰(172.16.30.253)을 같은 Wi-Fi에서 노트북 로컬 서버(172.16.30.225)에 접속시켜 전 흐름을 캡처. 새로 관측된 것:
- **파일 업로드의 TCP 세그먼트 분할**: `POST /documents`(PDF) 구간에서 1514바이트 패킷이 연속 전송되고 `[TCP PDU reassembled]`로 재조립됨. JSON 요청(작음)과 대비되는 파일 전송의 특성.
- **TCP Keep-Alive**: 평가 요청의 긴 LLM 대기 중 연결 유지 신호 관측.
- **다중 세션**: 세 엔드포인트 요청이 각각 다른 클라이언트 포트(56252, 56256, 56258...)로 독립 관리됨.
- 노트북 자신에서 노트북 서버로 보낸 요청은 loopback으로 처리되어 en0 캡처에 안 잡힘을 확인(동시 접속 캡처를 한 인터페이스로 잡기 어려운 이유). 동시성은 과제 1의 부하 테스트에서 프로세스 레벨로 이미 검증했으므로 추가 시도는 생략.

### 제출 보고서
두 캡처(EC2 원격, 폰 근거리)를 완결된 과제 보고서로 정리: [과제 2. WireShark HTTP 통신 캡처·분석](reports/02_wireshark_http_capture.md)

### Action Item
- 캡처 파일(`.pcapng`) 저장 완료 (IP 포함되어 `.gitignore` 처리, 커밋하지 않음)
- HTTPS 대비 실험(공개 사이트 TLS 캡처는 암호문만 노출)은 여유 시 추가
- 재시작해도 IP가 유지되도록 Elastic IP 적용 검토 (CD 안정화 목적)

---

## 2026-07-27 - PDF 업로드 지원 (Phase 9)

### 배경
User Docs가 `.md`/`.txt`만 지원했으나, 실사용 이력서·포트폴리오는 대부분 PDF다. 지원 형식을 넓혀 제품 가치를 높인다.

### 설계 - 라이브러리를 교체 가능하게 격리
`pypdf`(순수 파이썬, 가벼움)를 선택. pdfplumber는 표·레이아웃 추출이 정밀하지만 의존성이 무겁고, 우리가 다룰 이력서는 텍스트 위주라 과함. pdf2htmlEX는 PDF를 HTML로 시각 재현하는 도구라 "텍스트만 추출"이라는 목적과 안 맞고 pip 설치도 안 됨.

교체 비용을 줄이기 위해 **PDF 파싱을 `load_pdf_file` 한 함수로 격리**하고, `load_document`가 확장자로 분기하도록 설계.
- `api/documents.py`는 `load_document`만 호출 (파싱 라이브러리를 모름)
- 나중에 pdfplumber로 바꾼다면 `load_pdf_file` 몸통 3~4줄만 수정, 호출부·chunk·검색은 불변
- 반환을 순수 문자열로 통일해 뒷단이 라이브러리에 의존하지 않게 함

### 예외 처리
텍스트가 전혀 없는 PDF(스캔 이미지 등)는 빈 chunk 리스트가 되어 조용히 빈 인덱싱이 될 수 있음. 이를 422로 명시적 거부하도록 처리(빈 상태를 성공으로 위장하지 않음).

### 검증 - 한글 깨짐은 우리 코드 문제가 아니었음
1. 처음 `cupsfilter`(macOS 기본)로 만든 테스트 PDF에서 한글이 `૑৔ ࢲ۱`처럼 깨져 나옴. 영어는 정상. 원인은 추출 로직이 아니라 **cupsfilter가 한글 폰트를 제대로 임베딩하지 못한 불량 PDF**였음. 입력이 이미 깨져 있었던 것.
2. reportlab로 한글 폰트(AppleGothic)를 명시해 정상 PDF를 만들자 한글·영어 모두 정확히 추출됨. (reportlab은 검증 전용이라 `uv pip install`로 임시 설치 후 제거, lock 미오염 확인)
3. 회귀 테스트: 확장자 분기 로직을 monkeypatch로 검증(`.pdf`/`.PDF`→pdf 로더, `.md`/`.txt`→text 로더). PDF 파싱 자체는 라이브러리 책임이므로 우리가 책임지는 "분기"만 테스트. 전체 24개 통과.
4. **end-to-end**: 실제 서버에 한글 이력서 PDF를 `POST /documents`로 업로드(`chunks_added: 1`), 이어서 `POST /generate-question`이 그 PDF 내용(JWT, FastAPI)을 정확히 반영한 질문을 생성. PDF에서 뽑은 텍스트가 임베딩→검색→생성까지 온전히 흐름을 확인. md/txt와 완전히 동등하게 작동.

### 결론
1. "라이브러리 교체가 번거로울까"라는 우려를, 파싱을 한 함수로 격리하는 설계로 해소. 3단계에서 확인한 "경계를 한 곳에 몰면 교체가 국소적이 된다"는 원리의 적용 사례
2. 한글 깨짐을 "우리 코드 버그"로 단정하지 않고 입력 PDF를 재검토해 원인이 테스트 도구(cupsfilter)에 있었음을 확인. Judge Calibration 때와 같은 "도구 탓하기 전에 입력 데이터부터 확인" 패턴

### Action Item
- 스캔 이미지 PDF까지 지원하려면 OCR(예: pytesseract)이 필요하나, 이미지·의존성 부담이 커 현재 범위 밖으로 둠

---

## 2026-07-27 (계속) - 프론트엔드 추가 (Phase 10)

### 배경
지금까지 서비스를 보여주려면 curl 세 번을 순서대로 쳐야 했다. 업로드 → 질문 생성 → 답변 평가가 이미 다 동작하는데도, 그 흐름이 화면으로 이어지지 않아 "무엇을 만들었는지" 전달되지 않는 상태였다. Agent 3분기(개념 설명/학습 팁/심화 질문)도 JSON 필드로만 구분돼 있어 차이가 드러나지 않았다.

### 설계 - SPA를 의도적으로 배제
순수 HTML/CSS/JS 단일 페이지(`static/`)로 만들고 FastAPI가 직접 서빙하도록 했다. React를 쓰지 않은 이유는 이렇다.
- 화면이 하나뿐이라 라우팅·상태관리 라이브러리가 할 일이 없다
- 별도 프론트 서버를 띄우면 origin이 갈려 **CORS 설정이 필요**해지는데, 같은 서버가 서빙하면 그 문제가 아예 생기지 않는다
- 빌드 단계(node_modules, 번들러)가 생기면 Dockerfile과 CI가 모두 복잡해진다. 이미지 크기를 3.79GB까지 줄여둔 작업과도 상충한다

즉 "가벼워서" 고른 게 아니라, **SPA를 쓸 때 따라오는 비용(CORS·빌드·이미지)이 이 프로젝트에서는 대가 없이 발생**하기 때문에 배제했다.

### 엔드포인트 충돌과 그 파급
`GET /`를 데모 페이지로 쓰려 했는데 이미 헬스체크가 그 자리를 쓰고 있었다. 헬스체크를 `/health`로 분리했는데, 이때 함께 고쳐야 할 곳이 **세 군데** 있었다.
- `docker-compose.yml`의 healthcheck
- `.github/workflows/ci.yml`의 스모크 테스트와 배포 후 헬스체크
- `scripts/measure_api_latency.py`의 기준선 측정 대상

한 줄짜리 경로 변경이 인프라 설정 세 곳으로 번진 사례다. 엔드포인트를 여러 계층이 참조하고 있으면 변경 비용이 코드 밖에서 발생한다.

### 발견 - structured output을 안 쓰는 노드에서만 서식이 샜다
화면에 붙이자마자 꼬리질문 자리에 `**[꼬리 질문]**` 같은 마크다운 군더더기가 섞여 나오는 게 보였다. 확인해보니 **followup_node만 structured output을 쓰지 않는 유일한 노드**였다. 나머지 노드는 Pydantic 스키마로 필드가 고정돼 있어 서식이 낄 자리가 없었지만, followup은 자유 텍스트를 그대로 받고 있었다.

Phase 2에서 structured output을 도입한 이유(Gemini 자유 출력에 마크다운·설명이 섞여 API 계약과 안 맞음)가 **정확히 같은 형태로 재발**한 것이다. 당시엔 JSON 응답만 보고 있어 드러나지 않았고, 사람이 읽는 화면에 올리고 나서야 보였다.

대응은 두 겹으로 했다.
1. **예방**: `FOLLOWUP_PROMPT`에 마크다운·라벨·따옴표 없이 순수 텍스트로만 출력하도록 명시
2. **방어**: 프론트에 `cleanText()`를 두어 `**`, `#`, `[꼬리 질문]` 라벨, 양끝 따옴표를 제거

프롬프트 지시는 LLM이 지킬 수도 안 지킬 수도 있어 100% 보장이 아니다. 자유 텍스트를 받는 이상 표시 계층에서 한 번 더 막는 게 맞다고 판단했다.

### UI 버그 - 긴 텍스트와 겹친 선택 표시
선택된 질문에 오른쪽 상단 절대 위치로 "선택됨" 라벨(`::after`)을 띄웠는데, 질문이 길어 여러 줄이 되면 마지막 줄 텍스트와 겹쳤다. 짧은 질문으로 테스트해서 놓친 케이스다. 왼쪽 고정 위치의 체크 아이콘(`::before`)으로 바꾸고 그만큼 `padding-left`를 줘서, 텍스트 길이와 무관하게 겹치지 않도록 했다.

### 검증 절차에서 배운 것 - 캐시 때문에 "안 고쳐졌다"고 오판할 뻔함
수정 후 브라우저를 껐다 켜도 반영이 안 보였다. 코드를 다시 의심하기 전에 시크릿 창으로 열어보니 정상이었다. **브라우저 캐시**였다. 프론트 작업에서는 "고쳤는데 안 보인다"의 원인이 코드가 아니라 캐시일 수 있으므로, 코드를 되돌리기 전에 캐시부터 배제해야 한다. 백엔드 작업에서 서버 재시작을 먼저 확인하는 것과 같은 종류의 절차다.

### 결론
1. **화면을 붙이는 것 자체가 검증 수단이었다.** followup의 서식 오염은 API 응답만 볼 때는 몇 주 동안 드러나지 않다가, 사람이 읽는 형태로 렌더링하자마자 즉시 보였다. 출력 형태를 바꾸면 안 보이던 결함이 드러난다
2. **structured output을 쓰는 노드와 안 쓰는 노드의 차이가 실제 품질 차이로 나타났다.** 스키마로 고정된 출력은 문제가 없었고, 자유 텍스트인 곳에서만 오염이 발생. Phase 2의 결정이 왜 옳았는지 사후에 확인된 셈
3. 기술 선택을 "가벼운 걸 쓰자"가 아니라 **"이 프로젝트에서 그 비용이 회수되는가"**로 판단. SPA의 비용(CORS·빌드·이미지 크기)이 화면 하나짜리 데모에서는 회수되지 않는다고 보고 배제

### Action Item
- 멀티턴 루프를 붙이면 이 화면은 대화형 UI로 확장해야 한다. 현재 3단계 카드 구조는 단발성 흐름에 맞춰져 있어, 턴이 쌓이는 형태로 바뀌면 레이아웃 재설계가 필요하다

---

## 2026-07-27 (계속) - 멀티턴 면접 루프 (Phase 11)

### 배경 - "그럴 거면 LCEL로도 되지 않나"
Phase 7에서 Agent를 3분기로 확장했지만, 그래프는 여전히 한 방향으로 흘러 끝났다. 조건부 분기와 순차 실행은 LCEL의 `RunnableBranch`로도 표현할 수 있다. 즉 **지금까지의 구조만으로는 LangGraph를 쓸 이유를 설명할 수 없었다.** 명세서에도 이 반문을 Future Work 최우선 항목으로 적어뒀었다.

사이클은 이 반문에 답하는 유일한 구조다. 코칭을 받은 사용자가 다시 답하고, 그 답을 또 채점하는 흐름은 그래프가 되돌아가야 성립한다.

### 설계 - 사이클의 연결점을 interrupt로 만들었다
문제는 사이클 중간에 **사람의 입력을 기다려야** 한다는 것이다. 그래프가 혼자 돌면 되는 구조가 아니다.

`await_answer` 노드에서 LangGraph의 `interrupt()`를 호출하도록 했다. 이 함수는 그래프 실행을 그 자리에서 멈추고, 지금까지의 State를 checkpointer에 저장한 뒤 제어권을 API로 돌려준다. 사용자의 답변이 도착하면 `Command(resume=답변)`으로 재개하고, `interrupt()`가 그 값을 반환하며 이어서 실행된다.

```
retrieval → judge → 분기 → followup/advanced → decide_continue
    ↑                                              ├ "end" → END
    └──────── await_answer (여기서 멈춤) ←─────────┘
```

`await_answer → retrieval`이 사이클이다. 질문이 꼬리질문·심화질문으로 바뀌었으므로 context부터 새로 검색해야 한다(원래 질문의 context를 재사용하면 초점이 어긋난다).

**주의할 점**: interrupt로 멈춘 노드는 재개 시 처음부터 다시 실행되고 `interrupt()` 지점에서 저장된 값을 돌려받는다. 그래서 interrupt 앞에 부작용이 있는 코드를 두면 두 번 실행된다. 여기서는 직전 턴을 요약하는 순수 계산만 두었다.

### 설계 판단 두 가지
**1. 0~3점은 루프에서 제외했다.** fundamentals 노드는 개념을 설명할 뿐 다음 질문을 만들지 않는다. 기술적으로는 "다시 답해보세요"라고 되물을 수 있지만, 개념 자체를 모르는 사람에게 같은 주제를 재질문하는 건 코칭이 아니라 압박이다. 설명을 주고 세션을 마치는 쪽이 맞다고 판단했다. 분기 설계 때와 같은 기준(점수대마다 필요한 것이 다르다)의 연장이다.

**2. 기존 단발성 그래프를 남겼다.** `build_interview_agent_graph()`를 고치지 않고 `build_interview_session_graph()`를 따로 만들었다. `/evaluate-answer`와 Calibration 스크립트들이 그대로 동작해야 하기 때문이다. 노드는 전부 공유하고 배선만 다르다. LCEL 코드를 지우지 않고 보존한 것과 같은 방식이다.

### 검증 - LLM 없이 사이클을 증명하는 테스트
루프가 도는지 확인하려면 여러 턴을 돌려야 하는데, 매번 Gemini를 호출하면 CI에서 못 돌리고 비용도 든다. **노드를 전부 가짜로 갈아끼우고 루프 메커니즘만 검증하는 테스트 10개**를 작성했다.

사이클의 증거로 삼은 것은 **judge 노드의 호출 횟수**다. 한 세션에서 답변을 두 번 제출했을 때 judge가 2회, retrieval도 2회 호출됐다면 실행이 실제로 되돌아간 것이다. 이 방식으로 다음을 전부 API 키 없이 확인했다.
- interrupt로 멈추고 resume으로 재개되는가 (`snapshot.next == ("await_answer",)`)
- 재개 후 질문이 교체되고 이전 턴이 history에 쌓이는가
- MAX_TURNS(3)에서 멈추는가
- 0~3점 경로는 루프하지 않는가
- thread_id가 다른 두 세션의 State가 섞이지 않는가

CI test job이 "키가 필요 없는 계층만 검증"하도록 설계돼 있었는데, 이번 기능이 마침 그 범위에 딱 들어왔다. 회귀가 나기 쉬운 부분(라우팅·상태 전이)이 키 없이 검증 가능한 계층에 몰려 있다는 패턴이 Phase 7에 이어 또 확인됐다.

### 실측 - 한 세션에서 세 경로가 모두 실행됐다
실제 Gemini로 API를 돌린 결과, 턴마다 점수가 달라지며 서로 다른 경로를 탔다.

| 턴 | technical_score | 실행 경로 |
|---|---|---|
| 1 | 8 | advanced (심화 질문) |
| 2 | 9 | advanced (더 깊은 심화 질문) |
| 3 | 10 | 종료 (max_turns_reached) |

질문이 "JWT란 무엇인가" → "LocalStorage와 Cookie 저장의 취약점" → "HttpOnly 쿠키의 Cross-Origin 전송"으로 **점점 깊어졌다.** 심화 질문이 직전 답변을 전제로 생성되기 때문에, 턴이 쌓일수록 좁고 구체적인 영역으로 들어간다.

또 다른 실행에서는 1턴 6점(followup) → 2턴 8점(advanced) → 3턴 2점(fundamentals)으로 **한 세션 안에서 세 경로가 전부 나왔다.** 3턴에서 점수가 급락한 것은 검증 스크립트가 미리 정해둔 답변을 순서대로 넣는 방식이라, 질문이 동적으로 바뀌자 **동문서답**이 됐기 때문이다. 버그가 아니라 Judge가 질문과 답변의 불일치를 정확히 잡아낸 사례다. 멀티턴에서는 질문이 고정되지 않으므로 답변을 미리 준비하는 검증 방식 자체가 성립하지 않는다는 것도 함께 확인했다.

### 발견 - checkpoint 직렬화 기본값이 "허용하되 경고"였다
루프를 돌리자 `Deserializing unregistered type rag.schemas.EvaluationResult from checkpoint. This will be blocked in a future version.`이라는 경고가 나왔다. State에 Pydantic 객체가 들어가는데, LangGraph 기본 설정이 **모든 타입을 허용하되 경고만 띄우는** 상태였던 것이다.

동작에는 문제가 없었지만 두 가지 이유로 명시적 허용으로 바꿨다.
1. 경고가 "향후 버전에서 차단된다"고 못박고 있어, 방치하면 라이브러리 업그레이드 시 깨진다
2. 보안상으로도 명시적 허용이 맞다. checkpoint 저장소에 접근 가능한 공격자가 임의 객체를 넣어 역직렬화 시점에 코드를 실행시키는 경로를 막아준다

`JsonPlusSerializer(allowed_msgpack_modules=[...])`로 우리 스키마 4개만 등록했다. **경고를 끄는 게 아니라 원인을 없애는 방향**을 택했다.

### 부수 발견 - 배포 검증이 헬스체크가 아니었다
CI를 확인하다 배포 검증 단계가 `/`(데모 HTML)를 헬스체크로 쓰고 있는 것을 발견했다. Phase 10에서 `/`를 HTML 페이지로 바꾸고 헬스체크를 `/health`로 분리했는데, docker-build job만 갱신되고 deploy job이 누락돼 있었다. 정적 HTML은 앱 상태와 무관하게 응답할 수 있어 헬스체크로 부적합하다. `/health`로 정정.

Phase 10 로그에 "엔드포인트 변경이 인프라 설정 세 곳으로 번졌다"고 적었는데, 실제로는 **네 곳이었고 그중 하나를 놓쳤던 것**이다. 변경 파급 범위를 스스로 센 숫자도 틀릴 수 있다는 사례.

### 결론
1. **사이클이 LangGraph 채택 근거를 완성했다.** 조건부 분기까지는 LCEL로도 가능했지만, 되돌아가는 흐름과 실행 중간에 멈췄다 재개하는 동작은 LCEL로 만들 수 없다. Future Work 최우선으로 적어둔 항목을 해소
2. **사람을 기다리는 그래프**라는 형태를 다뤘다. 자동으로 끝까지 도는 파이프라인과 달리, 상태를 저장하고 외부 입력을 기다렸다가 재개하는 구조(human-in-the-loop)
3. LLM을 부르지 않고 루프를 검증하는 방법을 찾은 것이 실용적으로 가장 컸다. 가짜 노드로 갈아끼우고 호출 횟수를 세는 방식이라 CI에서 매번 돌아간다

### Action Item
- **세션이 서버 메모리에만 있다.** `MemorySaver`라서 컨테이너를 재시작하면 진행 중이던 세션이 사라지고, 인스턴스를 늘리면 세션이 인스턴스에 묶인다. 실사용 규모로 가려면 `SqliteSaver`나 Postgres 기반 checkpointer로 교체해야 한다. 지금은 단일 인스턴스 데모라 감수
- 종료 조건에 "개선 없음"(직전 턴 대비 점수가 오르지 않으면 중단)을 넣을지는 보류. history에 점수가 쌓이므로 구현은 어렵지 않으나, 몇 점 차이를 "개선 없음"으로 볼지 기준을 정할 근거가 아직 없다

---

## 2026-07-28 - 프론트엔드 대화형 개편

### 배경
멀티턴 API는 동작하는데 화면이 Phase 10의 단발 구조(답변 1회 → 평가 1회)라, 루프를 만들어놓고도 사람이 쓸 수 없는 상태였다.

### 설계에서 가장 신경 쓴 것 - 질문이 두 군데 보이면 안 된다
단발 화면에서는 꼬리질문·심화질문을 **코칭 결과의 일부**로 보여줬다. 그런데 멀티턴에서는 그 질문이 곧 **다음에 답해야 할 질문**이 된다. 코칭 블록 안에도 있고 입력창 위에도 있으면, 같은 문장이 화면에 두 번 나와 어디에 답하는 건지 헷갈린다.

그래서 역할을 갈랐다.
- 코칭 블록: 학습 팁이면 topic·이유·추천 학습, 심화 질문이면 **출제 의도만**
- 입력창 위: 다음에 답할 질문 **본문**

같은 데이터를 어디에 놓느냐가 아니라, **화면에서 그것이 무엇으로 읽히는가**가 기준이었다.

### 구조
턴이 끝날 때마다 타임라인에 카드가 쌓인다. 각 카드에는 그 턴의 질문·내 답변 말풍선, 점수 뱃지, 평가와 코칭이 함께 남아서 대화가 어떻게 진행됐는지 위로 스크롤해 되짚을 수 있다.

세션 진행 중에는 질문 변경을 막았다. 그래프가 그 세션의 맥락(checkpointer의 State)을 들고 있어서, 중간에 다른 질문으로 갈아타면 이어지던 흐름과 화면이 어긋난다. 바꾸려면 재시작해야 한다는 것을 안내로 알린다.

### 검증에서 겪은 것 - 트랜지션 때문에 멀쩡한 색을 버그로 볼 뻔했다
라이트/다크 색상을 확인하려고 테마를 바꾼 직후 `getComputedStyle`로 읽었더니, **라이트 모드인데 body 배경과 텍스트만 다크 값**으로 나왔다. 흰 카드 위에 밝은 회색 글씨라 안 보이는 상태로 읽혔다.

원인은 CSS `transition: background-color 0.3s, color 0.3s`였다. 전환 애니메이션이 진행 중인 순간의 중간값을 읽은 것이다. 트랜지션이 걸린 속성(body 배경·색)만 옛 값이고, 트랜지션이 없는 속성(카드 배경)은 이미 새 값이라 **일부만 안 바뀐 것처럼 보였다.**

`* { transition: none }`을 임시로 주입하고 다시 재니 두 테마 모두 정상이었다. Phase 10에서 브라우저 캐시 때문에 "안 고쳐졌다"고 오판할 뻔한 것과 같은 종류다. **측정 도구가 만들어낸 현상을 코드 결함으로 착각하지 않으려면, 이상한 값을 봤을 때 측정 조건부터 의심해야 한다.**

### 브라우저 end-to-end 검증
- 3턴 완주: 9점 → 10점 → 9점, 각 턴의 질문이 사이클로 교체되는 것 확인
- 심화 질문이 직전 답변을 전제로 좁혀지는 것 확인 ("I/O 바운드에 유리하다고 했는데, 그렇다면 CPU 바운드 작업은?")
- 0~3점 경로: FastAPI 질문에 JWT 답변을 넣어 동문서답을 만들자 0점 → 개념 설명 → 루프 없이 종료. 설계대로 동작
- 재시작 후 타임라인·입력창·뱃지 초기화
- 레이아웃 겹침 없음(턴 번호와 점수 뱃지, 말풍선 상하 간격), 라이트/다크 양쪽 색상 정상

### 디자인 개편 중 만든 회귀 - display:flex가 hidden을 무력화했다
미니멀 디자인으로 다듬으면서 "답변 제출 버튼을 오른쪽 아래로" 옮기려고 `#answer-area`에 `display: flex`를 넣었다. 그러자 **세션이 끝나도 입력창과 버튼이 사라지지 않는** 버그가 생겼다.

원인은 `hidden` 속성의 동작 방식이다. HTML의 `hidden`은 마법이 아니라 브라우저 기본 스타일시트의 `[hidden] { display: none }` 규칙으로 동작한다. 그런데 작성자 스타일시트(우리 CSS)에서 `display: flex`를 명시하면 **우선순위에서 작성자 스타일이 이겨** hidden이 무시된다.

`[hidden] { display: none !important; }`를 전역에 못박아 해결했다. 숨김은 레이아웃 규칙보다 항상 우선해야 한다.

이 버그가 화면에서는 "채점 결과가 내 답변보다 위에 있다"는 이상한 증상으로 보였다. 실제로는 순서가 뒤집힌 게 아니라, 사라졌어야 할 입력창이 결과 아래 그대로 남아 있었던 것이다. **증상과 원인이 다른 층에 있던 사례**이고, 레이아웃 속성 하나를 바꾼 것이 상태 전환 로직을 깨뜨릴 수 있다는 것도 함께 확인했다.

### 결론
1. **API가 되는 것과 사람이 쓸 수 있는 것은 다르다.** 루프는 이미 동작하고 있었지만 화면이 단발이라 아무도 쓸 수 없었다
2. 같은 데이터라도 화면에서 맡는 역할이 달라지면 배치도 달라져야 한다. 꼬리질문이 "코칭 결과"에서 "다음 질문"으로 역할이 바뀌자 놓일 자리도 바뀌었다
3. 이상한 측정값을 만나면 코드보다 측정 조건을 먼저 의심하는 편이 빨랐다 (트랜지션, 캐시 모두 같은 패턴)
- pypdf로 추출이 부족한 복잡한 레이아웃 PDF를 만나면 `load_pdf_file`만 pdfplumber로 교체(설계상 국소 수정으로 가능)
---

## 2026-07-31 - 채점 루브릭 도입과 측정 도구 재설계 (Phase 12)

### 배경
멘토링에서 "사용자가 왜 그 점수인지 납득하지 못한다"는 지적을 받았다. 루브릭·감점 근거·레벨 판정을 넣기로 하고, 효과를 Calibration Set으로 검증하려 했다.

### 1차 시도 - 프롬프트를 고칠수록 점수가 나빠졌다
루브릭과 감점 방식(만점에서 차감)을 넣고 측정했더니 오히려 떨어졌다.

| 회차 | 프롬프트 | 정확도 |
|---|---|---|
| 1 | 루브릭 없음 (baseline) | 88.2% |
| 2 | 루브릭 + 감점 방식 | 82.4% |
| 3 | 감점 제외 규칙 추가 | 88.2% |
| 4 | technical 감점 조건 축소 | 76.5% |

원인은 **만점에서 깎게 하니 LLM이 깎을 이유를 적극적으로 찾았다.**였다. good 케이스가 전부 10점에서 8점으로 내려앉았다. 반대로 "억지로 깎지 마라"를 넣자 이번엔 bad 케이스가 위로 샜다. 한쪽을 누르면 반대쪽이 올라오는 상태가 반복됐다.

### 진짜 문제
케이스별 점수 변동 폭을 재보니 **평균 1.8점, 최대 4점**이었다. Case 16은 네 번의 측정에서 `9 → 6 → 8 → 10`을 오갔다.

17개 표본에서는 케이스 하나가 뒤집히면 5.9%p가 움직인다. 즉 **88.2%와 82.4%의 차이가 프롬프트 효과인지 노이즈인지 구분할 수 없는 상태**에서 프롬프트를 세 번 연속 바꿨다. 네 번의 측정 중 무엇이 진짜였는지 말할 수 없게 됐다.

측정 도구가 변화보다 거칠면 어떤 개선도 증명할 수 없다. 임베딩 비교에서 5문항 결론이 20문항에서 뒤집혔던 것과 같은 종류의 실패다.

### Calibration Set v2 설계
표본을 늘리면서 두 가지를 함께 바꿨다.

1. **기대 범위를 분기 경계에 정렬**: 기존 세트는 `average`의 기대치가 `[1,4]`, `[2,5]`, `[3,6]`으로 제각각이었다. `[1,4]`면 1점도 통과인데 1점은 실제로 fundamentals 경로로 간다. 점수는 맞았다고 나오지만 엉뚱한 코칭이 나가는 상태. 그래서 bad `[0,3]`, average `[4,6]`, good `[7,10]`으로 통일해 **분기 경계(4점, 7점)와 맞췄다.**
2. **주제 확대**: 5개 → 13개. KB 18개 문서 중 5개 주제만 검증하고 있었다.

이렇게 하니 **"점수가 맞았는가"가 아니라 "올바른 코칭이 나갔는가"를 잴 수 있게 됐다.** 

### 발견
새 세트로 측정하니 **51.2%**가 나왔다. 그런데 실패 21건이 **전부 한 방향**이었다. 무작위였다면 양쪽으로 흩어졌을 텐데 하나도 예외 없이 점수가 위로 샜다.

| 레벨 | 기대 | 실제 평균 |
|---|---|---|
| bad | 0~3 | 4.0 |
| average | 4~6 | 8.6 |
| good | 7~10 | 10.0 |

원인은 Judge가 아니라 **내가 만든 케이스**였다. `average`로 라벨을 붙인 답변들이 "짧고 얕지만 틀린 내용은 없는" 것이었는데, 프롬프트에는 "짧다고 감점하지 말라"가 명시돼 있다. **10점이 나온 것이 프롬프트대로 동작한 결과였다.**

Day 4에 "Judge 실패의 원인이 Judge가 아니라 Calibration Set의 설계 결함"이었던 것과 정확히 같은 상황이다. 라벨 이름(`average`)에 대한 직관과 채점 기준이 어긋나 있었다.

`bad`와 `average`에 **실제로 틀린 내용**을 넣어 재작성했다. "모른다"가 아니라 "잘못 알고 있다"로 바꾼 것이다.

| 레벨 | 수정 전 | 수정 후 |
|---|---|---|
| bad | 짧고 부실하지만 틀리진 않음 | 핵심 개념 자체를 잘못 알고 있음 |
| average | 맞지만 짧음 | 일부는 맞고 일부는 틀림 |

### 결과
케이스만 고쳤을 뿐인데 **51.2% → 90.7%**가 됐다. 레벨별 점수 분포도 기대 구간 안으로 들어왔다.

```
bad     평균 2.6  (기대 0~3)
average 평균 5.5  (기대 4~6)
good    평균 10.0 (기대 7~10)
```

**Judge는 처음부터 제대로 채점하고 있었다.** 잘못된 것은 측정 도구였다.

### 배운 점
1. **측정 도구의 해상도가 변화의 크기보다 거칠면, 어떤 개선도 증명할 수 없다.** 변동 폭을 모른 채 프롬프트를 네 번 바꾼 것이 이번 시행착오의 핵심이었다
2. **실패가 한 방향으로만 쏠리면 대상이 아니라 기준을 의심해야 한다.** 무작위 오류라면 양방향으로 흩어진다
3. 같은 함정(Calibration Set 설계 결함)에 두 번 빠졌다. 첫 번째는 동일 답변에 다른 기대치를 준 것이었고, 이번엔 라벨 이름에 대한 직관이 채점 기준과 어긋난 것이었다. **"기대치를 정하는 사람"의 감각도 검증 대상이다**

### 루브릭 기여도 검증 - 원래 질문에 답하기
측정 도구가 준비된 뒤, Phase 12의 원래 질문("루브릭이 채점 편차를 줄이는가")을 확인했다. 프롬프트에서 루브릭과 감점 지침만 걷어내고 동일한 44개 세트로 측정했다.

| 조건 | 경로 정확도 |
|---|---|
| 루브릭 있음 (3회) | 93.2%, 88.6%, 93.2% |
| 루브릭 없음 (2회) | 77.3%, 86.4% |

평균만 보면 약 10%p 차이지만, **변동 폭이 5%p이고 루브릭 없는 쪽 두 값의 차이만도 9.1%p**다. 노이즈 범위와 겹치므로 "루브릭이 정확도를 올렸다"고 말할 수 없다.

레벨별 평균 점수를 보면 더 분명하다.

| 레벨 | 루브릭 있음 | 루브릭 없음 | 차이 |
|---|---|---|---|
| bad | 2.2 | 2.0 | -0.2 |
| average | 5.5 | 5.6 | +0.1 |
| good | 10.0 | 10.0 | 0.0 |

**거의 같다.** 루브릭을 넣든 빼든 Judge는 같은 점수를 낸다.

### 비교 도중 저지른 실수 - 다른 세트로 비교했다
처음 비교할 때 루브릭 있는 쪽은 43개 세트, 없는 쪽은 44개 세트(CORS bad 케이스 추가 후)로 측정했다. 케이스 인덱스가 한 칸씩 밀려 레벨별 집계가 어긋났고, 루브릭 있을 때 good 평균이 6.3으로 나왔다. 직전 측정에서 10.0이었던 값이다.

**A/B 비교는 한쪽만 바꿔야 한다**는 기본을 어긴 것이다. 결과가 직전 관측과 모순될 때 그것을 발견으로 받아들이지 않고 측정 조건부터 확인한 것이 이번엔 맞았다.

### 결론
1. **루브릭은 정확도를 올리지 않았다.** 처음 세운 가설은 틀렸다. 채점 편차의 원인은 기준 부재가 아니라 LLM 자체의 변동으로 보인다
2. **그래도 루브릭과 감점 근거는 유지한다.** 정확도와 무관하게 사용자가 "왜 이 점수인지" 알 수 있게 되었고, 그것이 멘토가 지적한 원래 문제였다. 목표가 둘이었는데 하나만 달성한 셈이다
3. **이번 작업의 실질적 성과는 측정 도구였다.** 표본 17개에서 44개로, 기준을  점수 범위에서 코칭 경로로 바꾸고, **변동 폭 약 5%p를 알아냈다.** 앞으로 이보다 작은 차이는 노이즈로 판정할 수 있다
4. 역설적으로 **"효과가 없었다"고 자신 있게 말할 수 있게 된 것 자체**가 도구가 좋아졌다는 증거다. v1에서는 네 번의 측정이 오르내렸지만 무엇도 판정하지 못했다

### Action Item
- 모범답안 제공은 이번에 넣지 않았다. KB 밖 내용을 생성하면 환각이 되므로 RAGAS 재측정을 전제로 별도 진행할 것
- 감점 합계와 점수의 일치율은 `check_deduction_consistency.py`로 측정할 수 있게 해뒀으나 아직 실행하지 않았다
- 경계선(4점, 7점) 부근 케이스가 반복적으로 넘나든다. 이는 루브릭으로 해결되지 않았으므로, 필요하다면 분기 경계 자체를 재검토하거나 경계 부근에서 두 번 채점해 다수결하는 방식을 검토할 수 있다
