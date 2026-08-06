"""배포 시 KB 인덱싱 대상이 앱의 검색 대상과 어긋나지 않는지 지킨다.

Phase 17 배포에서 실제로 깨졌던 부분이다. 앱은 Gemini 임베딩 컬렉션을 검색하는데
docker-entrypoint.sh와 load_kb.py는 ko-sroberta 컬렉션만 확인하고 채우고 있었다.
EC2 볼륨에는 Gemini 컬렉션이 없어 검색이 0건을 내고, 거리 판정에서 모든 질문이
"근거 없음"으로 빠졌다. 크래시가 아니라 조용히 망가지는 종류라 더 위험했다.

CI에는 API 키가 없으므로 벡터스토어를 만들지 않고 소스만 확인한다.
"""
import inspect
from pathlib import Path

from scripts import load_kb

ENTRYPOINT = Path("docker-entrypoint.sh")


def test_기본_적재_대상이_앱의_검색기를_따라간다():
    source = inspect.getsource(load_kb.main)
    assert "get_interview_kb_retriever()" in source, (
        "load_kb가 특정 컬렉션을 지목하면 임베딩을 바꿀 때 배포가 조용히 깨진다"
    )


def test_엔트리포인트가_앱의_검색_대상을_확인한다():
    script = ENTRYPOINT.read_text(encoding="utf-8")
    assert "get_interview_kb_retriever()" in script, (
        "엔트리포인트가 다른 컬렉션을 보면, 이미 채워진 옛 컬렉션을 보고 "
        "인덱싱을 건너뛴 뒤 앱은 빈 컬렉션을 검색하게 된다"
    )
    assert "get_interview_kb_vectorstore()" not in script


def test_비교_실험용_경로는_남아_있다():
    # 임베딩 비교는 계속 가능해야 하므로 옛 컬렉션을 채우는 길도 유지한다
    params = inspect.signature(load_kb.main).parameters
    assert "sroberta" in params
    assert "get_interview_kb_vectorstore()" in inspect.getsource(load_kb.main)
