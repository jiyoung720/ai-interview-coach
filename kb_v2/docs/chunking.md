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
  - title: "LangChain - ParentDocumentRetriever (API reference)"
    url: https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever
  - title: "LangChain - Recursive text splitter"
    url: https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter
  - title: "Is Semantic Chunking Worth the Computational Cost? (Qu et al., 2024)"
    url: https://arxiv.org/abs/2410.13070
last_reviewed: 2026-11-24
---
# Chunking 전략

## chunking이란
chunking은 긴 문서를 검색 단위가 되는 작은 조각(chunk)으로 나누는 작업이다. RAG는 질문과 관련된 조각을 찾아 LLM의 컨텍스트에 넣기 때문에, 어떻게 나누느냐가 검색 품질과 답변 품질에 함께 영향을 준다. 임베딩 모델에는 최대 입력 길이가 있고, 이를 넘으면 모델이나 API 설정에 따라 넘는 부분이 잘리거나 오류가 나므로, 조각은 그 길이 안에 들어와야 한다. chunk 크기의 효과는 문서 종류, 검색 방식, 가져오는 조각 수에 따라 달라서 일반적인 경향으로 이해하고 실험으로 확인해야 한다.

## chunk 크기의 트레이드오프
chunk를 크게 하면 한 조각에 앞뒤 문맥을 더 많이 보존할 수 있다. 반면 한 조각에 여러 주제가 섞이면 임베딩이 흐려져 관련 조각을 정확히 찾는 검색 품질이 떨어질 수 있다. 같은 개수(top-k)의 조각을 그대로 프롬프트에 넣는다면, 조각이 클수록 입력 토큰이 늘어 비용과 지연이 커질 수 있다. chunk가 너무 작으면 하나의 설명이 여러 조각으로 흩어질 수 있다.

## overlap
overlap은 경계 근처의 내용이 두 조각으로 나뉘어, 한 조각만으로는 문맥이 부족해지는 문제를 줄이려는 설정이다. 이웃한 조각이 일부 내용을 겹쳐 갖게 해서, 경계에 걸친 문장이 한쪽 조각에라도 이어서 남을 가능성을 높인다. 대가로 중복 텍스트가 늘어 저장 공간과 인덱싱 비용이 커지고, 비슷한 조각이 검색 결과에 함께 나올 수 있다.

## 의미 단위로 나누기
고정 길이로 자르는 대신 문단·제목·문장 경계를 존중해 나누면 근거가 덜 흩어질 수 있다. 기준은 크기 자체가 아니라, 질문 하나에 답할 근거가 한 조각 안에 모이는 단위다. 흔한 구현은 문단, 줄, 단어처럼 큰 단위부터 작은 단위 순으로 구분자를 바꿔 가며 정한 크기 안에 들어올 때까지 나누는 방식이고, 구현에 따라 문장 경계를 구분자로 추가하기도 한다. 이웃 문장의 임베딩 유사도가 크게 떨어지는 지점에서 나누는 semantic chunking도 있다. 다만 문장마다 임베딩 비용이 들고 임계값에 따라 결과가 달라지며, 고정 길이 분할보다 검색 성능이 늘 좋지는 않다는 실험 결과도 있다.

## 검색 단위와 전달 단위 나누기
작은 조각은 검색 정밀도에, 큰 조각은 문맥 보존에 유리하다. 그래서 작은 조각으로 검색하고, 찾은 조각이 속한 더 큰 조각이나 원문 구간을 LLM에 넘기는 방식(parent-child)을 쓰기도 한다. 검색은 작은 조각으로 정밀하게 하면서 답변에는 넓은 문맥을 주려는 절충이다. 대신 조각 사이의 관계를 따로 저장하고 관리해야 한다. 또 큰 조각을 넘기면 LLM 입력이 길어지거나, 같은 입력 길이 안에 담을 수 있는 근거 수가 줄 수 있다.
