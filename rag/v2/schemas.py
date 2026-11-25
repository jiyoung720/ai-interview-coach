"""v2 데이터 파일과 판정 결과의 형식 (설계 §3, §5.2, §6).

데이터는 사람이 읽고 고치기 쉽게 YAML/Markdown으로 두고, 읽을 때 이 스키마로 검증한다.
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Split = Literal["dev", "holdout"]


# ---------------------------------------------------------------- KB 문서

class Source(BaseModel):
    title: str
    url: str


class KBDocMeta(BaseModel):
    """kb_v2/docs/<topic>.md 의 frontmatter."""
    topic: str
    area: str
    difficulty: Literal["basic", "intermediate"]
    sources: list[Source] = Field(min_length=1)
    last_reviewed: date


# ---------------------------------------------------------------- 질문 은행

class KeyClaim(BaseModel):
    """채점 체크리스트의 주장 하나. 근거 문장은 evidence_doc 본문에 그대로 있어야 한다."""
    claim_id: str
    text: str
    evidence: str                 # KB 문서에서 그대로 가져온 근거 문장
    evidence_doc: str             # 근거 문서 ID (= KB 문서의 topic)
    # 이 주장을 충족한 것으로 함께 인정할 답의 모습. 주석이 아니라 필드라서 Judge 프롬프트에 그대로 들어간다.
    also_accept: list[str] = []


class ClaimFollowup(BaseModel):
    """핵심 주장 하나를 확인하는 검수된 꼬리질문. 그 주장 하나만 채점한다."""
    claim_id: str
    question: str


class BankQuestion(BaseModel):
    id: str
    topic: str
    question: str                 # 원문 그대로 출제한다 (설계 §3.1)
    difficulty: Literal["basic", "intermediate"] = "basic"
    key_claims: list[KeyClaim] = Field(min_length=1)
    kb_doc_ids: list[str] = Field(min_length=1)
    claim_followups: list[ClaimFollowup] = []
    deeper: list[str] = []        # 잘 답했을 때 고를 심화 질문(다른 은행 항목의 id)

    @model_validator(mode="after")
    def _unique_claim_ids(self):
        ids = [c.claim_id for c in self.key_claims]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.id}: claim_id가 중복됩니다")
        return self


class QuestionBank(BaseModel):
    questions: list[BankQuestion]


# ---------------------------------------------------------------- 경험 루브릭

class RubricItem(BaseModel):
    id: str
    name: str
    observed_when: str            # "관찰됨"의 기준


class Rubric(BaseModel):
    items: list[RubricItem] = Field(min_length=1)


# ---------------------------------------------------------------- 샘플 이력서와 프로필

class ProfileProject(BaseModel):
    id: str
    name: str
    role: str
    tech: list[str]
    outcomes: list[str] = []
    resume_span: str              # 이 항목의 근거가 되는 이력서 원문 구간 (이력서에 그대로 있어야 한다)


class ExperienceQuestion(BaseModel):
    id: str
    project_id: str
    question: str
    rubric_items: list[str] = Field(min_length=1, max_length=2)   # 이 질문이 볼 항목만 고정 (설계 §6.2)
    resume_span: str              # 질문의 전제를 뒷받침하는 이력서 원문 구간 (이력서에 그대로 있어야 한다)


class SampleProfile(BaseModel):
    sample_id: str
    summary: str
    projects: list[ProfileProject] = Field(min_length=1)
    experience_questions: list[ExperienceQuestion] = Field(min_length=1)


# ---------------------------------------------------------------- 캘리브레이션 답변

CoreStatus = Literal["met", "missing", "wrong", "insufficient_evidence"]
SideStatus = Literal["supported", "contradicted", "unverified"]
RubricStatus = Literal["observed", "absent", "not_applicable"]


class SideClaim(BaseModel):
    """답변에 나온 질문 밖 주장. 검색 평가셋(B7)의 재료도 된다."""
    side_id: str
    quote: str                    # 답변 안에 그대로 있어야 한다
    expected: SideStatus
    group: str                    # 같은 주장·의역·반대 주장은 같은 그룹 (질문이 달라도)
    expected_evidence_doc: str | None = None   # None이면 주장 단위로 "KB 근거 없음"

    @model_validator(mode="after")
    def _doc_matches_expected(self):
        return _check_doc_matches_expected(self)


def _check_doc_matches_expected(claim):
    """뒷받침·충돌이면 기대 근거 문서가 있어야 하고, 근거 없음이면 문서가 없어야 한다."""
    has_doc = claim.expected_evidence_doc is not None
    if (claim.expected == "unverified") == has_doc:
        raise ValueError(f"expected={claim.expected}와 expected_evidence_doc={claim.expected_evidence_doc}이 맞지 않습니다")
    return claim


class ConceptIntent(BaseModel):
    core: dict[str, CoreStatus]   # claim_id → 의도한 판정
    side: list[SideClaim] = []
    rationale: str = ""           # 판정 이유 한 줄 (의도 라벨과 함께 블라인드 파일에서 빠진다)


class ConceptCase(BaseModel):
    case_id: str
    question_id: str
    kind: Literal["missing", "misconception", "partial", "solid", "brief_correct",
                  "side_wrong", "injection", "length_short", "length_long"]
    answer: str
    intended: ConceptIntent
    pair_id: str | None = None    # 길이 편향 쌍 (같은 내용의 짧은/긴 답)


class ExperienceIntent(BaseModel):
    rubric: dict[str, RubricStatus]
    contradiction: bool = False   # 답변 품질과 별개인 플래그 (설계 §5.2)
    contradiction_quotes: tuple[str, str] | None = None   # (답변 인용, 이력서 인용)
    rationale: str = ""           # 판정 이유 한 줄

    @model_validator(mode="after")
    def _quotes_when_contradiction(self):
        if self.contradiction and not self.contradiction_quotes:
            raise ValueError("모순이면 답변 인용과 이력서 인용이 둘 다 필요합니다")
        return self


class ExperienceCase(BaseModel):
    case_id: str
    sample_id: str
    question_id: str
    quality: Literal["vague", "shallow", "solid"]
    answer: str
    intended: ExperienceIntent


class RetrievalSource(BaseModel):
    case_id: str
    side_id: str


class RetrievalClaim(BaseModel):
    """주장 → KB 조각 검색 평가셋의 주장 하나 (B7). 조각 단위 라벨은 검색 결과가 나온 뒤 붙인다."""
    claim_id: str
    text: str                     # 검색어로 쓰는 문장 (답변에서 온 주장은 인용 그대로)
    expected: SideStatus
    group: str
    expected_evidence_doc: str | None = None   # None이면 주장 단위로 "KB 근거 없음"
    source: RetrievalSource | None = None      # 개념 답변의 side에서 왔으면 그 위치. B7에서 보강한 주장은 None
    tags: list[str] = []          # 예: rare_term (저빈도 용어 부분집합)

    @model_validator(mode="after")
    def _doc_matches_expected(self):
        return _check_doc_matches_expected(self)


class RetrievalSet(BaseModel):
    """eval_v2/retrieval_claims.yaml. 분할은 토픽이 아니라 group 단위로 정하고,
    같은 질문에서 나온 주장은 group이 달라도 같은 분할에 둔다 (설계 §9.1)."""
    splits: dict[str, Split]      # group → split
    claims: list[RetrievalClaim]


class CaseSet(BaseModel):
    """eval_v2/*_cases.yaml. 분할은 토픽·이력서 단위로 정한다."""
    splits: dict[str, Split]      # concept: topic → split, experience: sample_id → split
    concept: list[ConceptCase] = []
    experience: list[ExperienceCase] = []
