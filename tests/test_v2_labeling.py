"""라벨링 파이프라인 (M1 B5). API 키 없이 레포의 실제 캘리브레이션 데이터로 돈다."""
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.labeling import create_labeling_router
from app.main import create_app
from core.config import load_settings
from rag.v2.labeling import (
    ARCHIVE_DIR, BLIND_MAP, HUMAN_LABELS, REVIEW_QUEUE, CodexLabels, LabelingError, build_review_queue,
    check_run, empty_human, export_bundle, finalize, intended_units, load_dataset, lock_actions, make_blind_map,
    project_section, read_json, relabel_ready_at, self_agreement, set_action, set_judgement, set_relabel, write_json,
)

REPO = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 12, 1, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def ds():
    return load_dataset(REPO)


def copy_data(dst: Path) -> Path:
    for rel in ("kb_v2", "data_v2", "eval_v2/concept_cases.yaml", "eval_v2/experience_cases.yaml"):
        src = REPO / rel
        if src.is_dir():
            shutil.copytree(src, dst / rel)
        else:
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst / rel)
    return dst


def codex_like_intended(ds, blind) -> dict:
    """의도 라벨을 그대로 Codex 라벨 형식으로 옮긴 것 (전부 일치하는 경우)."""
    to_blind = {cid: bid for bid, cid in blind["map"].items()}
    items = []
    for c in ds.concept:
        items.append({"id": to_blind[c.case_id], "core": dict(c.intended.core),
                      "side": {s.side_id: s.expected for s in c.intended.side}})
    for c in ds.experience:
        items.append({"id": to_blind[c.case_id], "rubric": dict(c.intended.rubric),
                      "contradiction": c.intended.contradiction,
                      "contradiction_quotes": list(c.intended.contradiction_quotes or []) or None})
    return {"run_id": blind["run_id"], "items": items}


def item_of(codex: dict, blind: dict, case_id: str) -> dict:
    bid = {c: b for b, c in blind["map"].items()}[case_id]
    return next(i for i in codex["items"] if i["id"] == bid)


@pytest.fixture
def run(tmp_path, ds):
    """export → Codex(의도와 같되 es01_missing c1만 다름) → 대기열. (root, blind, queue)"""
    root = copy_data(tmp_path / "repo")
    blind = export_bundle(root, tmp_path / "bundle")
    codex = codex_like_intended(ds, blind)
    item_of(codex, blind, "es01_missing")["core"]["c1"] = "met"
    queue = build_review_queue(ds, blind, CodexLabels.model_validate(codex))
    write_json(root / REVIEW_QUEUE, queue)
    return root, blind, queue


def locked_human(ds, run_id, at=NOW) -> dict:
    human = empty_human(run_id)
    for cid in ds.case_ids:
        set_action(human, ds.case_ids, cid, "next", at)
    lock_actions(human, ds.case_ids, at)
    return human


# ---------------------------------------------------------------- 블라인드 꾸러미와 실행

def test_블라인드_꾸러미에는_정답과_유형이_없다(tmp_path, ds):
    root = copy_data(tmp_path)
    blind = export_bundle(root, tmp_path / "bundle")
    text = (tmp_path / "bundle" / "blind.json").read_text(encoding="utf-8")
    for key in ('"intended"', '"rationale"', '"kind"', '"quality"', '"case_id"', '"pair_id"', '"expected"',
                '"group"', "expected_evidence_doc"):
        assert key not in text, key
    for case_id in blind["map"].values():
        assert f'"{case_id}"' not in text   # es01_missing 같은 ID에 유형이 드러난다
    assert json.loads(text)["run_id"] == blind["run_id"]
    kb = (tmp_path / "bundle" / "kb" / "chunking.md").read_text(encoding="utf-8")
    assert not kb.startswith("---") and "ParentDocumentRetriever (API reference)" not in kb


def test_중립_ID는_시드로_고정되고_유형별로_몰리지_않는다(ds):
    a, b = make_blind_map(ds), make_blind_map(ds)
    assert a == b
    assert len({a[f"C{i:03d}"].split("_", 1)[1] for i in range(1, 11)}) > 1


def test_경험_항목에는_프로젝트_섹션_전체를_넘긴다(ds):
    profile = ds.profiles["sample_eval"]
    eq1 = next(q for q in profile.experience_questions if q.id == "eq1")
    section = project_section(ds.resumes["sample_eval"], eq1.resume_span)
    assert "같은 100건으로 다시 비교해" in section          # 질문의 resume_span 밖에 있는 모순 근거
    assert "FAQ 봇" not in section and "## 프로젝트" not in section


def test_내보낸_뒤_입력이_바뀌면_병합을_거부한다(run):
    root, blind, queue = run
    path = root / "eval_v2/concept_cases.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("잘 모르겠습니다", "모르겠습니다", 1), encoding="utf-8")
    with pytest.raises(LabelingError, match="입력 데이터"):
        check_run(root, blind, queue)


def test_사람_작업이_시작된_실행은_새_실행으로만_바꾼다(run, ds, tmp_path):
    root, blind, queue = run
    human = empty_human(blind["run_id"])
    set_action(human, ds.case_ids, ds.case_ids[0], "probe", NOW)
    write_json(root / HUMAN_LABELS, human)
    path = root / "eval_v2/concept_cases.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("잘 모르겠습니다", "모르겠습니다", 1), encoding="utf-8")
    with pytest.raises(LabelingError, match="--new-run"):
        export_bundle(root, tmp_path / "bundle2")
    new = export_bundle(root, tmp_path / "bundle2", new_run=True)
    assert new["run_id"] != blind["run_id"]
    archived = root / ARCHIVE_DIR / blind["run_id"]
    assert (archived / "human_labels.json").exists() and not (root / HUMAN_LABELS).exists()


# ---------------------------------------------------------------- Codex 라벨 읽기와 비교

def test_Codex_형식_오류는_모아서_거부한다(run, ds):
    root, blind, _ = run
    codex = codex_like_intended(ds, blind)
    codex["items"].append(dict(codex["items"][0]))                       # 중복 ID
    codex["items"].append({"id": "C999", "core": {"c1": "met"}})          # 없는 ID
    codex["items"][1]["core"]["c9"] = "met"                               # 없는 항목
    with pytest.raises(LabelingError) as error:
        build_review_queue(ds, blind, CodexLabels.model_validate(codex))
    message = str(error.value)
    assert "중복 ID" in message and "없는 ID: C999" in message and "core.c9" in message

    codex = codex_like_intended(ds, blind)
    codex["run_id"] = "oldrun"
    with pytest.raises(LabelingError, match="run_id"):
        build_review_queue(ds, blind, CodexLabels.model_validate(codex))


def test_누락_잘못된_값_인용_없는_모순은_사유와_함께_불일치다(run, ds):
    _, blind, _ = run
    codex = codex_like_intended(ds, blind)
    del item_of(codex, blind, "es01_missing")["core"]["c2"]
    item_of(codex, blind, "rag_eq1_vague")["rubric"]["decision_basis"] = "maybe"
    item_of(codex, blind, "agent_eq3_contradiction")["contradiction_quotes"] = ["답변에 없는 문장", "이력서에 없는 문장"]
    queue = build_review_queue(ds, blind, CodexLabels.model_validate(codex))
    reasons = {d["unit"]: d["reason"] for d in queue["disagreements"]}
    assert reasons == {
        "es01_missing#core.c2": "missing",
        "rag_eq1_vague#rubric.decision_basis": "invalid_value",
        # 의도도 true지만 Codex의 인용이 원문에 없으면 일치로 치지 않는다
        "agent_eq3_contradiction#contradiction": "quotes_invalid",
    }


def test_표본은_시드로_고정되고_비율을_지킨다(run, ds):
    _, blind, _ = run
    codex = CodexLabels.model_validate(codex_like_intended(ds, blind))
    q1, q2 = build_review_queue(ds, blind, codex), build_review_queue(ds, blind, codex)
    assert q1 == q2
    assert len(q1["samples"]) == -(-q1["counts"]["agree"] * 15 // 100)
    assert len(q1["relabel"]) == -(-len(blind["map"]) * 20 // 100)


# ---------------------------------------------------------------- 사람 작업 순서와 범위

def test_판정_검수는_다음_행동을_잠근_뒤에만_배정된_단위만_받는다(run, ds):
    _, blind, queue = run
    human = empty_human(blind["run_id"])
    with pytest.raises(LabelingError, match="잠근 뒤"):
        set_judgement(ds, human, queue, "es01_missing#core.c1", "missing", NOW)
    with pytest.raises(LabelingError, match="남았습니다"):
        lock_actions(human, ds.case_ids, NOW)

    human = locked_human(ds, blind["run_id"])
    with pytest.raises(LabelingError, match="잠겼습니다"):
        set_action(human, ds.case_ids, ds.case_ids[0], "probe", NOW)
    unassigned = next(u for u in intended_units(ds) if u not in {"es01_missing#core.c1"}
                      and u not in {s["unit"] for s in queue["samples"]})
    with pytest.raises(LabelingError, match="배정되지 않은"):
        set_judgement(ds, human, queue, unassigned, "met", NOW)


def test_확정은_배정_밖_판정을_무시하고_완료_여부를_구분한다(run, ds):
    _, blind, queue = run
    human = locked_human(ds, blind["run_id"])
    final = finalize(ds, queue, human)
    assert final["unresolved"] == ["es01_missing#core.c1"] and not final["complete"]

    set_judgement(ds, human, queue, "es01_missing#core.c1", "met", NOW)
    set_judgement(ds, human, queue, "es01_missing#core.c1", "missing", NOW)   # 후보를 본 뒤 고침
    assert human["judgements"]["es01_missing#core.c1"]["first_label"] == "met"
    unassigned = next(u for u in intended_units(ds) if u.endswith("#core.c1")
                      and u not in {s["unit"] for s in queue["samples"]} and u != "es01_missing#core.c1")
    human["judgements"][unassigned] = {"label": "wrong", "note": "", "at": "t", "first_label": "wrong"}  # 파일을 직접 고친 경우
    final = finalize(ds, queue, human)
    assert final["units"][unassigned] == intended_units(ds)[unassigned]
    assert final["units"]["es01_missing#core.c1"] == "missing" and not final["complete"]   # 표본 검수가 남았다

    for s in queue["samples"]:
        label = "true" if s["label"] == "true" else s["label"]
        case_id = s["unit"].split("#")[0]
        quotes = list(ds.case(case_id).intended.contradiction_quotes or []) if label == "true" else None
        set_judgement(ds, human, queue, s["unit"], label, NOW, quotes=quotes)
    assert finalize(ds, queue, human)["complete"]


def test_사람이_모순으로_판정하려면_원문_인용_두_개가_필요하다(run, ds, tmp_path):
    root, blind, _ = run
    codex = codex_like_intended(ds, blind)
    item_of(codex, blind, "rag_eq1_vague")["contradiction"] = True
    item_of(codex, blind, "rag_eq1_vague")["contradiction_quotes"] = ["x", "y"]
    queue = build_review_queue(ds, blind, CodexLabels.model_validate(codex))
    human = locked_human(ds, blind["run_id"])
    unit = "rag_eq1_vague#contradiction"
    with pytest.raises(LabelingError, match="원문 그대로"):
        set_judgement(ds, human, queue, unit, "true", NOW)
    answer = ds.case("rag_eq1_vague").answer
    set_judgement(ds, human, queue, unit, "true", NOW,
                  quotes=[answer[:20], "같은 50문항으로 비교해"])
    assert finalize(ds, queue, human)["contradiction_quotes"][unit][1] == "같은 50문항으로 비교해"


def test_재라벨링은_답변마다_첫_라벨_1주_뒤에_열린다(run, ds):
    _, blind, queue = run
    old, new = queue["relabel"][0], queue["relabel"][1]
    human = empty_human(blind["run_id"])
    for cid in ds.case_ids:
        set_action(human, ds.case_ids, cid, "next", NOW - timedelta(days=8) if cid == old else NOW)
    lock_actions(human, ds.case_ids, NOW)
    set_relabel(human, queue, old, "probe", NOW)
    with pytest.raises(LabelingError, match="1주 뒤"):
        set_relabel(human, queue, new, "probe", NOW)            # 전체에서 가장 이른 시각이 아니라 이 답변 기준
    assert relabel_ready_at(human, new) == NOW + timedelta(days=7)
    not_target = next(c for c in ds.case_ids if c not in queue["relabel"])
    with pytest.raises(LabelingError, match="대상이 아닙니다"):
        set_relabel(human, queue, not_target, "probe", NOW + timedelta(days=30))
    assert self_agreement(human) == {"same": 0, "total": 1, "rate": 0.0}


# ---------------------------------------------------------------- 화면 API

@pytest.fixture
def client(run):
    root, blind, queue = run
    app = FastAPI()
    app.include_router(create_labeling_router(root))
    return TestClient(app), root, {c: b for b, c in blind["map"].items()}


def test_다음_행동_화면은_판정_정보를_보내지_않고_잠그면_닫힌다(client, ds):
    c, root, to_blind = client
    assert c.get("/labeling/api/judge", params={"queue": "disagreement"}).status_code == 409   # 잠그기 전
    rows = c.get("/labeling/api/actions").json()
    body = json.dumps(rows, ensure_ascii=False)
    assert "side_claims\": []" in body or "side_claims" not in body
    for word in ('"intended"', '"candidates"', "es01_missing"):
        assert word not in body
    assert all(r["item"].get("side_claims", []) == [] for r in rows)

    assert c.post("/labeling/api/actions/lock").status_code == 409                 # 다 붙이기 전
    for bid in to_blind.values():
        assert c.post("/labeling/api/actions", json={"id": bid, "action": "next"}).status_code == 200
    assert c.post("/labeling/api/actions/lock").status_code == 200
    assert c.get("/labeling/api/actions").status_code == 409                       # 이전 선택이 다시 보이지 않게
    assert c.post("/labeling/api/actions", json={"id": to_blind["es01_missing"], "action": "probe"}).status_code == 409


def test_판정_후보는_먼저_고른_뒤에만_보인다(client, ds):
    c, root, to_blind = client
    write_json(root / HUMAN_LABELS, locked_human(ds, read_json(root / BLIND_MAP)["run_id"]))
    rows = c.get("/labeling/api/judge", params={"queue": "disagreement"}).json()
    assert len(rows) == 1 and rows[0]["candidates"] is None and rows[0]["reason"] is None
    assert "es01_missing" not in json.dumps(rows, ensure_ascii=False)
    key = rows[0]["key"]
    assert key == f"{to_blind['es01_missing']}#core.c1"
    assert c.post("/labeling/api/judge", json={"key": key, "label": "nope"}).status_code == 400
    assert c.post("/labeling/api/judge", json={"key": key, "label": "wrong"}).status_code == 200
    row = c.get("/labeling/api/judge", params={"queue": "disagreement"}).json()[0]
    assert sorted(row["candidates"]) == ["met", "missing"] and row["reason"] == "different"

    sample = c.get("/labeling/api/judge", params={"queue": "sample"}).json()[0]
    assert sample["candidates"] is None
    # 배정되지 않은 단위는 화면 API로도 저장할 수 없다
    other = f"{to_blind['es01_solid']}#core.c1"
    if other.replace(to_blind["es01_solid"], "es01_solid") not in {s["unit"] for s in read_json(root / REVIEW_QUEUE)["samples"]}:
        assert c.post("/labeling/api/judge", json={"key": other, "label": "met"}).status_code == 400


def test_루프백이_아닌_요청은_거부한다(run):
    root, _, _ = run
    app = FastAPI()
    app.include_router(create_labeling_router(root))
    remote = TestClient(app, client=("10.0.0.5", 50000))
    assert remote.get("/labeling/api/state").status_code == 403


def test_데모_모드에는_라벨링_화면이_없다(tmp_path):
    settings = load_settings({"SECRET_KEY": "test-secret", "DATA_DIR": str(tmp_path)})
    with TestClient(create_app(settings)) as c:
        assert c.get("/labeling").status_code == 404
        assert c.get("/labeling/api/state").status_code == 404


def test_로컬_모드는_라벨링_화면을_등록한다(tmp_path):
    settings = load_settings({"APP_MODE": "local", "DATA_DIR": str(tmp_path)})
    paths = set(create_app(settings).openapi()["paths"])
    assert {"/labeling", "/labeling/api/judge", "/labeling/api/actions", "/labeling/api/relabel"} <= paths
