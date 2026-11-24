---
topic: rag_pipeline
area: rag
difficulty: basic
sources:
  - title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al., 2020)"
    url: https://arxiv.org/abs/2005.11401
  - title: "Seven Failure Points When Engineering a Retrieval Augmented Generation System (Barnett et al., 2024)"
    url: https://arxiv.org/abs/2401.05856
  - title: "Chroma - Query and Get"
    url: https://docs.trychroma.com/docs/querying-collections/query-and-get
  - title: "Chroma - Metadata Filtering"
    url: https://docs.trychroma.com/docs/querying-collections/metadata-filtering
  - title: "Chroma - Update Data"
    url: https://docs.trychroma.com/docs/collections/update-data
  - title: "Chroma - Delete Data"
    url: https://docs.trychroma.com/docs/collections/delete-data
  - title: "Anthropic - Reduce hallucinations"
    url: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations
last_reviewed: 2026-11-24
---
# RAG 파이프라인과 실패 유형

## RAG의 구성
RAG(Retrieval-Augmented Generation)는 질문과 관련된 자료를 먼저 검색하고, 그 자료를 근거로 LLM이 답을 생성하게 하는 방식이다. 인덱싱 단계에서는 문서를 검색할 수 있는 형태로 준비한다. 벡터 검색이라면 문서를 chunk로 나누고 임베딩해 저장하고, 키워드 검색이라면 단어 색인을 만든다. 질의 단계에서는 먼저 질문과 관련된 자료를 인덱스에서 검색한다. 그다음 검색한 자료를 근거로 프롬프트에 넣어 LLM이 답을 생성하게 한다.

## 인덱스 갱신
인덱싱은 한 번으로 끝나지 않는다. 문서가 추가되거나 본문이 바뀌면 바뀐 문서의 조각을 다시 만들어 임베딩하고 인덱스에 반영한다. 문서가 삭제되면 그 문서의 조각을 인덱스에서 지운다. 메타데이터만 바뀌었다면 조각을 다시 만들지 않고 해당 필드만 갱신할 수 있다. 바뀐 문서만 다시 처리하는 증분 인덱싱을 쓰면 전체를 다시 만드는 비용을 줄일 수 있다.

## 파인튜닝 대신 RAG를 쓰는 이유
RAG는 모델 가중치를 바꾸지 않고 검색 대상 자료만 바꿔 최신 정보나 사용자별 자료를 반영할 수 있다. 또 답에 쓰인 자료의 출처를 보여줄 수 있지만, 그 자료가 어떤 주장을 실제로 뒷받침하는지는 따로 확인해야 한다.

## 답이 틀렸을 때 원인 찾기
답이 틀렸을 때는 정답 근거가 검색 결과에 있었는지, 그 근거가 실제로 생성에 들어간 최종 컨텍스트에 포함됐는지, 답변이 그 근거를 따랐는지를 차례로 확인한다. 검색 실패는 답이 있는 자료를 찾지 못하거나 관련 없는 자료를 상위로 가져오는 경우다. 검색 결과에는 있었지만 컨텍스트 길이 제한이나 후처리 때문에 최종 컨텍스트에서 빠지는 경우도 있다. 생성 이탈은 필요한 근거가 최종 컨텍스트에 들어 있었는데도 LLM이 근거에 없는 내용을 덧붙이거나 근거와 다르게 답하는 경우다.

## 범위 밖 질문
벡터 검색은 조건에 맞는 후보가 있으면, 질문과 관련이 적어도 가장 가까운 순서로 최대 k개를 돌려준다. 그래서 지식베이스에 답이 없는 질문에도 엉뚱한 자료가 근거로 붙을 수 있다. 1순위 후보와의 거리가 정한 기준보다 멀면 근거가 없다고 보고 답을 보류하는 방식은 범위 밖 질문을 거르는 간단한 휴리스틱이다. 문서 종류나 날짜 같은 메타데이터로 검색 범위를 미리 제한하면 엉뚱한 후보를 줄일 수 있다.

## 근거 제한 프롬프트
생성 단계에서는 제공한 자료 안에서만 답하게 하거나, 자료에 답이 없으면 모른다고 말하게 하거나, 답하기 전에 관련 구절을 먼저 뽑게 하거나, 답변의 주장마다 근거 자료를 인용하게 하는 지시를 쓸 수 있다. 이런 지시는 근거에 없는 내용을 지어낼 가능성을 줄일 수 있지만 없애지는 못한다. 그래서 인용한 문장이 실제 자료에 있는지 코드로 확인하고, 그 문장이 답변의 주장을 실제로 뒷받침하는지는 따로 평가한다.
