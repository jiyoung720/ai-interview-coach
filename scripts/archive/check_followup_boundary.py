from rag.graph import build_interview_agent_graph

graph = build_interview_agent_graph()

question = "JWT란 무엇인가?"
answer = "JWT는 Payload에 사용자 정보를 담은 토큰으로, 서버가 이 토큰을 검증해서 사용자를 인증합니다. 다만 토큰이 만료되면 자동으로 갱신됩니다."

result = graph.invoke({"question": question, "answer": answer})

t_score = result["evaluation_result"].technical_score
followup = result.get("followup_question")

print(f"technical_score: {t_score}")
print(f"followup_question: {followup}")
print()

if t_score == 5:
    status = "PASS" if followup is None else "FAIL (5점인데 followup이 생성됨)"
    print(status)
else:
    print(f"technical_score가 5가 아님({t_score}) — 답변을 조정해서 재실행 필요")
