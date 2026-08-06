#!/bin/sh
set -e

# chroma_db는 volume이라 컨테이너를 처음 띄우면 비어 있다.
# Interview KB가 인덱싱되지 않은 상태면 Chain B 검색이 빈 결과를 내므로,
# 기동 전에 비어 있는지 확인하고 필요할 때만 일회성 인덱싱을 수행한다.
# (KB는 사용자가 올리는 데이터가 아니라 이미지에 포함된 고정 콘텐츠이므로 자동 적재가 안전하다)
#
# 확인 대상은 앱이 실제로 검색하는 컬렉션이다. 임베딩을 바꾸면 컬렉션도 함께 바뀌는데
# 여기서 특정 컬렉션을 지목해두면, 이미 채워진 옛 컬렉션을 보고 "인덱싱 완료"로 판단한 뒤
# 앱은 빈 컬렉션을 검색하게 된다. 그 경우 크래시 없이 모든 질문이 "근거 없음"이 된다.
if [ "$SKIP_KB_LOAD" != "1" ]; then
  python - <<'PY'
from rag.vectorstore import get_interview_kb_retriever

count = get_interview_kb_retriever().vectorstore._collection.count()
if count == 0:
    print("[entrypoint] Interview KB가 비어 있어 인덱싱을 시작합니다.")
    import runpy
    runpy.run_module("scripts.load_kb", run_name="__main__")
else:
    print(f"[entrypoint] Interview KB 확인 완료 (chunk {count}개), 인덱싱을 건너뜁니다.")
PY
fi

exec "$@"
