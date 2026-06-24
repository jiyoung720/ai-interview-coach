from rag.chains import get_chain_a

chain_a = get_chain_a()
result = chain_a.invoke("JWT 관련 경험")

print(type(result))
for i, q in enumerate(result.questions, 1):
    print(f"{i}. {q}")
