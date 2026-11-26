"""의도 라벨과 Codex 라벨을 비교해 판정 대기열을 만들고, 사람 작업이 끝나면 확정 라벨을 만든다 (M1 B5).

실행:
    uv run python -m scripts.v2.merge_labels            # review_queue.json 생성 (불일치 + 일치 15% 표본 + 재라벨링 20%)
    uv run python -m scripts.v2.merge_labels --finalize # final_labels.json 생성 (사람 판정 반영)

대기열·대응표·사람 판정은 같은 실행 ID로 묶인다. 사람 작업이 시작된 실행의 대기열은 다시 만들지 않는다.
다시 시작하려면 export_for_codex --new-run으로 새 실행을 연다.
"""
import argparse
from pathlib import Path

from pydantic import ValidationError

from rag.v2.labeling import (
    BLIND_MAP, CODEX_LABELS, FINAL_LABELS, HUMAN_LABELS, REVIEW_QUEUE, CodexLabels, LabelingError,
    build_review_queue, check_run, empty_human, finalize, load_dataset, read_json, self_agreement, write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    root = Path(".")
    try:
        return run(root, args.finalize)
    except LabelingError as error:
        print(error)
        return 1


def run(root: Path, do_finalize: bool) -> int:
    ds = load_dataset(root)
    blind = read_json(root / BLIND_MAP)
    if blind is None:
        raise LabelingError("blind_map.json이 없습니다. export_for_codex부터 돌리세요.")

    if do_finalize:
        queue = read_json(root / REVIEW_QUEUE)
        if queue is None:
            raise LabelingError("review_queue.json이 없습니다. 먼저 merge_labels를 돌리세요.")
        human = read_json(root / HUMAN_LABELS, empty_human(blind["run_id"]))
        check_run(root, blind, queue, human)
        final = finalize(ds, queue, human)
        final["self_agreement"] = self_agreement(human)
        write_json(root / FINAL_LABELS, final)
        check = final["sample_check"]
        print(f"{'완료' if final['complete'] else '미완료'}: 확정 {len(final['units'])}개, "
              f"미판정 불일치 {len(final['unresolved'])}개")
        print(f"일치 표본 검수 {check['reviewed']}/{check['total']}, 그중 바뀐 것 {len(check['changed'])}개")
        print(f"다음 행동 {len(final['actions'])}건 (잠금 {'됨' if final['actions_locked'] else '안 됨'}), "
              f"자기 일치도 {final['self_agreement']}")
        return 0 if final["complete"] else 1

    codex_raw = read_json(root / CODEX_LABELS)
    if codex_raw is None:
        raise LabelingError("codex_labels.json이 없습니다. 꾸러미를 Codex에 맡기고 결과를 저장하세요.")
    human = read_json(root / HUMAN_LABELS)
    check_run(root, blind, human)
    if human and (human["actions"] or human["judgements"] or human["relabel"]):
        raise LabelingError("이 실행에서 사람 작업이 이미 시작돼 대기열을 다시 만들지 않습니다. "
                            "새로 시작하려면 export_for_codex --new-run.")
    try:
        codex = CodexLabels.model_validate(codex_raw)
    except ValidationError as error:
        missing = [".".join(map(str, e["loc"])) for e in error.errors()]
        raise LabelingError(f"codex_labels.json 형식 오류 (빠지거나 잘못된 필드: {missing}). "
                            "run_id는 꾸러미 blind.json의 run_id와 같아야 합니다.")
    queue = build_review_queue(ds, blind, codex)
    write_json(root / REVIEW_QUEUE, queue)
    c = queue["counts"]
    reasons = {}
    for d in queue["disagreements"]:
        reasons[d["reason"]] = reasons.get(d["reason"], 0) + 1
    print(f"실행 {queue['run_id']}: 라벨 단위 {c['units']}개, 일치 {c['agree']}, 불일치 {c['disagree']} {reasons}")
    print(f"사람 판정: 불일치 {len(queue['disagreements'])} + 일치 표본 {len(queue['samples'])}")
    print(f"다음 행동 재라벨링 대상 {len(queue['relabel'])}건 (답변별 첫 라벨 1주 뒤)")
    print("라벨링 화면: APP_MODE=local uv run uvicorn app.main:app --host 127.0.0.1 → http://127.0.0.1:8000/labeling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
