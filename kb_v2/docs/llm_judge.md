---
topic: llm_judge
area: evaluation
difficulty: intermediate
sources:
  - title: "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (Zheng et al., 2023)"
    url: https://arxiv.org/abs/2306.05685
  - title: "Large Language Models are not Fair Evaluators (Wang et al., 2023)"
    url: https://arxiv.org/abs/2305.17926
last_reviewed: 2026-11-23
---
# LLM-as-a-judge와 편향

## 무엇인가
LLM-as-a-judge는 사람 대신 LLM이 다른 모델의 출력이나 답변을 채점하게 하는 평가 방식이다. 사람 평가보다 빠르고 싸게 많은 사례를 채점할 수 있다. 다만 판정이 사람의 판단과 얼마나 일치하는지를 사람이 붙인 라벨로 따로 확인해야 믿을 수 있다.

## 알려진 편향
위치 편향은 두 답변을 비교할 때 내용과 상관없이 앞이나 뒤에 놓인 답변을 더 좋게 판정하는 경향이다. 길이 편향은 더 길고 장황한 답변을 내용과 상관없이 더 높게 평가하는 경향이다. 자기 선호 편향은 판정 모델이 자신이나 같은 계열 모델이 생성한 답변을 더 높게 평가하는 경향이다.

## 완화 방법
비교 평가에서는 두 답변의 순서를 바꿔 두 번 판정하고 결과가 일치할 때만 채택해 위치 편향을 줄인다. 채점 기준(루브릭)을 명시하고 근거를 먼저 쓰게 한 뒤 점수를 내게 하면 판정이 안정된다. 판정 모델은 평가 대상을 생성한 모델과 다른 모델을 쓰면 자기 선호 편향을 줄일 수 있다. 같은 입력을 여러 번 판정해 결과가 얼마나 흔들리는지 재면 판정의 반복 일관성을 확인할 수 있다.
