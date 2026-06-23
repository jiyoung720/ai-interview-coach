from functools import lru_cache

from langchain_chroma import Chroma

from rag.embeddings import get_embeddings

CHROMA_DIR = "chroma_db"
USER_DOCS_COLLECTION = "user_docs"


@lru_cache(maxsize=1)
def get_user_docs_vectorstore() -> Chroma:
    return Chroma(
        collection_name=USER_DOCS_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
        # 메인 프로젝트에서 디버깅했던 부분 — Chroma 기본 거리함수는 L2라서
        # cosine similarity로 쓰려면 명시적으로 지정해줘야 함
        collection_metadata={"hnsw:space": "cosine"},
    )


def get_user_docs_retriever(k: int = 3):
    return get_user_docs_vectorstore().as_retriever(search_kwargs={"k": k})
