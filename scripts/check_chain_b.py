from rag.chains import get_chain_b

chain_b = get_chain_b()
result = chain_b.invoke({
    "question": "JWT란 무엇인가?",
    "answer": "잘 모르겠습니다.",
})
print(type(result))
print(result)
