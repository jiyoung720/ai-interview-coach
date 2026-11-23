---
topic: chunking
area: retrieval
difficulty: basic
sources:
  - title: "LangChain - Text splitters"
    url: https://docs.langchain.com/oss/python/integrations/splitters
  - title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al., 2020)"
    url: https://arxiv.org/abs/2005.11401
  - title: "Chunking 설정별 RAG 성능 통제 실험 (arXiv 2601.14123)"
    url: https://arxiv.org/abs/2601.14123
last_reviewed: 2026-11-23
---
# Chunking 전략

## chunking이란
chunking은 긴 문서를 검색 단위가 되는 작은 조각(chunk)으로 나누는 작업이다. RAG는 질문과 관련된 조각을 찾아 LLM의 컨텍스트에 넣기 때문에, 어떻게 나누느냐가 검색 품질과 답변 품질에 함께 영향을 준다. chunk 크기의 효과는 문서 종류, 검색 방식, 가져오는 조각 수에 따라 달라서 일반적인 경향으로 이해하고 실험으로 확인해야 한다.

## chunk 크기의 트레이드오프
chunk를 크게 하면 한 조각에 앞뒤 문맥을 더 많이 보존할 수 있다. 반면 한 조각에 여러 주제가 섞이면 임베딩이 흐려져 관련 조각을 정확히 찾는 검색 품질이 떨어질 수 있다. 같은 개수(top-k)의 조각을 그대로 프롬프트에 넣는다면, 조각이 클수록 입력 토큰이 늘어 비용과 지연이 커질 수 있다. chunk가 너무 작으면 하나의 설명이 여러 조각으로 흩어질 수 있다.

## overlap
overlap은 경계 근처의 내용이 조각 사이에서 잘려 사라지는 손실을 줄이려는 설정이다. 이웃한 조각이 일부 내용을 겹쳐 갖게 해서, 경계에 걸친 문장이 한쪽 조각에라도 이어서 남을 가능성을 높인다. 대가로 중복 텍스트가 늘어 저장 공간과 인덱싱 비용이 커지고, 비슷한 조각이 검색 결과에 함께 나올 수 있다.

## 의미 단위로 나누기
고정 길이로 자르는 대신 문단·제목·문장 경계를 존중해 나누면 근거가 덜 흩어질 수 있다. 기준은 크기 자체가 아니라, 질문 하나에 답할 근거가 한 조각 안에 모이는 단위다.
