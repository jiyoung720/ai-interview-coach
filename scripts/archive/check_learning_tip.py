from rag.graph import build_interview_agent_graph

graph = build_interview_agent_graph()

print("=== Case A: bad 답변 (Learning Tip + Followup 둘 다 기대, topic 공유) ===")
result_low = graph.invoke({"question": "JWT란 무엇인가?", "answer": "잘 모르겠습니다."})
print("technical_score:", result_low["evaluation_result"].technical_score)
print("learning_tip:", result_low.get("learning_tip"))
print("followup_question:", result_low.get("followup_question"))

print()
print("=== Case B: good 답변 (둘 다 None 기대) ===")
result_high = graph.invoke({
    "question": "JWT란 무엇인가?",
    "answer": "JWT는 사용자 인증 정보를 안전하게 전달하기 위한 토큰 기반 인증 방식으로, Header, Payload, Signature로 구성되며 서버가 별도 세션 저장소 없이 서명을 검증해 사용자를 인증할 수 있습니다.",
})
print("technical_score:", result_high["evaluation_result"].technical_score)
print("learning_tip:", result_high.get("learning_tip"))
print("followup_question:", result_high.get("followup_question"))
