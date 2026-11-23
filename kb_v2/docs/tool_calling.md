---
topic: tool_calling
area: agents
difficulty: basic
sources:
  - title: "Gemini API - Function calling"
    url: https://ai.google.dev/gemini-api/docs/function-calling
  - title: "ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022)"
    url: https://arxiv.org/abs/2210.03629
last_reviewed: 2026-11-23
---
# Tool Calling

## 무엇인가
tool calling(function calling)은 LLM이 답을 바로 쓰는 대신, 미리 정의된 함수를 어떤 인자로 호출할지 구조화된 형태로 내놓는 기능이다. 모델은 함수를 직접 실행하지 않고, 애플리케이션이 그 호출을 실행한 뒤 결과를 다시 모델에게 돌려준다. 모델은 함수 이름, 설명, 인자 스키마를 보고 언제 어떤 도구를 쓸지 판단하므로, 도구 설명이 사실상 프롬프트 역할을 한다.

## 실행 루프
모델이 도구 호출을 요청하면 애플리케이션이 실행하고 결과를 대화에 추가한 뒤 모델을 다시 부른다. 모델이 더 이상 도구를 부르지 않고 최종 답을 낼 때까지 이 과정을 반복한다. ReAct는 추론과 행동(도구 호출)을 번갈아 하며 관찰 결과를 다음 추론에 반영하는 방식이다.

## 실패 처리
모델은 존재하지 않는 도구를 부르거나 스키마에 맞지 않는 인자를 넣을 수 있으므로, 실행 전에 이름과 인자를 검증해야 한다. 같은 도구를 끝없이 반복 호출하지 않도록 호출 횟수 상한을 두고, 상한에 걸리면 도구 없이 처리하는 경로로 되돌아가야 한다. 도구가 실행할 수 있는 범위는 모델이 넘긴 인자가 아니라 애플리케이션이 허용한 권한으로 제한해야 한다.
