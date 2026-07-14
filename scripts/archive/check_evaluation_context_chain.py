from rag.chains import get_evaluation_context_chain

chain = get_evaluation_context_chain()
filled = chain.invoke({
    "question": "JWT란 무엇인가?",
    "answer": "잘 모르겠습니다.",
})
print(filled.to_string())
