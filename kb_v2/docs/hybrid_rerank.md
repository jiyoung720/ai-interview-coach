---
topic: hybrid_rerank
area: retrieval
difficulty: intermediate
sources:
  - title: "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods (Cormack et al., 2009)"
    url: https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf
  - title: "Apache Lucene - BM25Similarity"
    url: https://lucene.apache.org/core/10_3_1/core/org/apache/lucene/search/similarities/BM25Similarity.html
  - title: "OpenSearch - Normalization processor (점수 정규화와 결합)"
    url: https://docs.opensearch.org/latest/search-plugins/search-pipelines/normalization-processor/
  - title: "Sentence Transformers - Retrieve & Re-Rank"
    url: https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html
last_reviewed: 2026-11-23
---
# 하이브리드 검색과 reranking

## 키워드 검색과 벡터 검색
BM25는 질문의 단어가 문서에 얼마나 자주 나오는지(같은 단어가 반복될수록 효과는 줄어든다), 그 단어가 전체 문서에서 얼마나 드문지, 문서 길이를 함께 반영하는 키워드 기반 점수다. 키워드 검색은 정확한 용어, 고유명사, 에러 코드처럼 표현이 그대로 일치해야 하는 검색에 강하다. 단, 질문과 문서의 단어가 같은 토큰으로 색인돼 있어야 일치한다. 벡터 검색은 단어가 달라도 의미가 비슷한 문서를 찾는 데 강하지만, 학습에서 드물었던 용어는 놓칠 수 있다.

## 하이브리드 검색
하이브리드 검색은 키워드 검색과 벡터 검색의 결과를 합쳐 서로의 약점을 보완한다. 두 검색의 점수는 척도가 달라 그대로 더하기 어렵기 때문에, 점수를 같은 범위로 정규화한 뒤 가중합하거나 각 결과 목록의 순위를 합치는 방법을 쓴다. 순위를 합치는 방법의 예로, Reciprocal Rank Fusion(RRF)은 각 결과 목록에서 문서의 순위 r에 대해 1/(k + r)을 더해 최종 순위를 정한다. 여기서 k는 낮은 순위 문서의 영향을 조절하는 상수로, 검색해 오는 문서 수(top-k)와는 다른 값이다. RRF 점수는 순위만으로 계산하므로, 점수가 높다고 그 문서에 실제로 답이 들어 있다는 보장은 없다.

## reranking
reranking은 1차 검색이 가져온 후보를 더 정교한 모델로 다시 평가해 상위 결과의 품질을 높이려는 단계다. 흔한 구현은 질문과 후보 문서를 한 번에 입력해 관련도를 계산하는 cross-encoder다. 질문과 문서를 따로 임베딩해 비교하는 bi-encoder보다 대체로 더 정교하게 관련도를 판단하지만, 효과는 데이터와 모델에 따라 다르다. 후보마다 모델을 돌려야 해서 비용과 지연이 크므로, 큰 문서 집합에서는 보통 1차 검색의 상위 후보에만 적용한다. 후보가 적다면 전부 다시 평가할 수도 있다.
