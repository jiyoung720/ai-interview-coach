from rag.vectorstore import get_interview_kb_retriever

retriever = get_interview_kb_retriever()
docs = retriever.invoke("JWT란 무엇인가?")

print(f"검색된 chunk 수: {len(docs)}")
for i, doc in enumerate(docs):
    print(f"--- chunk {i} (source: {doc.metadata.get('source')}) ---")
    print(doc.page_content)
    print()
