from rag.vectorstore import get_interview_kb_retriever

retriever = get_interview_kb_retriever()

cases = [
    ("세션 기반 인증과 토큰 기반 인증의 차이는 무엇인가요?",
     "세션 기반 인증은 서버가 상태를 저장하고 클라이언트에는 세션 ID만 전달한다. 토큰 기반 인증은 서버가 상태를 저장하지 않고, 토큰 자체에 서명된 정보로 검증한다. 세션은 수평 확장 시 공유 저장소가 필요하지만 토큰은 그렇지 않다."),
    ("Spring Bean의 기본 스코프는 무엇인가요?",
     "Bean은 기본적으로 싱글톤 스코프로 관리되어, 애플리케이션 전체에서 하나의 인스턴스만 생성되고 재사용된다."),
]

for question, reference in cases:
    print("=" * 60)
    print(f"질문: {question}")
    print(f"reference: {reference}")
    print()
    docs = retriever.invoke(question)
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "unknown")
        print(f"--- {i+1}순위 (source: {source}) ---")
        print(doc.page_content)
        print()
