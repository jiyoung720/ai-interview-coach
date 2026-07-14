import json
from pathlib import Path

from rag.chains import get_chain_b

CALIBRATION_PATH = Path("tests/fixtures/calibration_set.json")

# 지난 실행에서 completeness가 기대보다 낮게 나왔던 케이스 번호 (1-indexed)
TARGET_CASES = [2, 3, 8, 9]


def check_in_range(score: int, expected_range: list[int]) -> bool:
    return expected_range[0] <= score <= expected_range[1]


def main():
    calibration_set = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    chain_b = get_chain_b()

    for case_num in TARGET_CASES:
        case = calibration_set[case_num - 1]
        result = chain_b.invoke({"question": case["question"], "answer": case["answer"]})

        print(f"{'=' * 60}")
        print(f"Case {case_num} [{case['answer_level']}]")
        print(f"Q: {case['question']}")
        print(f"A: {case['answer']}")
        print(f"기대 completeness: {case['expected']['completeness_score']}")
        print(f"실제 completeness: {result['completeness_score']}")
        print(f"\nstrengths:")
        for s in result["strengths"]:
            print(f"  - {s}")
        print(f"\nimprovements:")
        for imp in result["improvements"]:
            print(f"  - {imp}")
        print(f"\noverall_feedback: {result['overall_feedback']}")
        print()


if __name__ == "__main__":
    main()
