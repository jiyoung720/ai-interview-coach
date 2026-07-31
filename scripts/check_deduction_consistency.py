"""감점 합계가 점수와 일치하는지 검증한다 (Phase 12).

프롬프트에서 `deductions의 points 합 = 10 - technical_score`를 요구했지만,
LLM이 산술을 틀릴 수 있으므로 실제로 지켜지는지 측정한다.
불일치가 잦다면 감점 목록을 참고용으로 낮추거나, 코드에서 점수를 재계산하는
방식으로 바꿔야 한다.

Calibration Set을 그대로 재사용해 별도 입력 없이 돌린다.

실행: uv run python -m scripts.check_deduction_consistency
"""

import json
from pathlib import Path

from rag.graph import build_chain_b_graph

CALIBRATION_PATH = Path("tests/fixtures/calibration_set.json")


def main() -> None:
    cases = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    graph = build_chain_b_graph()

    matched = 0
    mismatches = []
    levels = {}

    print(f"총 {len(cases)}개 케이스로 감점 합계 일치 여부 확인\n")

    for i, case in enumerate(cases, 1):
        result = graph.invoke({"question": case["question"], "answer": case["answer"]})
        ev = result["evaluation_result"]

        deducted = sum(d.points for d in ev.deductions)
        expected = 10 - ev.technical_score
        ok = deducted == expected

        if ok:
            matched += 1
        else:
            mismatches.append((i, ev.technical_score, deducted, expected))

        levels[ev.level] = levels.get(ev.level, 0) + 1

        mark = "OK" if ok else "MISMATCH"
        print(f"[{mark}] Case {i:02d} | score={ev.technical_score} "
              f"감점합={deducted} 기대={expected} | level={ev.level} "
              f"| 감점 {len(ev.deductions)}건")

    total = len(cases)
    print("\n" + "=" * 50)
    print(f"감점 합계 일치: {matched}/{total} ({matched / total * 100:.1f}%)")
    print(f"레벨 분포: {levels}")

    if mismatches:
        print(f"\n불일치 {len(mismatches)}건:")
        for i, score, deducted, expected in mismatches:
            print(f"  Case {i:02d}: score={score}인데 감점합={deducted} (기대 {expected})")


if __name__ == "__main__":
    main()
