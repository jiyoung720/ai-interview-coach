from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from rag.config import GEMINI_API_KEY

EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"  # 한국어로 파인튜닝된 임베딩 모델 - 기본값


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"


# Gemini Embedding은 기본 경로가 아니라 ko-sroberta와의 비교 실험 전용이라,
# import를 함수 내부로 미뤄서 비교 실험을 안 하는 한 로드되지 않게 함.
@lru_cache(maxsize=1)
def get_gemini_embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY,
    )
