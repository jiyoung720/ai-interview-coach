---
topic: rag_pipeline
area: rag
difficulty: basic
sources:
  - title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al., 2020)"
    url: https://arxiv.org/abs/2005.11401
  - title: "Seven Failure Points When Engineering a Retrieval Augmented Generation System (Barnett et al., 2024)"
    url: https://arxiv.org/abs/2401.05856
last_reviewed: 2026-11-23
---
# RAG 파이프라인과 실패 유형

## RAG의 구성
RAG(Retrieval-Augmented Generation)는 질문과 관련된 문서를 먼저 검색하고, 그 문서를 컨텍스트로 넣어 LLM이 답을 생성하게 하는 방식이다. 인덱싱 단계에서는 문서를 chunk로 나누고 임베딩해 저장한다. 질의 단계에서는 질문을 임베딩해 가까운 chunk를 찾고, 찾은 chunk와 질문을 프롬프트에 넣어 생성한다.

## 파인튜닝 대신 RAG를 쓰는 이유
RAG는 모델 가중치를 바꾸지 않고 검색 대상 문서만 바꿔 최신 정보나 사용자별 자료를 반영할 수 있다. 또 답이 어떤 문서에서 나왔는지 출처를 보여줄 수 있어 검증이 쉽다.

## 실패 유형
검색 실패는 답이 있는 문서를 찾지 못하거나 관련 없는 문서를 상위로 가져오는 경우다. 생성 이탈은 올바른 문서를 찾았는데도 LLM이 컨텍스트에 없는 내용을 덧붙이거나 컨텍스트와 다르게 답하는 경우다. 검색 실패와 생성 이탈은 원인이 달라서, 검색 지표와 생성 충실도를 따로 측정해야 어디를 고칠지 알 수 있다.

## 범위 밖 질문
벡터 검색은 질문과 아무리 먼 문서라도 상위 k개를 항상 돌려준다. 그래서 지식베이스에 답이 없는 질문에도 엉뚱한 문서가 근거로 붙을 수 있다. 1순위 문서와의 거리가 임계값보다 멀면 근거가 없다고 보고 답을 보류하는 식으로 범위 밖 질문을 걸러낸다.
