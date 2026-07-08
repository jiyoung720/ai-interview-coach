from rag.graph import build_chain_b_graph

graph = build_chain_b_graph()
result = graph.invoke({"question": "JWT란 무엇인가?", "answer": "잘 모르겠습니다."})

print(type(result["evaluation_result"]))
print(result["evaluation_result"])
print()
print("retrieved_sources:", result["retrieved_sources"])
