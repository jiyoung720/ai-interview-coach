from functools import lru_cache

from langchain_chroma import Chroma

from rag.embeddings import get_embeddings

CHROMA_DIR = "chroma_db"
USER_DOCS_COLLECTION = "user_docs"
INTERVIEW_KB_COLLECTION = "interview_kb"


@lru_cache(maxsize=1)
def get_user_docs_vectorstore() -> Chroma:
    return Chroma(
        collection_name=USER_DOCS_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )


def get_user_docs_retriever(k: int = 3):
    return get_user_docs_vectorstore().as_retriever(search_kwargs={"k": k})


@lru_cache(maxsize=1)
def get_interview_kb_vectorstore() -> Chroma:
    return Chroma(
        collection_name=INTERVIEW_KB_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )


def get_interview_kb_retriever(k: int = 3):
    return get_interview_kb_vectorstore().as_retriever(search_kwargs={"k": k})


INTERVIEW_KB_GEMINI_COLLECTION = "interview_kb_gemini_embedding"


@lru_cache(maxsize=1)
def get_interview_kb_gemini_vectorstore() -> Chroma:
    from rag.embeddings import get_gemini_embeddings

    return Chroma(
        collection_name=INTERVIEW_KB_GEMINI_COLLECTION,
        embedding_function=get_gemini_embeddings(),
        persist_directory=CHROMA_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )


def get_interview_kb_gemini_retriever(k: int = 3):
    return get_interview_kb_gemini_vectorstore().as_retriever(search_kwargs={"k": k})
