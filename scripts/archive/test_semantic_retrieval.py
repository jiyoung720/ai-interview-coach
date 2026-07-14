from langchain_core.documents import Document

from rag.vectorstore import get_user_docs_vectorstore

TEST_SOURCE = "_semantic_test"

doc_auth = Document(
    page_content="JWT를 이용한 사용자 인증 처리. Access Token과 Refresh Token을 분리하여 보안을 강화했습니다.",
    metadata={"source": TEST_SOURCE},
)
doc_unrelated = Document(
    page_content="pytest로 단위 테스트를 작성했습니다. CI 파이프라인에서 매 커밋마다 자동으로 실행되도록 구성했습니다.",
    metadata={"source": TEST_SOURCE},
)

vectorstore = get_user_docs_vectorstore()
vectorstore.delete(where={"source": TEST_SOURCE})
vectorstore.add_documents([doc_auth, doc_unrelated])

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
docs = retriever.invoke("로그인한 사용자를 어떻게 식별하나요?")

print("=== 검색 결과 (관련도 순) ===")
for i, doc in enumerate(docs):
    print(f"{i+1}. {doc.page_content}")

vectorstore.delete(where={"source": TEST_SOURCE})
print("\n테스트 데이터 정리 완료 (실제 컬렉션엔 영향 없음)")
