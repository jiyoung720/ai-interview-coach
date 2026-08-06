from pathlib import Path

from rag.loader import chunk_text
from rag.vectorstore import get_interview_kb_retriever, get_interview_kb_vectorstore

KB_DIR = Path("kb")


def main(sroberta: bool = False, only_missing: bool = False) -> None:
    """KB 문서를 벡터 DB에 적재한다.

    기본값은 **앱이 실제로 검색하는 컬렉션**이다. 임베딩을 바꾸면 검색 대상 컬렉션도
    함께 바뀌는데, 여기서 특정 컬렉션을 지목해두면 배포된 컨테이너가 빈 인덱스를
    검색하게 된다. 그 경우 크래시가 나지 않고 모든 질문이 "근거 없음"으로 판정되어
    조용히 망가지므로, 앱이 쓰는 검색기를 그대로 따라간다.

    sroberta=True는 임베딩 비교 실험용 컬렉션을 채울 때만 쓴다.
    """
    vectorstore = get_interview_kb_vectorstore() if sroberta else get_interview_kb_retriever().vectorstore

    indexed = set()
    if only_missing:
        # 도중에 실패해 인덱스가 불완전하게 남았을 때 빠진 문서만 채운다
        indexed = {m["source"] for m in vectorstore.get(include=["metadatas"])["metadatas"]}

    for file_path in sorted(KB_DIR.glob("*.md")):
        if file_path.name in indexed:
            continue

        text = file_path.read_text(encoding="utf-8")
        documents = chunk_text(text, source=file_path.name)

        vectorstore.delete(where={"source": file_path.name})  # 재실행 시 중복 방지
        vectorstore.add_documents(documents)

        print(f"{file_path.name}: {len(documents)} chunks 인덱싱 완료")


if __name__ == "__main__":
    import sys

    main(sroberta="--sroberta" in sys.argv, only_missing="--only-missing" in sys.argv)
