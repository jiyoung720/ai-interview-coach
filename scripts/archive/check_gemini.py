from langchain_google_genai import ChatGoogleGenerativeAI

from rag.config import GEMINI_MODEL
from rag.llm_utils import extract_text

llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL)
response = llm.invoke("안녕")
print(extract_text(response))
