# 평가 스크립트가 API를 얼마나 쓸지 미리 알려주고, 스모크 테스트로 줄여 돌릴 수 있게 하는 공용 헬퍼.
#
# RAGAS는 지표 하나를 재는 데도 LLM을 여러 번 부른다. 문항당 답변 생성 1회에
# Faithfulness(문장 분해 + 근거 대조)와 Context Precision(청크 k개 각각 판정)이 붙어
# 대략 6배로 불어나므로, 30문항짜리 전체 실행도 수백 회 호출이 된다.
# 코드를 고친 직후에 전체를 돌렸다가 잔액만 태우는 일을 막으려고 둔다.
import argparse

CALLS_PER_ITEM = 6  # 생성 1 + Faithfulness 2 + Context Precision 3(k=3)


def in_scope_only(cases: list) -> list:
    """범위 밖 문항(Phase 17)을 걸러낸다.

    이들은 정답 문서가 없어 Top-1 정확도를 계산할 수 없고 reference도 없어
    RAGAS를 돌릴 수 없다. 판정은 scripts/calibrate_scope_threshold.py에서 따로 measure한다.
    """
    return [c for c in cases if c.get("type") != "out_of_scope"]


def build_parser() -> argparse.ArgumentParser:
    """--limit/--yes 를 단 파서. 다른 인자가 필요한 스크립트는 여기에 add_argument 해서 쓴다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="앞에서부터 N개만 평가 (스모크 테스트용)")
    parser.add_argument("--yes", action="store_true", help="예상 호출량 확인 없이 실행")
    return parser


def trim_by_args(items: list, multiplier: int = 1, calls_per_item: int = CALLS_PER_ITEM, args=None) -> list:
    """--limit / --yes 를 해석해 평가 대상을 잘라 돌려준다.

    multiplier: 같은 세트를 여러 번 도는 경우의 배수 (임베딩 2종 비교면 2)
    args: 스크립트가 이미 파싱해둔 결과. 없으면 여기서 파싱한다.
    호출량이 적으면 굳이 묻지 않고 그냥 진행한다.
    """
    if args is None:
        args = build_parser().parse_args()

    if args.limit:
        items = items[: args.limit]

    estimated = len(items) * multiplier * calls_per_item
    print(f"평가 대상: {len(items)}개 -> 예상 LLM 호출 약 {estimated}회")

    if not args.yes and estimated > 100:
        if input("계속하시겠습니까? [y/N] ").strip().lower() != "y":
            raise SystemExit("중단했습니다.")

    return items
