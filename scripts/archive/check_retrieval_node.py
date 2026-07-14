from rag.graph import build_retrieval_only_graph

graph = build_retrieval_only_graph()
result = graph.invoke({"question": "JWT란 무엇인가?", "answer": ""})

print("=== state 전체 ===")
print(result)
print()
print("=== context ===")
print(result["context"])
print()
print("=== retrieved_sources ===")
print(result["retrieved_sources"])
