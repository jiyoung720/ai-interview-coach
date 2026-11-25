"""v2 데이터 검사기 (M1 B1).

작은 테스트용 데이터로 검사기가 잡아야 할 오류를 하나씩 확인하고, 마지막에 실제 레포
데이터를 검사한다(실제 레포 검사가 CI에서 데이터 오류를 잡는 장치다).
"""
from datetime import date
from pathlib import Path

import pytest
import yaml

from scripts.v2.check_data import check

TODAY = date(2026, 11, 23)

KB_DOC = """---
topic: chunking
area: retrieval
difficulty: basic
sources:
  - title: 예시 출처
    url: https://example.com
last_reviewed: 2026-11-01
---
# Chunking

chunk가 크면 한 chunk에 더 많은 문맥이 담긴다.
chunk가 크면 관련 없는 내용이 섞여 검색 정밀도가 떨어진다.
"""

BANK = {"questions": [
    {
        "id": "chunking_01", "topic": "chunking",
        "question": "chunk 크기를 키우면 무엇이 달라지나요?",
        "key_claims": [
            {"claim_id": "c1", "text": "문맥이 더 담긴다",
             "evidence": "chunk가 크면 한 chunk에 더 많은 문맥이 담긴다.", "evidence_doc": "chunking"},
            {"claim_id": "c2", "text": "정밀도가 떨어진다",
             "evidence": "chunk가 크면 관련 없는 내용이 섞여 검색 정밀도가 떨어진다.", "evidence_doc": "chunking"},
        ],
        "kb_doc_ids": ["chunking"],
        "claim_followups": [{"claim_id": "c2", "question": "정밀도에는 어떤 영향이 있나요?"}],
        "deeper": ["chunking_02"],
    },
    {
        "id": "chunking_02", "topic": "chunking", "question": "overlap은 왜 두나요?",
        "key_claims": [{"claim_id": "c1", "text": "문맥", "evidence": "chunk가 크면 한 chunk에 더 많은 문맥이 담긴다.",
                        "evidence_doc": "chunking"}],
        "kb_doc_ids": ["chunking"],
    },
]}

RUBRIC = {"items": [
    {"id": "decision_basis", "name": "의사결정 근거", "observed_when": "왜 그렇게 했는지 말한다"},
    {"id": "outcome", "name": "결과·측정", "observed_when": "결과를 어떻게 확인했는지 말한다"},
]}

RESUME = "# 합성 이력서 A\n\n- RAG 기반 사내 문서 검색 챗봇을 만들었다. 임베딩 모델을 교체해 정확도를 올렸다.\n"

PROFILE = {
    "sample_id": "sample_a",
    "summary": "RAG 챗봇 경험",
    "projects": [{"id": "p1", "name": "문서 검색 챗봇", "role": "개발", "tech": ["RAG"],
                  "resume_span": "RAG 기반 사내 문서 검색 챗봇을 만들었다."}],
    "experience_questions": [{"id": "eq1", "project_id": "p1", "question": "임베딩을 왜 바꿨나요?",
                              "rubric_items": ["decision_basis"],
                              "resume_span": "임베딩 모델을 교체해 정확도를 올렸다."}],
}

CONCEPT_CASES = {
    "splits": {"chunking": "dev", "other": "holdout"},
    "concept": [{
        "case_id": "cc1", "question_id": "chunking_01", "kind": "partial",
        "answer": "문맥이 더 담깁니다. 그리고 HNSW 때문에 빨라집니다.",
        "intended": {"core": {"c1": "met", "c2": "missing"},
                     "side": [{"side_id": "s1", "quote": "HNSW 때문에 빨라집니다", "expected": "unverified",
                               "group": "g_hnsw", "expected_evidence_doc": None}]},
    }],
}

EXPERIENCE_CASES = {
    "splits": {"sample_a": "dev", "sample_b": "holdout"},
    "experience": [{
        "case_id": "ec1", "sample_id": "sample_a", "question_id": "eq1", "quality": "shallow",
        "answer": "정확도가 낮아서 바꿨고, 이전 모델은 쓴 적 없습니다.",
        "intended": {"rubric": {"decision_basis": "observed"}, "contradiction": True,
                     "contradiction_quotes": ["이전 모델은 쓴 적 없습니다", "임베딩 모델을 교체해 정확도를 올렸다."]},
    }],
}


RETRIEVAL = {
    "splits": {"g_hnsw": "dev", "g_extra": "holdout"},
    "claims": [
        {"claim_id": "rc1", "text": "HNSW 때문에 빨라집니다", "expected": "unverified", "group": "g_hnsw",
         "expected_evidence_doc": None, "source": {"case_id": "cc1", "side_id": "s1"}},
        {"claim_id": "rc2", "text": "B7에서 보강한 경계 주장", "expected": "supported", "group": "g_extra",
         "expected_evidence_doc": "chunking", "tags": ["rare_term"]},
    ],
}


def write_tree(root: Path, **overrides) -> Path:
    files = {
        "kb_v2/docs/chunking.md": KB_DOC,
        "kb_v2/question_bank.yaml": BANK,
        "kb_v2/rubric.yaml": RUBRIC,
        "data_v2/samples/sample_a.md": RESUME,
        "data_v2/samples/sample_a.profile.yaml": PROFILE,
        "eval_v2/concept_cases.yaml": CONCEPT_CASES,
        "eval_v2/experience_cases.yaml": EXPERIENCE_CASES,
        "eval_v2/retrieval_claims.yaml": RETRIEVAL,
    }
    files.update(overrides)
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = content if isinstance(content, str) else yaml.safe_dump(content, allow_unicode=True)
        path.write_text(text, encoding="utf-8")
    return root


def errors_of(root):
    return check(root, today=TODAY).errors


def test_올바른_데이터는_통과한다(tmp_path):
    report = check(write_tree(tmp_path), today=TODAY)
    assert report.errors == []


def test_근거_문장이_문서에_없으면_오류(tmp_path):
    bank = yaml.safe_load(yaml.safe_dump(BANK))
    bank["questions"][0]["key_claims"][0]["evidence"] = "문서에 없는 문장이다."
    assert any("근거 문장" in e for e in errors_of(write_tree(tmp_path, **{"kb_v2/question_bank.yaml": bank})))


def test_없는_근거_문서와_참조는_오류(tmp_path):
    bank = yaml.safe_load(yaml.safe_dump(BANK))
    bank["questions"][0]["key_claims"][0]["evidence_doc"] = "nope"
    bank["questions"][0]["claim_followups"][0]["claim_id"] = "c9"
    bank["questions"][0]["deeper"] = ["missing_q"]
    errors = errors_of(write_tree(tmp_path, **{"kb_v2/question_bank.yaml": bank}))
    assert any("근거 문서가 없습니다" in e for e in errors)
    assert any("claim_followups" in e for e in errors)
    assert any("deeper" in e for e in errors)


def test_오래된_KB_문서는_경고(tmp_path):
    stale = KB_DOC.replace("last_reviewed: 2026-11-01", "last_reviewed: 2025-01-01")
    report = check(write_tree(tmp_path, **{"kb_v2/docs/chunking.md": stale}), today=TODAY)
    assert report.errors == [] and any("마지막 검토" in w for w in report.warnings)


def test_핵심_주장마다_의도_라벨이_있어야_한다(tmp_path):
    cases = yaml.safe_load(yaml.safe_dump(CONCEPT_CASES))
    del cases["concept"][0]["intended"]["core"]["c2"]
    assert any("의도 라벨" in e for e in errors_of(write_tree(tmp_path, **{"eval_v2/concept_cases.yaml": cases})))


def test_질문_밖_주장_인용은_답변에_그대로_있어야_한다(tmp_path):
    cases = yaml.safe_load(yaml.safe_dump(CONCEPT_CASES))
    cases["concept"][0]["intended"]["side"][0]["quote"] = "답변에 없는 말"
    assert any("인용" in e for e in errors_of(write_tree(tmp_path, **{"eval_v2/concept_cases.yaml": cases})))


def test_분할이_정해지지_않은_토픽은_오류(tmp_path):
    cases = yaml.safe_load(yaml.safe_dump(CONCEPT_CASES))
    cases["splits"] = {"other": "holdout"}
    assert any("분할" in e for e in errors_of(write_tree(tmp_path, **{"eval_v2/concept_cases.yaml": cases})))


def test_경험_답변은_고정된_루브릭_항목에만_라벨을_붙인다(tmp_path):
    cases = yaml.safe_load(yaml.safe_dump(EXPERIENCE_CASES))
    cases["experience"][0]["intended"]["rubric"]["outcome"] = "absent"
    assert any("루브릭 항목" in e for e in errors_of(write_tree(tmp_path, **{"eval_v2/experience_cases.yaml": cases})))


def test_모순은_인용이_원문에_있어야_하고_품질과_별개다(tmp_path):
    cases = yaml.safe_load(yaml.safe_dump(EXPERIENCE_CASES))
    cases["experience"][0]["intended"]["contradiction_quotes"][1] = "이력서에 없는 문장"
    assert any("모순 인용(이력서)" in e for e in errors_of(write_tree(tmp_path, **{"eval_v2/experience_cases.yaml": cases})))


def test_프로필_원문_구간은_이력서에_그대로_있어야_한다(tmp_path):
    profile = yaml.safe_load(yaml.safe_dump(PROFILE, allow_unicode=True))
    profile["projects"][0]["resume_span"] = "이력서에 없는 경력"
    assert any("resume_span" in e for e in errors_of(write_tree(tmp_path, **{"data_v2/samples/sample_a.profile.yaml": profile})))


def test_경험_질문의_전제_구간도_이력서에_있어야_한다(tmp_path):
    profile = yaml.safe_load(yaml.safe_dump(PROFILE, allow_unicode=True))
    profile["experience_questions"][0]["resume_span"] = "이력서에 없는 전제"
    assert any("질문 전제" in e for e in errors_of(write_tree(tmp_path, **{"data_v2/samples/sample_a.profile.yaml": profile})))


def test_검색_주장은_개념_답변의_질문_밖_주장과_같아야_한다(tmp_path):
    retrieval = yaml.safe_load(yaml.safe_dump(RETRIEVAL, allow_unicode=True))
    retrieval["claims"][0]["text"] = "HNSW 덕분에 빨라집니다"
    errors = errors_of(write_tree(tmp_path, **{"eval_v2/retrieval_claims.yaml": retrieval}))
    assert any("내용이 다릅니다" in e for e in errors)


def test_질문_밖_주장이_검색_평가셋에서_빠지면_오류(tmp_path):
    retrieval = yaml.safe_load(yaml.safe_dump(RETRIEVAL, allow_unicode=True))
    del retrieval["claims"][0]
    errors = errors_of(write_tree(tmp_path, **{"eval_v2/retrieval_claims.yaml": retrieval}))
    assert any("검색 평가셋에 없습니다" in e for e in errors)


def test_검색_주장은_group마다_분할이_있어야_한다(tmp_path):
    retrieval = yaml.safe_load(yaml.safe_dump(RETRIEVAL, allow_unicode=True))
    del retrieval["splits"]["g_hnsw"]
    errors = errors_of(write_tree(tmp_path, **{"eval_v2/retrieval_claims.yaml": retrieval}))
    assert any("group g_hnsw" in e for e in errors)


def test_기대_판정과_근거_문서_유무가_맞아야_한다(tmp_path):
    retrieval = yaml.safe_load(yaml.safe_dump(RETRIEVAL, allow_unicode=True))
    retrieval["claims"][1]["expected_evidence_doc"] = None   # supported인데 문서 없음
    assert any("expected_evidence_doc" in e for e in errors_of(write_tree(tmp_path, **{"eval_v2/retrieval_claims.yaml": retrieval})))


def test_같은_질문의_주장은_group이_달라도_같은_분할이다(tmp_path):
    cases = yaml.safe_load(yaml.safe_dump(CONCEPT_CASES, allow_unicode=True))
    cases["concept"][0]["intended"]["side"].append(
        {"side_id": "s2", "quote": "문맥이 더 담깁니다", "expected": "supported", "group": "g_other",
         "expected_evidence_doc": "chunking"})
    retrieval = yaml.safe_load(yaml.safe_dump(RETRIEVAL, allow_unicode=True))
    retrieval["splits"]["g_other"] = "holdout"
    retrieval["claims"].append(
        {"claim_id": "rc3", "text": "문맥이 더 담깁니다", "expected": "supported", "group": "g_other",
         "expected_evidence_doc": "chunking", "source": {"case_id": "cc1", "side_id": "s2"}})
    errors = errors_of(write_tree(tmp_path, **{"eval_v2/concept_cases.yaml": cases,
                                               "eval_v2/retrieval_claims.yaml": retrieval}))
    assert any("같은 질문 chunking_01" in e for e in errors)


def test_주장이_없는_분할_키로는_양쪽_분할을_채울_수_없다(tmp_path):
    retrieval = yaml.safe_load(yaml.safe_dump(RETRIEVAL, allow_unicode=True))
    del retrieval["claims"][1]   # holdout group(g_extra)의 키만 남는다
    report = check(write_tree(tmp_path, **{"eval_v2/retrieval_claims.yaml": retrieval}), today=TODAY)
    assert any("한쪽에만" in w for w in report.warnings)


def test_레포의_실제_v2_데이터가_검사를_통과한다():
    report = check(Path("."))
    assert report.errors == [], "\n".join(report.errors)
