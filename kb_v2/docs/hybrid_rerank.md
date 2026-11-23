---
topic: hybrid_rerank
area: retrieval
difficulty: intermediate
sources:
  - title: "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods (Cormack et al., 2009)"
    url: https://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf
  - title: "The Probabilistic Relevance Framework: BM25 and Beyond (Robertson & Zaragoza, 2009)"
    url: https://dl.acm.org/doi/10.1561/1500000019
  - title: "Sentence Transformers - Cross-Encoders"
    url: https://www.sbert.net/
last_reviewed: 2026-11-23
---
# 하이브리드 검색과 reranking

## BM25와 벡터 검색
BM25는 질문의 단어가 문서에 얼마나 자주 나오는지와 그 단어가 전체 문서에서 얼마나 드문지를 함께 반영하는 키워드 기반 점수다. 그래서 정확한 용어, 고유명사, 드문 전문용어를 찾는 데 강하다. 벡터 검색은 단어가 달라도 의미가 비슷한 문서를 찾는 데 강하지만, 학습에서 드물었던 용어는 놓칠 수 있다.

## 하이브리드 검색
하이브리드 검색은 키워드 검색과 벡터 검색의 결과를 합쳐 서로의 약점을 보완한다. 두 검색의 점수는 척도가 달라 그대로 더하기 어렵기 때문에, 점수 대신 순위를 합치는 방법을 자주 쓴다. Reciprocal Rank Fusion(RRF)은 각 검색 결과에서 문서의 순위 r에 대해 1/(k + r)을 더해 최종 순위를 정한다. RRF 점수는 순위만으로 계산하므로, 점수가 높다고 해서 그 문서에 실제로 답이 들어 있다는 보장은 없다.

## reranking
reranking은 1차 검색이 가져온 후보 몇십 개를 더 정교한 모델로 다시 정렬하는 단계다. bi-encoder는 질문과 문서를 따로 임베딩해 빠르게 비교하고, cross-encoder는 질문과 문서를 한 번에 입력해 관련도를 직접 계산한다. cross-encoder는 더 정확하지만 후보마다 모델을 돌려야 해서 느리므로, 전체 문서가 아니라 1차 후보에만 적용한다.
