from rag.graph import build_chain_a_graph

graph = build_chain_a_graph()
result = graph.invoke({"question": "JWT 관련 경험"})

print(type(result["generated_questions"]))
for i, q in enumerate(result["generated_questions"].questions, 1):
    print(f"{i}. {q}")
print()
print("retrieved_sources:", result["retrieved_sources"])
