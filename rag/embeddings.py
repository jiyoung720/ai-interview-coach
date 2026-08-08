# 텍스트를 숫자 벡터로 바꾸는 임베딩 모델을 만들어 반환하는 파일 (검색의 가장 밑바닥)
# 의미가 비슷한 문장은 벡터도 가깝게 만들어주기 때문에, 키워드가 아니라 "의미"로 검색이 된다.
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from rag.config import GEMINI_API_KEY

EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"  # 한국어로 파인튜닝된 로컬 임베딩 모델


# 업로드 문서(이력서 등) 검색에 쓴다. 사용자가 올린 개인정보라 외부 API로 보내지 않으려고
# 로컬 모델을 유지한다. KB 검색은 Gemini Embedding을 쓴다(아래 참고).
# 모델 파일이 423MB로 무거우므로 lru_cache로 프로세스당 한 번만 로드
@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"


# Interview KB 검색에 쓴다. KB를 29개로 늘리자 ko-sroberta가 "멱등성", "N+1 문제" 같은
# 저빈도 전문용어를 구분하지 못해 교체했다(768차원 vs 3072차원, 30문항 86.7% -> 100%).
#
# import를 함수 안에 둔 이유: 업로드 문서만 다루는 코드(예: scripts/check_retriever.py)는
# 이 모듈을 부를 일이 없는데, 최상단에 두면 그때도 함께 로드된다.
@lru_cache(maxsize=1)
def get_gemini_embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY,
    )
