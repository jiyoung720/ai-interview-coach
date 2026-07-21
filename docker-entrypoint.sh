#!/bin/sh
set -e

# chroma_db는 volume이라 컨테이너를 처음 띄우면 비어 있다.
# Interview KB가 인덱싱되지 않은 상태면 Chain B 검색이 빈 결과를 내므로,
# 기동 전에 비어 있는지 확인하고 필요할 때만 일회성 인덱싱을 수행한다.
# (KB는 사용자가 올리는 데이터가 아니라 이미지에 포함된 고정 콘텐츠이므로 자동 적재가 안전하다)
if [ "$SKIP_KB_LOAD" != "1" ]; then
  python - <<'PY'
from rag.vectorstore import get_interview_kb_vectorstore

count = get_interview_kb_vectorstore()._collection.count()
if count == 0:
    print("[entrypoint] Interview KB가 비어 있어 인덱싱을 시작합니다.")
    import runpy
    runpy.run_module("scripts.load_kb", run_name="__main__")
else:
    print(f"[entrypoint] Interview KB 확인 완료 (chunk {count}개), 인덱싱을 건너뜁니다.")
PY
fi

exec "$@"
