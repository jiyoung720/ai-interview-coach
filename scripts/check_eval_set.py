# 평가셋의 정답 키가 실제 KB와 맞는지 검사한다. API를 쓰지 않으므로 비용 없이 매번 돌릴 수 있다.
#
# Phase 15에서 `http.md`를 분리하며 "JWT를 HTTP 요청에 실어 보낼 때 어떤 헤더를 사용하나요?"의
# 정답 키를 `rest_api_design.md`로 잘못 옮겼다. 그 문서에는 Authorization도 Bearer도 없는데,
# 두 임베딩 모두 실제로는 맞는 문서를 찾아오고 있었으므로 오답이 아니라 정답 키가 틀린 것이었다.
# RAGAS 평가를 수백 회 돌리고 나서야 발견했다. 이런 오류를 문자열 검사만으로 미리 잡는다.
import json
import re
import sys
from pathlib import Path

KB_DIR = Path("kb")
EVAL_SET_PATH = Path("tests/fixtures/retrieval_eval_set.json")


def normalize(text: str) -> str:
    """공백·개행 차이로 검사가 실패하지 않도록 눌러준다."""
    return re.sub(r"\s+", " ", text).strip()


def check(eval_set: list, kb_texts: dict) -> tuple[list, list]:
    errors, warnings = [], []

    for i, case in enumerate(eval_set, 1):
        question = case["question"]
        expected = case.get("expected_sources", [])
        label = f"{i:02d} {question[:38]}"

        # expected_sources가 빈 목록인 것은 범위 밖 문항(Phase 17)이라 정상이다
        if not expected:
            if "note" not in case:
                warnings.append(f"{label}\n     범위 밖 문항인데 note가 없다")
            continue

        missing = [s for s in expected if s not in kb_texts]
        if missing:
            errors.append(f"{label}\n     KB에 없는 문서를 정답으로 지정: {missing}")
            continue

        evidence = case.get("key_evidence")
        if not evidence:
            warnings.append(f"{label}\n     key_evidence 없음 (정답 키를 검증할 수 없다)")
            continue

        found = [s for s in expected if normalize(evidence) in normalize(kb_texts[s])]
        if not found:
            errors.append(
                f"{label}\n"
                f"     key_evidence가 정답 문서 어디에도 없다\n"
                f"     근거: {evidence[:60]}\n"
                f"     정답: {expected}"
            )

    return errors, warnings


def main() -> int:
    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    kb_texts = {p.name: p.read_text(encoding="utf-8") for p in KB_DIR.glob("*.md")}

    print(f"평가셋 {len(eval_set)}문항, KB {len(kb_texts)}개 문서")

    errors, warnings = check(eval_set, kb_texts)

    if warnings:
        print(f"\n경고 {len(warnings)}건")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\n오류 {len(errors)}건")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\n정답 키 오류 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
