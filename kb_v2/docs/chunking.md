---
topic: chunking
area: retrieval
difficulty: basic
sources:
  - title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al., 2020)"
    url: https://arxiv.org/abs/2005.11401
  - title: "LangChain - Text splitters"
    url: https://python.langchain.com/docs/concepts/text_splitters/
last_reviewed: 2026-11-23
---
# Chunking 전략

## chunking이란
chunking은 긴 문서를 검색 단위가 되는 작은 조각(chunk)으로 나누는 작업이다. RAG는 질문과 가까운 chunk를 찾아 LLM의 컨텍스트에 넣기 때문에, 어떻게 나누느냐가 검색 품질과 답변 품질을 함께 좌우한다.

## chunk 크기의 트레이드오프
chunk가 크면 한 chunk 안에 문맥이 더 많이 담겨, 답에 필요한 앞뒤 설명이 끊기지 않는다. 반면 chunk가 크면 관련 없는 내용이 함께 섞여 임베딩이 흐려지고 검색 정밀도가 떨어진다. 또 chunk가 크면 컨텍스트에 넣는 토큰이 늘어 비용과 지연이 커진다. chunk가 너무 작으면 문장이 중간에 잘려 근거가 여러 chunk로 흩어진다.

## overlap
overlap은 이웃한 chunk가 일부 내용을 겹쳐 갖게 하는 설정이다. 경계에서 잘린 문장이나 설명이 양쪽 chunk 어디에서든 온전히 검색되도록 하려는 것이다. overlap을 늘리면 경계 손실은 줄지만 저장하는 중복 텍스트와 인덱스 크기가 늘어난다.

## 의미 단위로 나누기
고정 길이로 자르는 대신 문단·제목·문장 경계를 존중해 나누면 근거가 덜 흩어진다. 기준은 크기 자체가 아니라, 질문 하나에 답할 근거가 한 chunk 안에 모이는 단위다. 나열형 문서는 하위 주제별로 쪼갤수록, 비교형 문서는 비교 대상을 한 chunk에 함께 둘수록 검색이 좋아지는 경우가 많다.
