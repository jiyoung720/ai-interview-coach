---
topic: embedding_similarity
area: retrieval
difficulty: basic
sources:
  - title: "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks (Reimers & Gurevych, 2019)"
    url: https://arxiv.org/abs/1908.10084
  - title: "Efficient and robust approximate nearest neighbor search using HNSW graphs (Malkov & Yashunin, 2016)"
    url: https://arxiv.org/abs/1603.09320
  - title: "Faiss - MetricType and distances"
    url: https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances
  - title: "BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models (Thakur et al., 2021)"
    url: https://arxiv.org/abs/2104.08663
last_reviewed: 2026-11-23
---
# 임베딩과 유사도

## 임베딩이란
임베딩은 텍스트를 고정된 길이의 숫자 벡터로 바꾼 것이다. 의미가 비슷한 문장은 벡터 공간에서 가까운 위치에 놓이도록 학습된다. 그래서 키워드가 겹치지 않아도 의미가 비슷하면 검색할 수 있다. 예를 들어 Sentence-BERT는 문장 쌍을 이용해 문장 단위 임베딩을 학습한다.

## 코사인 유사도와 L2 거리
코사인 유사도는 두 벡터 사이 각도의 코사인 값으로, 벡터의 크기와 관계없이 방향이 얼마나 비슷한지를 잰다. L2 거리는 두 벡터 끝점 사이의 직선거리라서 벡터의 크기에도 영향을 받는다. 0이 아닌 벡터를 모두 길이 1로 정규화하면, 코사인 유사도가 높은 순서와 L2 거리가 가까운 순서가 같아진다. 텍스트 임베딩은 방향이 의미를 담는다고 보고 코사인을 쓰는 경우가 많다.

## 근사 최근접 이웃 검색
문서가 많아지면 모든 벡터와 거리를 계산하는 정확한 검색은 느려진다. 그래서 정확도를 조금 양보하고 속도를 얻는 근사 최근접 이웃(ANN) 검색을 쓴다. HNSW는 여러 층의 그래프를 만들어 위층에서 대략적인 위치를 찾고 아래층으로 내려가며 이웃을 좁히는 ANN 방식이다. 근사 검색이라 정확한 검색과 반환 결과가 조금 다를 수 있다.

## 검색이 엉뚱한 문서를 가져올 때
먼저 상위 후보 조각을 직접 확인해 원인을 진단한다. 원인에는 임베딩 모델이 드문 전문용어를 잘 구분하지 못하는 경우, 문서에 용어의 정의나 약어 표기가 빠진 경우, 조각 경계에서 설명이 잘린 경우, 질문의 표현이 문서와 다른 경우 등이 있다. 원인에 맞게 문서나 질의 표현 보강, 조각 크기 조정, 키워드 검색 결합, 임베딩 모델 교체 중 알맞은 방법을 고른다.

## 거리 임계값과 모델 교체
거리 값의 분포는 임베딩 모델마다 다르다. 그래서 거리 임계값으로 답을 보류하는 시스템에서 임베딩 모델을 바꾸면 임계값도 다시 검증해야 한다.
