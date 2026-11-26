"""로컬 전용 라벨링 화면 API (M1 B5). 데모 모드에는 등록하지 않는다 (app/main.py).

작업 순서 (순서와 범위는 rag/v2/labeling.py가 강제한다)
1. actions: 다음 행동 라벨. 판정 라벨·후보·규칙 결과를 보여 주지 않는다 (설계 §6.4 2-1). 모두 붙이면 잠근다.
2. judge: 잠근 뒤에만 열린다. 배정된 단위(불일치 + 일치 15% 표본)만.
   후보는 사람이 먼저 한 번 고른 뒤에만 보여 준다 (후보를 보고 따라 고르지 않게).
3. relabel: 답변마다 첫 라벨 1주 뒤에 열리고, 이전 선택을 보여 주지 않는다. 잠근 뒤에는 첫 라벨 화면도 닫힌다.

화면에는 case_id 대신 중립 ID(C001 등)만 나간다. case_id에 답변 유형이 드러나기 때문이다.
판정 파일을 레포에 쓰므로 루프백(127.0.0.1)에서 온 요청만 받는다.
"""
import random
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from rag.v2.labeling import (
    ACTIONS, BLIND_MAP, HUMAN_LABELS, REVIEW_QUEUE, SEED, LabelingError, OrderError, blind_item, check_run, empty_human,
    load_dataset, lock_actions, now_utc, read_json, relabel_ready_at, set_action, set_judgement, set_relabel,
    strip_frontmatter, unit_options, write_json,
)

PAGE = Path(__file__).resolve().parent.parent / "static" / "labeling.html"
LOOPBACK = {"127.0.0.1", "::1", "localhost", "testclient"}


def loopback_only(request: Request) -> None:
    host = request.client.host if request.client else None
    if host not in LOOPBACK:
        raise HTTPException(403, "라벨링 화면은 이 컴퓨터(127.0.0.1)에서만 열 수 있습니다")


class JudgeIn(BaseModel):
    key: str                        # "C017#core.c1"
    label: str
    note: str = ""
    quotes: list[str] | None = None  # 모순 true일 때 [답변 문장, 이력서 문장]


class ActionIn(BaseModel):
    id: str                         # "C017"
    action: str


def create_labeling_router(root: Path) -> APIRouter:
    router = APIRouter(prefix="/labeling", dependencies=[Depends(loopback_only)])
    lock = threading.Lock()

    def context():
        blind = read_json(root / BLIND_MAP)
        queue = read_json(root / REVIEW_QUEUE)
        if blind is None or queue is None:
            raise HTTPException(409, "대기열이 없습니다. export_for_codex → Codex 라벨링 → merge_labels 순서로 준비하세요.")
        human = read_json(root / HUMAN_LABELS, empty_human(blind["run_id"]))
        try:
            check_run(root, blind, queue, human)
        except LabelingError as error:
            raise HTTPException(409, str(error))
        mapping = blind["map"]
        return load_dataset(root), mapping, {c: b for b, c in mapping.items()}, queue, human

    def save(human: dict, change) -> None:
        try:
            change()
        except OrderError as error:
            raise HTTPException(409, str(error))
        except LabelingError as error:
            raise HTTPException(400, str(error))
        write_json(root / HUMAN_LABELS, human)

    def real_unit(key: str, mapping: dict) -> str:
        blind_id, _, part = key.partition("#")
        if blind_id not in mapping or not part:
            raise HTTPException(404, "없는 항목입니다")
        return f"{mapping[blind_id]}#{part}"

    @router.get("")
    def page():
        return FileResponse(PAGE)

    @router.get("/api/state")
    def state():
        ds, mapping, _, queue, human = context()
        judged = human["judgements"]
        dis = [d["unit"] for d in queue["disagreements"]]
        smp = [s["unit"] for s in queue["samples"]]
        now = now_utc()
        ready = [c for c in queue["relabel"] if (t := relabel_ready_at(human, c)) and t <= now]
        return {
            "locked": bool(human["actions_locked_at"]),
            "actions": {"done": len(human["actions"]), "total": len(mapping)},
            "disagreement": {"done": sum(u in judged for u in dis), "total": len(dis)},
            "sample": {"done": sum(u in judged for u in smp), "total": len(smp)},
            "relabel": {"done": len(human["relabel"]), "total": len(queue["relabel"]), "ready": len(ready)},
            "action_labels": ACTIONS,
        }

    @router.get("/api/kb")
    def kb_docs():
        # 질문 밖 주장 판정용. 기대 근거 문서를 알려 주면 힌트가 되므로 전체 본문을 주고 사람이 고른다.
        return {p.stem: strip_frontmatter(p.read_text(encoding="utf-8"))
                for p in sorted((root / "kb_v2/docs").glob("*.md"))}

    # ------------------------------------------------------------ 1. 다음 행동

    @router.get("/api/actions")
    def action_items():
        ds, mapping, _, _, human = context()
        if human["actions_locked_at"]:
            raise HTTPException(409, "다음 행동 라벨은 잠겼습니다")
        return [{"id": bid, "item": blind_item(ds, bid, cid, sides=[]),
                 "decided": (human["actions"].get(cid) or {}).get("action")} for bid, cid in mapping.items()]

    @router.post("/api/actions")
    def act(body: ActionIn):
        with lock:
            ds, mapping, _, _, human = context()
            if body.id not in mapping:
                raise HTTPException(404, "없는 항목입니다")
            save(human, lambda: set_action(human, ds.case_ids, mapping[body.id], body.action, now_utc()))
        return {"ok": True}

    @router.post("/api/actions/lock")
    def lock_first_actions():
        with lock:
            ds, _, _, _, human = context()
            save(human, lambda: lock_actions(human, ds.case_ids, now_utc()))
        return {"ok": True}

    # ------------------------------------------------------------ 2. 판정 검수

    @router.get("/api/judge")
    def judge_items(queue: str):
        ds, mapping, to_blind, q, human = context()
        if not human["actions_locked_at"]:
            raise HTTPException(409, "다음 행동 라벨을 모두 붙이고 잠근 뒤에 판정 검수를 합니다")
        if queue == "disagreement":
            rows = q["disagreements"]
        elif queue == "sample":
            rows = q["samples"]
        else:
            raise HTTPException(400, "queue는 disagreement 또는 sample입니다")
        out = []
        for row in rows:
            unit = row["unit"]
            case_id, part = unit.split("#", 1)
            key = f"{to_blind[case_id]}#{part}"
            decided = human["judgements"].get(unit)
            entry = {
                "key": key,
                "item": blind_item(ds, to_blind[case_id], case_id,
                                   sides=[part.removeprefix("side.")] if part.startswith("side.") else []),
                "target": part,
                "options": unit_options(unit),
                "decided": decided,
                "candidates": None,
                "reason": None,
            }
            if decided:   # 먼저 고른 뒤에만 후보를 보여 준다
                if queue == "disagreement":
                    cands = [c for c in {row["intended"], row["codex"]} if c]
                    random.Random(f"{SEED}:{key}").shuffle(cands)   # 순서로 출처가 드러나지 않게
                    entry["candidates"], entry["reason"] = cands, row["reason"]
                else:
                    entry["candidates"] = [row["label"]]
            out.append(entry)
        return out

    @router.post("/api/judge")
    def judge(body: JudgeIn):
        with lock:
            ds, mapping, _, q, human = context()
            unit = real_unit(body.key, mapping)
            save(human, lambda: set_judgement(ds, human, q, unit, body.label, now_utc(), body.note, body.quotes))
        return {"ok": True}

    # ------------------------------------------------------------ 3. 재라벨링

    @router.get("/api/relabel")
    def relabel_items():
        ds, _, to_blind, q, human = context()
        now = now_utc()
        out = []
        for cid in q["relabel"]:
            ready = relabel_ready_at(human, cid)
            if ready and ready <= now:
                bid = to_blind[cid]
                # 이전 선택(actions)은 보내지 않는다
                out.append({"id": bid, "item": blind_item(ds, bid, cid, sides=[]),
                            "decided": (human["relabel"].get(cid) or {}).get("action")})
        return sorted(out, key=lambda r: r["id"])

    @router.post("/api/relabel")
    def relabel(body: ActionIn):
        with lock:
            _, mapping, _, q, human = context()
            if body.id not in mapping:
                raise HTTPException(404, "없는 항목입니다")
            save(human, lambda: set_relabel(human, q, mapping[body.id], body.action, now_utc()))
        return {"ok": True}

    return router
