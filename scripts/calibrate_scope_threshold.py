# 범위 밖 질문을 걸러낼 거리 임계값을 정한다 (Phase 17).
#
# 1순위 문서와의 거리가 임계값 이상이면 "고정 지식에 근거가 없다"로 판정한다.
# 임계값을 전체 데이터에서 고르면 그 데이터에 과적합되므로 group 5-fold로 검증한다.
# 같은 주제를 표현만 바꾼 문항이 train과 test에 걸쳐 들어가면 임계값이 실제보다
# 좋아 보이기 때문에, 무작위가 아니라 topic 단위로 묶어 나눈다.
#
# 판정은 결정적이라 재실행 변동이 없다. 남는 불확실성은 표본오차뿐이므로
# LLM 채점에서 잰 변동 폭(약 5%p)을 여기에 끌어다 쓰면 안 된다.
import json
from pathlib import Path

EVAL_SET_PATH = Path("tests/fixtures/retrieval_eval_set.json")
CACHE_PATH = Path("tests/fixtures/scope_distances.json")

# 범위 안 문항을 잘못 막는 것은 지금보다 나빠지는 것이고,
# 범위 밖을 놓치는 것은 현재 동작과 같다. 그래서 오탐부터 억제한다.
MIN_IN_SCOPE_PASS = 0.95   # 범위 안 문항 중 통과시켜야 할 최소 비율


def load_distances(refresh: bool) -> list[dict]:
    """문항별 1순위 거리를 잰다. 임베딩만 쓰고 LLM은 부르지 않는다.

    거리는 임베딩 모델과 KB 내용에 종속된다. 둘 중 하나라도 바뀌면 캐시된 값으로 고른
    임계값은 더 이상 유효하지 않으므로, 평가셋이 달라진 것을 감지하면 다시 재도록 한다.
    """
    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    questions = [c["question"] for c in eval_set]

    if CACHE_PATH.exists() and not refresh:
        cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if [r["question"] for r in cached] == questions:
            return cached
        print("평가셋이 캐시와 다르다. 거리를 다시 측정한다.\n")

    from rag.vectorstore import get_interview_kb_retriever

    vectorstore = get_interview_kb_retriever().vectorstore

    rows = []
    for case in eval_set:
        doc, distance = vectorstore.similarity_search_with_score(case["question"], k=1)[0]
        rows.append({
            "question": case["question"],
            "topic": case["topic"],
            "out_of_scope": case["type"] == "out_of_scope",
            "distance": float(distance),
            "top_source": doc.metadata.get("source"),
        })

    CACHE_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows


def evaluate(rows: list[dict], threshold: float) -> dict:
    """거리 >= 임계값이면 범위 밖으로 판정한다."""
    tp = sum(1 for r in rows if r["out_of_scope"] and r["distance"] >= threshold)
    fn = sum(1 for r in rows if r["out_of_scope"] and r["distance"] < threshold)
    fp = sum(1 for r in rows if not r["out_of_scope"] and r["distance"] >= threshold)
    tn = sum(1 for r in rows if not r["out_of_scope"] and r["distance"] < threshold)

    return {
        "recall": tp / (tp + fn) if tp + fn else 0.0,          # 범위 밖을 잡아낸 비율
        "precision": tp / (tp + fp) if tp + fp else 0.0,       # 범위 밖이라 한 것 중 실제 비율
        "in_scope_pass": tn / (tn + fp) if tn + fp else 0.0,   # 범위 안 문항을 통과시킨 비율
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
    }


def pick_threshold(rows: list[dict]) -> float:
    """오탐을 기준 이하로 억제하면서 범위 밖 재현율이 가장 높은 임계값을 고른다."""
    candidates = sorted({round(r["distance"], 4) for r in rows})
    best, best_recall = None, -1.0

    for t in candidates:
        m = evaluate(rows, t)
        if m["in_scope_pass"] >= MIN_IN_SCOPE_PASS and m["recall"] > best_recall:
            best, best_recall = t, m["recall"]

    # 제약을 만족하는 임계값이 없으면 오탐이 가장 적은 쪽으로 물러선다
    return best if best is not None else max(candidates)


def group_folds(rows: list[dict], k: int = 5) -> list[list[dict]]:
    """topic 단위로 묶어 나눈다. 같은 주제가 train과 test에 걸쳐 들어가지 않게 한다."""
    topics = sorted({r["topic"] for r in rows})
    folds = [[] for _ in range(k)]
    for i, topic in enumerate(topics):
        folds[i % k].extend(r for r in rows if r["topic"] == topic)
    return folds


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="거리를 다시 측정한다 (임베딩 API 사용)")
    args = parser.parse_args()

    rows = load_distances(args.refresh)
    n_out = sum(1 for r in rows if r["out_of_scope"])
    print(f"문항 {len(rows)}개 (범위 밖 {n_out}, 범위 안 {len(rows) - n_out}), 주제 {len({r['topic'] for r in rows})}개\n")

    folds = group_folds(rows)
    print("group 5-fold 교차 검증")
    print(f"{'fold':>5} {'임계값':>8} {'재현율':>8} {'정밀도':>8} {'범위안 통과':>11}")

    test_scores = []
    for i, test in enumerate(folds, 1):
        train = [r for j, f in enumerate(folds, 1) if j != i for r in f]
        t = pick_threshold(train)
        m = evaluate(test, t)
        test_scores.append(m)
        print(f"{i:>5} {t:>8.3f} {m['recall']:>8.1%} {m['precision']:>8.1%} {m['in_scope_pass']:>11.1%}")

    avg = lambda key: sum(m[key] for m in test_scores) / len(test_scores)
    print(f"{'평균':>5} {'':>8} {avg('recall'):>8.1%} {avg('precision'):>8.1%} {avg('in_scope_pass'):>11.1%}")

    final = pick_threshold(rows)
    m = evaluate(rows, final)
    print(f"\n전체 데이터로 고른 임계값: {final:.3f}")
    print(f"  범위 밖 {m['tp']}/{m['tp'] + m['fn']} 잡아냄 (재현율 {m['recall']:.1%})")
    print(f"  범위 안 {m['tn']}/{m['tn'] + m['fp']} 통과 (오탐 {m['fp']}건)")

    missed = sorted((r for r in rows if r["out_of_scope"] and r["distance"] < final),
                    key=lambda r: -r["distance"])
    if missed:
        print(f"\n놓친 범위 밖 문항 {len(missed)}건 (엉뚱한 근거로 채점될 것)")
        for r in missed:
            print(f"  {r['distance']:.3f}  {r['question'][:40]:<42} -> {r['top_source']}")

    wrong = [r for r in rows if not r["out_of_scope"] and r["distance"] >= final]
    if wrong:
        print(f"\n잘못 막은 범위 안 문항 {len(wrong)}건 (채점받아야 하는데 보류될 것)")
        for r in wrong:
            print(f"  {r['distance']:.3f}  {r['question'][:40]:<42} -> {r['top_source']}")


if __name__ == "__main__":
    main()
