import json
from pathlib import Path

from rag.graph import build_chain_b_graph

CALIBRATION_PATH = Path("tests/fixtures/calibration_set.json")


def check_in_range(score: int, expected_range: list[int]) -> bool:
    return expected_range[0] <= score <= expected_range[1]


def run_calibration():
    calibration_set = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    graph = build_chain_b_graph()

    passed = 0
    results = []

    print(f"[LangGraph 버전] 총 {len(calibration_set)}개 케이스 실행 중...\n")

    for i, case in enumerate(calibration_set, 1):
        question = case["question"]
        answer = case["answer"]
        answer_level = case["answer_level"]
        expected = case["expected"]

        state = graph.invoke({"question": question, "answer": answer})
        evaluation = state["evaluation_result"]

        t_score = evaluation.technical_score
        c_score = evaluation.completeness_score
        t_pass = check_in_range(t_score, expected["technical_score"])
        c_pass = check_in_range(c_score, expected["completeness_score"])
        case_passed = t_pass and c_pass

        if case_passed:
            passed += 1

        status = "✅" if case_passed else "❌"
        print(f"{status} Case {i:02d} [{answer_level}]")
        print(f"   technical:    {t_score:2d}  (expected {expected['technical_score']})  {'✅' if t_pass else '❌'}")
        print(f"   completeness: {c_score:2d}  (expected {expected['completeness_score']})  {'✅' if c_pass else '❌'}")
        print()

        results.append({"case": i, "answer_level": answer_level, "passed": case_passed})

    print("=" * 50)
    print(f"[LangGraph 버전] 결과: {passed}/{len(calibration_set)} 통과")
    print(f"정확도: {passed / len(calibration_set) * 100:.1f}%")

    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n❌ 실패 케이스 ({len(failed)}개):")
        for r in failed:
            print(f"   Case {r['case']:02d} [{r['answer_level']}]")


if __name__ == "__main__":
    run_calibration()
