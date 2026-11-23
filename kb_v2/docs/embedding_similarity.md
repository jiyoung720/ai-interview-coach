---
topic: embedding_similarity
area: retrieval
difficulty: basic
sources:
  - title: "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks (Reimers & Gurevych, 2019)"
    url: https://arxiv.org/abs/1908.10084
  - title: "Efficient and robust approximate nearest neighbor search using HNSW graphs (Malkov & Yashunin, 2016)"
    url: https://arxiv.org/abs/1603.09320
  - title: "Gemini API - Embeddings"
    url: https://ai.google.dev/gemini-api/docs/embeddings
last_reviewed: 2026-11-23
---
# 임베딩과 유사도

## 임베딩이란
임베딩은 텍스트를 고정된 길이의 숫자 벡터로 바꾼 것이다. 의미가 비슷한 문장은 벡터 공간에서 가까운 위치에 놓이도록 학습된다. 그래서 키워드가 겹치지 않아도 의미가 비슷하면 검색할 수 있다. 문장 단위 임베딩 모델은 문장 쌍의 유사도를 학습 목표로 삼아 만들어진다.

## 코사인 유사도와 L2 거리
코사인 유사도는 두 벡터 사이 각도의 코사인 값으로, 벡터의 크기와 관계없이 방향이 얼마나 비슷한지를 잰다. L2 거리는 두 벡터 끝점 사이의 직선거리라서 벡터의 크기에도 영향을 받는다. 벡터를 길이 1로 정규화하면 코사인 유사도와 L2 거리는 같은 순위를 만든다. 텍스트 임베딩은 방향이 의미를 담는다고 보고 코사인을 쓰는 경우가 많다.

## 근사 최근접 이웃 검색
문서가 많아지면 모든 벡터와 거리를 계산하는 정확한 검색은 느려진다. 그래서 정확도를 조금 양보하고 속도를 얻는 근사 최근접 이웃(ANN) 검색을 쓴다. HNSW는 여러 층의 그래프를 만들어 위층에서 대략적인 위치를 찾고 아래층으로 내려가며 이웃을 좁히는 ANN 방식이다.

## 한계
임베딩 모델이 학습 중에 보지 못한 전문용어나 드문 단어는 의미를 제대로 구분하지 못할 수 있다. 이 경우 문서를 고쳐도 검색이 나아지지 않고, 임베딩 모델을 바꾸거나 키워드 검색을 함께 써야 한다. 거리 값의 절대 크기는 임베딩 모델마다 다르므로, 모델을 바꾸면 거리 임계값도 다시 정해야 한다.
