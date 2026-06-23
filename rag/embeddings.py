from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
