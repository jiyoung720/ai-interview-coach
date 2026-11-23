---
topic: structured_output
area: prompting
difficulty: basic
sources:
  - title: "Gemini API - Structured output"
    url: https://ai.google.dev/gemini-api/docs/structured-output
  - title: "JSON Schema"
    url: https://json-schema.org/
last_reviewed: 2026-11-23
---
# Structured Output

## 왜 필요한가
LLM의 자유 텍스트 응답을 코드에서 쓰려면 원하는 값을 문자열에서 파싱해야 하는데, 형식이 조금만 달라져도 파싱이 깨진다. structured output은 응답이 정해진 스키마(필드 이름, 타입, 허용 값)를 따르도록 모델에 강제하는 기능이다. 그래서 애플리케이션은 문자열 파싱 없이 정해진 필드를 바로 읽을 수 있다.

## 어떻게 쓰나
스키마는 보통 JSON Schema나 Pydantic 같은 데이터 모델로 정의해 모델 호출에 함께 넘긴다. 필드 설명(description)과 열거형(enum)을 주면 모델이 각 필드에 무엇을 넣어야 하는지 더 정확히 따른다.

## 한계와 주의점
스키마를 강제해도 형식이 맞는 것일 뿐, 내용이 사실이거나 논리적으로 맞다는 보장은 없다. 그래서 값의 범위나 필드 사이의 관계(예: 감점 합계와 점수의 일치) 같은 규칙은 코드로 따로 검증해야 한다. 필드는 정의된 순서대로 생성되는 경향이 있어, 근거를 먼저 쓰고 결론을 나중에 쓰도록 필드 순서를 정하면 사후 정당화를 줄일 수 있다.
