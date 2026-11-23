---
topic: prompt_injection
area: safety
difficulty: basic
sources:
  - title: "OWASP Top 10 for LLM Applications - LLM01 Prompt Injection"
    url: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
  - title: "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection (Greshake et al., 2023)"
    url: https://arxiv.org/abs/2302.12173
last_reviewed: 2026-11-23
---
# 프롬프트 인젝션

## 무엇인가
프롬프트 인젝션은 사용자 입력이나 외부 데이터에 숨긴 지시문으로 LLM이 원래 지시를 무시하고 공격자의 의도대로 동작하게 만드는 공격이다. LLM은 시스템 지시와 사용자가 넣은 데이터를 같은 텍스트로 받기 때문에 둘을 근본적으로 구분하지 못한다.

## 직접 인젝션과 간접 인젝션
직접 인젝션은 사용자가 입력창에 "이전 지시를 무시하라" 같은 문장을 직접 넣는 경우다. 간접 인젝션은 LLM이 읽는 웹페이지, 문서, 검색 결과, 도구 응답 안에 지시문이 숨어 있는 경우다. 간접 인젝션은 사용자가 공격자가 아니어도 일어날 수 있어서, RAG나 도구를 쓰는 애플리케이션에서 특히 위험하다.

## 방어
프롬프트 인젝션을 완전히 막는 단일 방법은 없어서 여러 겹으로 방어한다. 신뢰할 수 없는 입력은 구분된 블록에 넣고 그 안의 지시를 따르지 말라고 명시한다. 모델 출력은 그대로 믿지 않고 코드로 형식과 값을 검증한다. 모델이 쓸 수 있는 도구와 권한을 최소로 하고, 되돌릴 수 없는 동작은 사람의 확인을 거치게 한다.
