"""Codex 독립 라벨용 블라인드 꾸러미를 만든다 (M1 B5).

꾸러미에는 답변·질문·핵심 주장·고정된 질문 밖 주장 인용·KB 본문만 들어가고,
의도 라벨·rationale·kind·quality·case_id는 없다. Codex가 레포의 정답 파일을 읽지 못하게,
꾸러미 폴더를 레포 밖으로 복사해서 그 안에서 돌린다.

입력 데이터의 해시로 실행 ID를 정한다. 사람 작업이 시작된 뒤 입력이 바뀌었으면 거부하고,
새로 시작하려면 --new-run으로 기존 파일을 eval_v2/labels/archive/<run_id>/로 옮긴다.

실행:
    uv run python -m scripts.v2.export_for_codex [--out eval_v2/labels/codex_bundle] [--new-run]
결과를 eval_v2/labels/codex_labels.json으로 저장한 뒤 merge_labels를 돌린다.
"""
import argparse
from pathlib import Path

from rag.v2.labeling import LabelingError, export_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("eval_v2/labels/codex_bundle"))
    parser.add_argument("--new-run", action="store_true")
    args = parser.parse_args()
    try:
        blind = export_bundle(Path("."), args.out, new_run=args.new_run)
    except LabelingError as error:
        print(error)
        return 1
    mapping = blind["map"]
    concept = sum(k.startswith("C") for k in mapping)
    print(f"실행 {blind['run_id']} 꾸러미: {args.out} (개념 {concept}건, 경험 {len(mapping) - concept}건)")
    print("이 폴더를 레포 밖으로 복사해 Codex에 INSTRUCTIONS.md대로 라벨링을 맡기고,")
    print("결과를 eval_v2/labels/codex_labels.json으로 저장하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
