---
topic: prompt_injection
area: safety
difficulty: basic
sources:
  - title: "OWASP Top 10 for LLM Applications - LLM01 Prompt Injection"
    url: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
  - title: "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection (Greshake et al., 2023)"
    url: https://arxiv.org/abs/2302.12173
  - title: "Google Cloud - System instructions"
    url: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/system-instructions
last_reviewed: 2026-11-23
---
# 프롬프트 인젝션

## 무엇인가
프롬프트 인젝션은 사용자 입력이나 외부 데이터에 들어 있는 지시문 때문에 LLM이 개발자가 의도한 지시를 벗어나 동작하게 되는 공격이다. API는 시스템 지시와 사용자 입력을 따로 전달할 수 있지만, 그 구분이 모델의 행동을 막는 보안 경계를 보장하지는 않는다. 모델은 결국 두 입력을 함께 읽고 판단하기 때문에, 입력 안의 문장이 지시처럼 작동할 수 있다.

## 직접 인젝션과 간접 인젝션
둘은 지시문이 들어오는 경로로 구분한다. 직접 인젝션은 사용자가 입력으로 지시문을 직접 넣는 경우다. 간접 인젝션은 LLM이 읽는 웹페이지, 문서, 검색 결과, 도구 응답처럼 외부 경로로 지시문이 들어오는 경우다. 간접 인젝션은 사용자가 공격자가 아니어도 일어날 수 있어서, RAG나 도구를 쓰는 애플리케이션에서 특히 위험하다.

## 방어
프롬프트에 구분자를 두거나 지시를 따르지 말라고 쓰는 것만으로는 막을 수 없다. 외부 문서나 도구 응답은 신뢰할 수 없는 데이터로 다루고, 그 안의 문장이 권한을 부여할 수 없도록 실행 전에 애플리케이션 코드에서 허용된 동작과 인자를 검사한다. 모델이 쓸 수 있는 도구와 권한을 최소로 하고, 되돌릴 수 없거나 위험한 동작은 사람의 확인을 거치게 한다. 모델 출력도 그대로 믿지 않고 코드로 형식과 값을 검증한다.
