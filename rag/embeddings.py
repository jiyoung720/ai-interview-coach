# 텍스트를 숫자 벡터로 바꾸는 임베딩 모델을 만들어 반환하는 파일 (검색의 가장 밑바닥)
# 의미가 비슷한 문장은 벡터도 가깝게 만들어주기 때문에, 키워드가 아니라 "의미"로 검색이 된다.
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from rag.config import GEMINI_API_KEY

EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"  # 한국어로 파인튜닝된 임베딩 모델 -기본값


# 기본 임베딩. User Docs와 Interview KB 둘 다 이걸로 인덱싱한다.
# 모델 로딩이 무거우므로 lru_cache로 프로세스당 한 번만 로드
@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"


# Gemini Embedding은 기본 경로가 아니라 ko-sroberta(한국어 특화 모델)와의 비교 실험 전용이라,
# import를 함수 내부로 미뤄서 비교 실험을 안 하는 한 로드되지 않게 함.
@lru_cache(maxsize=1)
def get_gemini_embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY,
    )
