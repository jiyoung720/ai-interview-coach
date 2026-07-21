"""Agent 다중 분기(0~3 / 4~6 / 7~10) 세 경로가 실제로 동작하는지 확인.

Day 4의 경계값 검증과 같은 방식으로, 각 구간의 점수가 나오도록 설계한 답변을
넣고 실제로 의도한 노드가 실행되는지(next_action)와 해당 결과가 채워지는지 본다.
"""
from rag.graph import build_interview_agent_graph

CASES = [
    (
        "0~3점 기대 (개념 자체를 모름)",
        "JWT란 무엇인가?",
        "잘 모르겠습니다.",
        "fundamentals_explained",
        "concept_explanation",
    ),
    (
        "4~6점 기대 (부분 이해)",
        "JWT란 무엇인가?",
        "JWT는 Payload에 사용자 정보를 담은 토큰으로, 서버가 이 토큰을 검증해서 "
        "사용자를 인증합니다. 다만 토큰이 만료되면 자동으로 갱신됩니다.",
        "followup_generated",
        "learning_tip",
    ),
    (
        "7~10점 기대 (정확히 답함)",
        "JWT란 무엇인가?",
        "JWT는 JSON Web Token의 약자로 Header, Payload, Signature 세 부분으로 구성됩니다. "
        "서버가 비밀키로 서명하고, 검증 시 서명을 확인하므로 별도의 세션 저장소 없이 "
        "stateless하게 사용자를 인증할 수 있습니다.",
        "advanced_question_generated",
        "advanced_question",
    ),
]


def main():
    graph = build_interview_agent_graph()

    for label, question, answer, expected_action, expected_key in CASES:
        print("=" * 60)
        print(f"[{label}]")
        result = graph.invoke({"question": question, "answer": answer})

        score = result["evaluation_result"].technical_score
        action = result.get("next_action")
        payload = result.get(expected_key)

        passed = action == expected_action and payload is not None
        print(f"  technical_score = {score}")
        print(f"  next_action     = {action} (기대: {expected_action})")
        print(f"  {expected_key} 채워짐 = {payload is not None}")
        print(f"  => {'PASS' if passed else 'FAIL'}")

        # 다른 경로의 키가 잘못 채워지지 않았는지도 확인
        other_keys = {"concept_explanation", "learning_tip", "advanced_question"} - {expected_key}
        leaked = [k for k in other_keys if result.get(k) is not None]
        if leaked:
            print(f"  [경고] 다른 경로 키가 채워짐: {leaked}")

        if payload is not None:
            print(f"  결과 미리보기: {str(payload)[:150]}...")
        print()


if __name__ == "__main__":
    main()
