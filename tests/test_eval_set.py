"""평가셋의 정답 키가 KB와 어긋나지 않는지 지킨다.

Phase 15에서 `http.md`를 분리하며 정답 키를 잘못 옮긴 것을 RAGAS 평가를 수백 회
돌리고 나서야 발견했다. 문자열 검사만으로 잡히는 종류였으므로 CI에서 매번 확인한다.
KB 문서를 고쳐 근거 문장이 사라지는 경우도 여기서 걸린다.
"""
import json
from pathlib import Path

import pytest

from scripts.check_eval_set import EVAL_SET_PATH, KB_DIR, check


@pytest.fixture(scope="module")
def kb_texts():
    return {p.name: p.read_text(encoding="utf-8") for p in KB_DIR.glob("*.md")}


@pytest.fixture(scope="module")
def eval_set():
    return json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))


def test_정답_키가_KB와_일치한다(eval_set, kb_texts):
    errors, _ = check(eval_set, kb_texts)
    assert not errors, "\n" + "\n".join(errors)


def test_모든_문항에_근거_문구가_있다(eval_set):
    # 범위 밖 문항(expected_sources가 빈 목록)은 근거가 없는 것이 정상이다
    missing = [
        c["question"] for c in eval_set if c.get("expected_sources") and not c.get("key_evidence")
    ]
    assert not missing, f"key_evidence 없는 문항: {missing}"


def test_검사기가_잘못된_정답_키를_잡아낸다(kb_texts):
    # 검사가 항상 통과하면 의미가 없으므로, 실제로 걸러내는지 확인한다
    broken = [
        {   # 근거 문구가 정답 문서에 없는 경우 (Phase 15에서 실제로 있던 버그)
            "question": "JWT를 HTTP 요청에 실어 보낼 때 어떤 헤더를 사용하나요?",
            "expected_sources": ["rest_api_design.md"],
            "key_evidence": "형식은 `Authorization: Bearer <토큰>`이며",
        },
        {   # KB에 없는 문서를 정답으로 지정한 경우
            "question": "HTTP 메서드는 무엇이 있나요?",
            "expected_sources": ["존재하지_않는_문서.md"],
            "key_evidence": "GET은 리소스 조회",
        },
    ]
    errors, _ = check(broken, kb_texts)
    assert len(errors) == 2
