"""v2 데이터 검사 (API 불필요, CI에서 매번 실행).

무엇을 검사하나
- 스키마: KB frontmatter, 질문 은행, 루브릭, 샘플 프로필, 캘리브레이션 답변
- key_evidence: 핵심 주장의 근거 문장이 근거 문서 본문에 **그대로** 있는가, 문서 ID가 존재하는가
- 참조 무결성: claim_followups·deeper·kb_doc_ids, 경험 질문의 루브릭 항목, 답변이 가리키는 질문
- 인용: 질문 밖 주장과 모순 인용이 답변·이력서 원문에 그대로 있는가
- 분할: 답변이 속한 토픽·이력서마다 dev/holdout이 정해져 있는가

무엇을 검사하지 않나
- 근거 문장이 주장을 **실제로 뒷받침하는지**는 사람이 검수한다. CI는 문장이 있는지만 본다.

실행:
    uv run python -m scripts.v2.check_data
"""
import re
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml
from pydantic import ValidationError

from rag.v2.schemas import CaseSet, KBDocMeta, QuestionBank, Rubric, SampleProfile

STALE_AFTER = timedelta(days=180)   # 빨리 변하는 분야라 반년이 지나면 다시 본다 (설계 §6.1)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not match:
        raise ValueError("frontmatter(--- ... ---)가 없습니다")
    return yaml.safe_load(match.group(1)) or {}, match.group(2)


def _load_yaml(path: Path, report: Report):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        report.errors.append(f"{path}: YAML을 읽을 수 없습니다: {error}")
        return None


def check(root: Path, today: date | None = None) -> Report:
    today = today or date.today()
    report = Report()

    # ---- KB 문서
    docs: dict[str, str] = {}   # topic → 본문(정규화)
    for path in sorted((root / "kb_v2" / "docs").glob("*.md")):
        try:
            meta_raw, body = split_frontmatter(path.read_text(encoding="utf-8"))
            meta = KBDocMeta.model_validate(meta_raw)
        except (ValueError, ValidationError) as error:
            report.errors.append(f"{path.name}: {error}")
            continue
        if meta.topic != path.stem:
            report.errors.append(f"{path.name}: topic({meta.topic})이 파일 이름과 다릅니다")
        if today - meta.last_reviewed > STALE_AFTER:
            report.warnings.append(f"{path.name}: 마지막 검토가 {meta.last_reviewed}입니다. 내용을 다시 확인하세요")
        docs[meta.topic] = _norm(body)

    # ---- 질문 은행
    bank: dict = {}
    bank_path = root / "kb_v2" / "question_bank.yaml"
    if bank_path.exists() and (raw := _load_yaml(bank_path, report)) is not None:
        try:
            questions = QuestionBank.model_validate(raw).questions
        except ValidationError as error:
            report.errors.append(f"question_bank.yaml: {error}")
            questions = []
        for q in questions:
            if q.id in bank:
                report.errors.append(f"질문 id 중복: {q.id}")
            bank[q.id] = q
        for q in bank.values():
            for doc_id in q.kb_doc_ids:
                if doc_id not in docs:
                    report.errors.append(f"{q.id}: kb_doc_ids의 문서가 없습니다: {doc_id}")
            claim_ids = {c.claim_id for c in q.key_claims}
            for claim in q.key_claims:
                if claim.evidence_doc not in docs:
                    report.errors.append(f"{q.id}/{claim.claim_id}: 근거 문서가 없습니다: {claim.evidence_doc}")
                elif _norm(claim.evidence) not in docs[claim.evidence_doc]:
                    report.errors.append(
                        f"{q.id}/{claim.claim_id}: 근거 문장이 {claim.evidence_doc} 본문에 그대로 없습니다"
                    )
            for followup in q.claim_followups:
                if followup.claim_id not in claim_ids:
                    report.errors.append(f"{q.id}: claim_followups가 없는 주장을 가리킵니다: {followup.claim_id}")
            for deeper_id in q.deeper:
                if deeper_id == q.id or deeper_id not in bank:
                    report.errors.append(f"{q.id}: deeper가 가리키는 질문이 없습니다: {deeper_id}")

    # ---- 루브릭
    rubric_ids: set[str] = set()
    rubric_path = root / "kb_v2" / "rubric.yaml"
    if rubric_path.exists() and (raw := _load_yaml(rubric_path, report)) is not None:
        try:
            rubric_ids = {item.id for item in Rubric.model_validate(raw).items}
        except ValidationError as error:
            report.errors.append(f"rubric.yaml: {error}")

    # ---- 샘플 이력서와 프로필
    samples: dict[str, tuple[SampleProfile, str]] = {}   # sample_id → (프로필, 이력서 원문 정규화)
    samples_dir = root / "data_v2" / "samples"
    for path in sorted(samples_dir.glob("*.profile.yaml")):
        sample_id = path.name.removesuffix(".profile.yaml")
        resume_path = samples_dir / f"{sample_id}.md"
        if (raw := _load_yaml(path, report)) is None:
            continue
        try:
            profile = SampleProfile.model_validate(raw)
        except ValidationError as error:
            report.errors.append(f"{path.name}: {error}")
            continue
        if profile.sample_id != sample_id:
            report.errors.append(f"{path.name}: sample_id({profile.sample_id})가 파일 이름과 다릅니다")
        if not resume_path.exists():
            report.errors.append(f"{path.name}: 이력서 원문이 없습니다: {resume_path.name}")
            continue
        resume = _norm(resume_path.read_text(encoding="utf-8"))
        project_ids = {p.id for p in profile.projects}
        for project in profile.projects:
            if _norm(project.resume_span) not in resume:
                report.errors.append(f"{sample_id}/{project.id}: resume_span이 이력서 원문에 그대로 없습니다")
        for question in profile.experience_questions:
            if _norm(question.resume_span) not in resume:
                report.errors.append(f"{sample_id}/{question.id}: 질문 전제의 resume_span이 이력서 원문에 그대로 없습니다")
            if question.project_id not in project_ids:
                report.errors.append(f"{sample_id}/{question.id}: 없는 프로젝트를 가리킵니다: {question.project_id}")
            for item in question.rubric_items:
                if rubric_ids and item not in rubric_ids:
                    report.errors.append(f"{sample_id}/{question.id}: 루브릭에 없는 항목입니다: {item}")
        samples[sample_id] = (profile, resume)

    # ---- 캘리브레이션 답변
    for name in ("concept_cases.yaml", "experience_cases.yaml"):
        path = root / "eval_v2" / name
        if not path.exists() or (raw := _load_yaml(path, report)) is None:
            continue
        try:
            cases = CaseSet.model_validate(raw)
        except ValidationError as error:
            report.errors.append(f"{name}: {error}")
            continue
        _check_concept_cases(cases, bank, docs, report)
        _check_experience_cases(cases, samples, report)

    return report


def _check_concept_cases(cases: CaseSet, bank: dict, docs: dict, report: Report) -> None:
    seen = set()
    for case in cases.concept:
        if case.case_id in seen:
            report.errors.append(f"case_id 중복: {case.case_id}")
        seen.add(case.case_id)
        question = bank.get(case.question_id)
        if question is None:
            report.errors.append(f"{case.case_id}: 질문 은행에 없는 질문입니다: {case.question_id}")
            continue
        if question.topic not in cases.splits:
            report.errors.append(f"{case.case_id}: 토픽 {question.topic}의 dev/holdout 분할이 정해지지 않았습니다")
        expected_ids = {c.claim_id for c in question.key_claims}
        if set(case.intended.core) != expected_ids:
            report.errors.append(f"{case.case_id}: 모든 핵심 주장에 의도 라벨이 있어야 합니다 {sorted(expected_ids)}")
        answer = _norm(case.answer)
        for side in case.intended.side:
            if _norm(side.quote) not in answer:
                report.errors.append(f"{case.case_id}/{side.side_id}: 질문 밖 주장 인용이 답변에 그대로 없습니다")
            if side.expected_evidence_doc and side.expected_evidence_doc not in docs:
                report.errors.append(f"{case.case_id}/{side.side_id}: 기대 근거 문서가 없습니다: {side.expected_evidence_doc}")
    _warn_if_single_split(cases, report)


def _check_experience_cases(cases: CaseSet, samples: dict, report: Report) -> None:
    seen = set()
    for case in cases.experience:
        if case.case_id in seen:
            report.errors.append(f"case_id 중복: {case.case_id}")
        seen.add(case.case_id)
        if case.sample_id not in samples:
            report.errors.append(f"{case.case_id}: 샘플이 없습니다: {case.sample_id}")
            continue
        if case.sample_id not in cases.splits:
            report.errors.append(f"{case.case_id}: 샘플 {case.sample_id}의 dev/holdout 분할이 정해지지 않았습니다")
        profile, resume = samples[case.sample_id]
        question = next((q for q in profile.experience_questions if q.id == case.question_id), None)
        if question is None:
            report.errors.append(f"{case.case_id}: 경험 질문이 없습니다: {case.question_id}")
            continue
        if set(case.intended.rubric) != set(question.rubric_items):
            report.errors.append(f"{case.case_id}: 질문에 고정된 루브릭 항목 {question.rubric_items}에만 라벨을 붙여야 합니다")
        if case.intended.contradiction_quotes:
            answer_quote, resume_quote = case.intended.contradiction_quotes
            if _norm(answer_quote) not in _norm(case.answer):
                report.errors.append(f"{case.case_id}: 모순 인용(답변)이 답변에 그대로 없습니다")
            if _norm(resume_quote) not in resume:
                report.errors.append(f"{case.case_id}: 모순 인용(이력서)이 이력서에 그대로 없습니다")
    _warn_if_single_split(cases, report)


def _warn_if_single_split(cases: CaseSet, report: Report) -> None:
    if cases.splits and len(set(cases.splits.values())) < 2:
        report.warnings.append("dev와 holdout 중 한쪽만 있습니다")


def main() -> int:
    report = check(Path("."))
    for warning in report.warnings:
        print(f"[경고] {warning}")
    for error in report.errors:
        print(f"[오류] {error}")
    print("통과" if report.ok else f"실패: 오류 {len(report.errors)}건")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
