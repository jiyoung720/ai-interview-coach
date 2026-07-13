from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from rag.config import GEMINI_API_KEY

EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"


@lru_cache(maxsize=1)
def get_gemini_embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY,
    )
