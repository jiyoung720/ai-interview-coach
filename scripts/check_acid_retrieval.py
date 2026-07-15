from rag.vectorstore import get_interview_kb_retriever

retriever = get_interview_kb_retriever()
question = "트랜잭션의 ACID 속성은 무엇인가요?"

for attempt in range(3):
    docs = retriever.invoke(question)
    print(f"=== 시도 {attempt + 1} ===")
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "unknown")
        preview = doc.page_content[:60].replace("\n", " ")
        print(f"  {i + 1}순위: {source} | {preview}...")
    print()
