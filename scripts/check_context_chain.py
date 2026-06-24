from rag.chains import get_context_chain

context_chain = get_context_chain()
filled = context_chain.invoke("JWT 관련 경험")
print(filled.to_string())
