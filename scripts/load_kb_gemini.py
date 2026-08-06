from pathlib import Path

from rag.loader import chunk_text
from rag.vectorstore import get_interview_kb_gemini_vectorstore

KB_DIR = Path("kb")


def main(only_missing: bool = False) -> None:
    vectorstore = get_interview_kb_gemini_vectorstore()

    indexed = set()
    if only_missing:
        indexed = {m["source"] for m in vectorstore.get(include=["metadatas"])["metadatas"]}

    for file_path in sorted(KB_DIR.glob("*.md")):
        if file_path.name in indexed:
            continue

        text = file_path.read_text(encoding="utf-8")
        documents = chunk_text(text, source=file_path.name)

        vectorstore.delete(where={"source": file_path.name})
        vectorstore.add_documents(documents)

        print(f"{file_path.name}: {len(documents)} chunks 인덱싱 완료 (Gemini Embedding)")


# KB 전체를 Gemini API로 다시 임베딩하므로 실행할 때마다 과금된다.
# import만 해도 재인덱싱이 시작되는 사고가 있어서 가드를 뒀다.
# 도중에 한도에 걸리면 인덱스가 불완전하게 남는다. 그때는 --only-missing으로 빠진 문서만 채운다.
if __name__ == "__main__":
    import sys

    main(only_missing="--only-missing" in sys.argv)
