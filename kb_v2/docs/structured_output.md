---
topic: structured_output
area: prompting
difficulty: basic
sources:
  - title: "Gemini API - Structured output"
    url: https://ai.google.dev/gemini-api/docs/structured-output
  - title: "JSON Schema - Numeric types"
    url: https://json-schema.org/understanding-json-schema/reference/numeric
last_reviewed: 2026-11-23
---
# Structured Output

## 왜 쓰나
LLM의 자유 텍스트 응답을 코드에서 쓰려면 원하는 값을 문장에서 찾아 추출해야 하는데, 표현이 조금만 달라져도 추출이 깨지기 쉽다. structured output은 모델의 응답이 정해진 스키마(필드 이름, 타입, 허용 값 등)를 따르도록 제약하는 기능이다. 그래서 자유 텍스트에서 원하는 값을 추출하는 부담이 줄고, SDK가 지원하면 응답을 바로 객체로 받을 수 있다. JSON 문자열로 받는다면 JSON 파싱은 여전히 필요하지만, 형식이 정해져 있어 훨씬 안정적이다.

## 어떻게 쓰나
스키마는 보통 JSON Schema나 Pydantic 같은 데이터 모델로 정의해 모델 호출에 함께 넘긴다. 필드 설명(description)과 열거형(enum)을 주면 모델이 각 필드에 무엇을 넣어야 하는지 더 정확히 따른다.

## 한계와 주의점
스키마는 형식과 일부 값 제약(타입, 열거형, 숫자 범위 등)을 표현할 수 있지만, 내용이 사실인지나 근거가 맞는지는 보장하지 않는다. 그래서 스키마로 표현할 수 없는 업무 규칙이나 필드 사이의 관계(예: 감점 합계와 점수의 일치), 근거의 정확성은 애플리케이션 코드에서 따로 검증한다.
