# 검색의 인프라를 담당하는 파일 (Chroma 벡터 DB에 연결하고, 검색기(retriever)를 만들어 건네주는 것")
from functools import lru_cache

from langchain_chroma import Chroma

from rag.embeddings import get_embeddings

# User Docs(사용자가 올리는 이력서 등)와 Interview KB(운영자가 작성하는 고정 지식)는
# 성격이 다른 데이터라 컬렉션을 분리 - Chain A는 전자를, Chain B는 후자를 검색한다.
CHROMA_DIR = "chroma_db"
USER_DOCS_COLLECTION = "user_docs"
INTERVIEW_KB_COLLECTION = "interview_kb"


@lru_cache(maxsize=1)  # 임베딩 모델을 매 요청마다 다시 로드하지 않도록 프로세스당 1개만 생성
def get_user_docs_vectorstore() -> Chroma:
    return Chroma(
        collection_name=USER_DOCS_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
        # Chroma 기본값은 L2 거리라 벡터 크기 차이에 영향을 받음. 텍스트 임베딩은
        # "방향"(의미)이 중요하므로 cosine distance를 명시적으로 지정.
        collection_metadata={"hnsw:space": "cosine"},
    )


# 벡터스토어를 감싸 "쿼리 문자열 -> 관련 문서 목록"을 돌려주는 검색기로 만듦
# k=3: 유사도 상위 3개만 가져옴 (노드에서 docs가 항상 3개인 이유)
def get_user_docs_retriever(k: int = 3):
    return get_user_docs_vectorstore().as_retriever(search_kwargs={"k": k})


# Chain B가 검색하는 면접 KB 컬렉션. user_docs와 설정은 같고 컬렉션 이름만 다름
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


# 아래는 임베딩 비교 실험 전용. 같은 KB를 Gemini 임베딩으로 인덱싱한 별도 컬렉션이라,
# ko-sroberta 컬렉션과 완전히 독립적으로 두 임베딩을 나란히 비교할 수 있다.
INTERVIEW_KB_GEMINI_COLLECTION = "interview_kb_gemini_embedding"


@lru_cache(maxsize=1)
def get_interview_kb_gemini_vectorstore() -> Chroma:
    from rag.embeddings import get_gemini_embeddings   # 실험 전용이라 함수 안에서 지연 import

    return Chroma(
        collection_name=INTERVIEW_KB_GEMINI_COLLECTION,
        embedding_function=get_gemini_embeddings(),
        persist_directory=CHROMA_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )


def get_interview_kb_gemini_retriever(k: int = 3):
    return get_interview_kb_gemini_vectorstore().as_retriever(search_kwargs={"k": k})
