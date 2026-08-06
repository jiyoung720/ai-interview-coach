"""Calibration Set v2 실행 (Phase 12).

v1과 달라진 점:
1. 기대 범위를 분기 경계(4점, 7점)에 정렬했다. 그래서 점수 정확도뿐 아니라
   **올바른 코칭 경로로 갔는지**를 함께 잴 수 있다. 실제로 사용자에게 영향을
   주는 것은 몇 점인지가 아니라 어떤 코칭이 나가는지다.
2. 주제를 5개에서 12개로 넓혔다. v1은 KB 18개 문서 중 5개 주제만 검증했다.

실행:
    uv run python -m scripts.run_calibration_v2
    uv run python -m scripts.run_calibration_v2 tests/fixtures/calibration_set.json
"""

from collections import defaultdict
from pathlib import Path

import json

from rag.graph import build_chain_b_graph
from scripts.eval_budget import build_parser, trim_by_args
from rag.graph_nodes import ADVANCED_THRESHOLD, FUNDAMENTALS_THRESHOLD

DEFAULT_PATH = Path("tests/fixtures/calibration_set_v2.json")

# 답변 수준이 어느 코칭 경로로 가야 하는지. 기대 점수 범위와 짝을 이룬다
EXPECTED_ROUTE = {
    "bad": "fundamentals",
    "average": "learning_tip",
    "good": "advanced",
    "technically_correct_but_brief": "advanced",
    "verbose_but_technically_wrong": "fundamentals",
}


def route_of(score: int) -> str:
    if score < FUNDAMENTALS_THRESHOLD:
        return "fundamentals"
    if score >= ADVANCED_THRESHOLD:
        return "advanced"
    return "learning_tip"


def in_range(score: int, rng: list[int]) -> bool:
    return rng[0] <= score <= rng[1]


def main() -> None:
    parser = build_parser()
    parser.add_argument("path", nargs="?", default=str(DEFAULT_PATH), help="캘리브레이션 세트 경로")
    args = parser.parse_args()

    path = Path(args.path)
    cases = json.loads(path.read_text(encoding="utf-8"))
    # 케이스당 채점 1회 + 코칭 노드 1회 정도라 RAGAS만큼 무겁지는 않다
    cases = trim_by_args(cases, calls_per_item=2, args=args)
    graph = build_chain_b_graph()

    score_pass = 0
    route_pass = 0
    by_topic = defaultdict(lambda: [0, 0])   # topic -> [통과, 전체]
    failures = []

    print(f"{path.name}: {len(cases)}개 케이스\n")

    for i, case in enumerate(cases, 1):
        result = graph.invoke({"question": case["question"], "answer": case["answer"]})
        ev = result["evaluation_result"]

        exp = case["expected"]
        ok_score = in_range(ev.technical_score, exp["technical_score"]) and \
            in_range(ev.completeness_score, exp["completeness_score"])

        actual_route = route_of(ev.technical_score)
        want_route = EXPECTED_ROUTE[case["answer_level"]]
        ok_route = actual_route == want_route

        score_pass += ok_score
        route_pass += ok_route
        topic = case.get("topic", "?")
        by_topic[topic][1] += 1
        by_topic[topic][0] += ok_route

        mark = "OK  " if (ok_score and ok_route) else "FAIL"
        print(f"[{mark}] {i:02d} {topic:<22} tech={ev.technical_score:>2} "
              f"comp={ev.completeness_score:>2} level={ev.level:<6} "
              f"경로={actual_route}{'' if ok_route else f' (기대 {want_route})'}")

        if not ok_route:
            failures.append((i, topic, case["answer_level"], ev.technical_score, want_route, actual_route))

    total = len(cases)
    print("\n" + "=" * 60)
    print(f"점수 범위 일치 : {score_pass}/{total} ({score_pass / total * 100:.1f}%)")
    print(f"코칭 경로 일치 : {route_pass}/{total} ({route_pass / total * 100:.1f}%)  <- 사용자 체감에 직결")

    print("\n주제별 경로 정확도:")
    for topic, (ok, n) in sorted(by_topic.items()):
        bar = ".".join("" for _ in range(1))
        print(f"  {topic:<24} {ok}/{n}")

    if failures:
        print(f"\n경로가 어긋난 {len(failures)}건:")
        for i, topic, level, score, want, got in failures:
            print(f"  {i:02d} {topic} [{level}] score={score} -> {got} (기대 {want})")


if __name__ == "__main__":
    main()
