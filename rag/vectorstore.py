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


def get_interview_kb_sroberta_retriever(k: int = 3):
    return get_interview_kb_vectorstore().as_retriever(search_kwargs={"k": k})


# 같은 KB를 Gemini 임베딩으로 인덱싱한 별도 컬렉션. ko-sroberta 컬렉션과 독립적이라
# 두 임베딩을 나란히 비교할 수 있고, 앱이 쓰는 쪽을 바꿔도 다른 쪽 인덱스는 그대로 남는다.
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


# 앱이 실제로 쓰는 KB 검색기. 어느 임베딩을 쓸지는 여기 한 곳에서만 정한다.
#
# KB를 18개에서 29개로 늘린 뒤 30문항 평가에서 Gemini가 Top-1 100%, ko-sroberta가 86.7%였다.
# ko-sroberta는 "멱등성", "N+1 문제" 같은 저빈도 전문용어를 벡터로 구분하지 못해
# 무관한 문서를 1순위로 올렸다(768차원 vs 3072차원). KB가 작을 때는 주제가 서로 멀어
# 드러나지 않던 한계다. 측정 근거는 docs/experiment_log.md 참고.
#
# 대신 검색마다 API 호출이 생기므로, 크레딧이 없으면 검색부터 막힌다.
# 되돌리려면 이 함수만 sroberta 쪽으로 바꾸면 된다(양쪽 인덱스가 모두 남아 있다).
def get_interview_kb_retriever(k: int = 3):
    return get_interview_kb_gemini_retriever(k)
