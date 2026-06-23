# 실험 로그

## 2026-06-23 — Semantic Retrieval 검증

### 가설
임베딩 기반 검색이 키워드 일치가 아니라 의미로 작동하는지 확인.

### 방법
`scripts/test_semantic_retrieval.py` — "JWT", "인증" 단어를 전혀 포함하지 않은 쿼리("로그인한 사용자를 어떻게 식별하나요?")로 인증 관련 chunk와 무관한(pytest/CI) chunk를 구분할 수 있는지 테스트.

### 결과
- 무관한 chunk(pytest/CI)는 정확히 최하위로 밀려남 → 최소한의 의미 구분은 작동.
- 다만 여러 주제가 섞인 긴 chunk(README 전체)가, 주제 하나로 깨끗한 짧은 chunk(doc_auth)보다 더 높은 유사도를 받는 경우가 있었음.

### 결론
**Chunk는 주제 하나당 짧고 포커스 있게 유지해야 한다.** 혼합 주제 chunk는 의도와 다르게 부풀려진 유사도 점수를 받을 수 있음. Interview KB(`jwt.md`, `fastapi.md` 등) 작성 시 이 원칙 적용.
