---
topic: llm_judge
area: evaluation
difficulty: intermediate
sources:
  - title: "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (Zheng et al., 2023)"
    url: https://arxiv.org/abs/2306.05685
  - title: "LLM Evaluators Recognize and Favor Their Own Generations (Panickssery et al., 2024)"
    url: https://arxiv.org/abs/2404.13076
  - title: "Anthropic - Glossary (Temperature)"
    url: https://platform.claude.com/docs/en/about-claude/glossary#temperature
last_reviewed: 2026-11-24
---
# LLM-as-a-judge와 편향

## 무엇인가
LLM-as-a-judge는 사람 대신 LLM이 다른 모델의 출력이나 사람의 답변을 채점하게 하는 평가 방식이다. 사람 평가보다 빠르고 싸게 많은 사례를 채점할 수 있다. 문자열 일치 같은 규칙 기반 평가는 빠르고 결과가 일정하지만, 표현은 다르고 뜻은 같은 답을 놓칠 수 있다. LLM 판정은 의미를 보고 판단할 수 있지만, 규칙 기반보다 점수가 높게 나왔다는 것만으로 더 정확하다고 볼 수는 없다.

## 알려진 편향
위치 편향은 두 답변을 비교할 때 내용과 상관없이 앞이나 뒤에 놓인 답변을 더 좋게 판정하는 경향이다. 길이 편향은 더 길고 장황한 답변을 내용과 상관없이 더 높게 평가하는 경향이다. 자기 선호 편향은 판정 모델이 자신이 생성한 답변을 더 높게 평가하는 경향이다.

## 판정을 믿을 수 있는지 확인하기
판정을 믿으려면 사람이 붙인 라벨과 얼마나 일치하는지와, 같은 입력을 여러 번 판정했을 때 결과가 얼마나 흔들리는지를 따로 확인한다. 매번 같은 오답을 내는 판정 모델도 반복 일관성은 높을 수 있으므로, 두 가지는 별개의 기준이다. temperature를 0으로 낮춰도 같은 입력에 항상 같은 출력이 나온다고 보장되지는 않으므로, 반복 판정으로 흔들림을 직접 잰다. 판정 응답을 해석하지 못했을 때 0점으로 기록하면 판정 실패와 낮은 점수가 섞여 지표가 왜곡된다. 실패는 따로 기록하고 재시도하거나 집계에서 분리한다.

## 편향 완화
편향을 줄이는 방법은 평가 상황에 따라 다르며, 순서 교환, 다른 판정 모델 사용, 루브릭과 길이 통제 중 상황에 맞는 것을 쓴다. 두 답변을 비교하는 평가라면 순서를 바꿔 두 번 판정하고 결과가 일치할 때만 채택해 위치 편향을 줄인다. 모델이 생성한 답변을 평가할 때는 생성 모델과 다른 판정 모델을 쓰면 자기 선호 편향을 줄일 수 있다. 채점 기준(루브릭)에 길이로 점수를 주지 말라고 명시하고, 내용은 같고 길이만 다른 답변 쌍으로 길이 편향을 측정할 수 있다.
