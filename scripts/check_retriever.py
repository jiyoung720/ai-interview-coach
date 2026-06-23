import sys

from rag.vectorstore import get_user_docs_retriever

query = sys.argv[1] if len(sys.argv) > 1 else "JWT"

retriever = get_user_docs_retriever()
docs = retriever.invoke(query)

print(f"쿼리: {query}")
print(f"검색된 chunk 수: {len(docs)}")
for i, doc in enumerate(docs):
    print(f"--- chunk {i} ---")
    print(doc.page_content)
    print()
