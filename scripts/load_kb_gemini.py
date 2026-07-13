from pathlib import Path

from rag.loader import chunk_text
from rag.vectorstore import get_interview_kb_gemini_vectorstore

KB_DIR = Path("kb")

vectorstore = get_interview_kb_gemini_vectorstore()

for file_path in sorted(KB_DIR.glob("*.md")):
    text = file_path.read_text(encoding="utf-8")
    documents = chunk_text(text, source=file_path.name)

    vectorstore.delete(where={"source": file_path.name})
    vectorstore.add_documents(documents)

    print(f"{file_path.name}: {len(documents)} chunks 인덱싱 완료 (Gemini Embedding)")
