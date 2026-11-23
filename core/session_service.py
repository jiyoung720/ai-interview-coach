"""세션 생성·이벤트·조회·삭제의 계약 (설계 §5.4, §8).

상태는 SQLite 하나에만 있다. 이벤트 하나는 다음 순서로 처리한다.

    소유권·만료 확인 → 세션 잠금 → (잠금 안에서) 멱등 조회 → 버전·질문·길이 검사
    → (answer면) 판정 1회분 예산 예약 → 엔진으로 한 턴 실행
    → 턴·세션·멱등 기록을 한 트랜잭션으로 커밋

커밋 전에 실패하면 턴·버전·멱등 응답은 반영되지 않는다(이미 차감한 예산은 남는다).
같은 키로 다시 보내면 처음부터 다시 처리한다. 커밋 후 응답이 유실되면 같은 키 재전송에
저장된 응답을 그대로 돌려준다.
"""
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from core import idempotency, llm, transitions
from core.budget import kst_day
from core.db import connect
from core.locks import KeyedLocks
from core.tracing import get_tracer

SESSION_TTL_SECONDS = 7 * 24 * 60 * 60   # 데모 세션 7일 (설계 §2.5)
MAX_ANSWER_CHARS = 2000


class ServiceError(Exception):
    status_code = 400


class NotFound(ServiceError):
    status_code = 404


class Expired(ServiceError):
    status_code = 410


class Conflict(ServiceError):
    """오래된 버전, 다른 질문에 대한 답, 진행할 수 없는 상태."""
    status_code = 409


class KeyReused(ServiceError):
    """같은 멱등 키에 다른 본문."""
    status_code = 422


class VisitorLimit(ServiceError):
    """방문자별 하루 세션 수 상한."""
    status_code = 429


@dataclass(frozen=True)
class VisitorLimits:
    per_owner: int = 3
    per_ip: int = 10


class SessionService:
    def __init__(self, db_path: Path, engine, *, locks: KeyedLocks | None = None, clock=time.time,
                 ttl_seconds: int = SESSION_TTL_SECONDS, lock_timeout: float = 30.0,
                 visitor_limits: VisitorLimits | None = None, max_answer_chars: int = MAX_ANSWER_CHARS):
        self.db_path = db_path
        self.engine = engine
        self.locks = locks or KeyedLocks()
        self.clock = clock
        self.ttl = ttl_seconds
        self.lock_timeout = lock_timeout
        self.visitor_limits = visitor_limits      # None이면 제한 없음(로컬 모드)
        self.max_answer_chars = max_answer_chars

    # ------------------------------------------------------------------ 생성
    def create(self, owner_id: str, create_key: str, body: dict, client_ip: str | None = None) -> dict:
        hash_ = idempotency.body_hash(body)
        with self.locks.hold(f"create:{owner_id}:{create_key}", self.lock_timeout):
            conn = connect(self.db_path)
            try:
                row = conn.execute(
                    "SELECT * FROM sessions WHERE owner_id = ? AND create_key = ?", (owner_id, create_key)
                ).fetchone()
                if row is not None:
                    if row["create_body_hash"] != hash_:
                        raise KeyReused("같은 생성 키에 다른 요청 본문입니다.")
                    if row["status"] != "planning":
                        return self._view(conn, row)
                    session_id = row["id"]   # 계획 도중 실패했던 세션: 같은 세션에서 계획만 다시 실행
                else:
                    session_id = self._insert_planning(conn, owner_id, create_key, hash_, client_ip)

                with get_tracer().span("plan", trace_session_id=self.trace_session_id(session_id)):
                    plan = self.engine.plan(body)   # 외부 호출이 생길 수 있어 트랜잭션 밖에서 실행
                with self.locks.hold(f"session:{session_id}", self.lock_timeout):
                    conn.execute("BEGIN IMMEDIATE")
                    if not self._exists(conn, session_id):
                        conn.execute("ROLLBACK")
                        raise NotFound("세션이 삭제되었습니다.")
                    conn.execute(
                        "UPDATE sessions SET status = ?, version = version + 1, plan_json = ?, "
                        "current_question_json = ? WHERE id = ?",
                        (transitions.status_after_plan(plan), json.dumps(plan, ensure_ascii=False),
                         json.dumps(plan[0], ensure_ascii=False) if plan else None, session_id),
                    )
                    conn.execute("COMMIT")
                    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
                    return self._view(conn, row)
            finally:
                conn.close()

    def _insert_planning(self, conn, owner_id: str, create_key: str, hash_: str, client_ip: str | None) -> str:
        session_id = str(uuid.uuid4())
        now = self.clock()
        conn.execute("BEGIN IMMEDIATE")
        try:
            # 세션 등록과 방문자 세션 수 차감은 한 트랜잭션이다. 같은 생성 키 재전송은 여기까지 오지 않는다.
            if self.visitor_limits is not None:
                self._count_visitor(conn, kst_day(now), "owner", owner_id, self.visitor_limits.per_owner)
                if client_ip:
                    self._count_visitor(conn, kst_day(now), "ip", client_ip, self.visitor_limits.per_ip)
            conn.execute(
                "INSERT INTO sessions (id, owner_id, status, version, cursor_json, trace_session_id, create_key, "
                "create_body_hash, created_at, expires_at) VALUES (?, ?, 'planning', 0, ?, ?, ?, ?, ?, ?)",
                (session_id, owner_id, json.dumps({"main_index": 0, "depth": 0}), secrets.token_hex(16),
                 create_key, hash_, now, now + self.ttl),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return session_id

    @staticmethod
    def _count_visitor(conn, day: str, kind: str, key: str, limit: int) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO visitor_daily (day, kind, key, count) VALUES (?, ?, ?, 0)", (day, kind, key)
        )
        cur = conn.execute(
            "UPDATE visitor_daily SET count = count + 1 WHERE day = ? AND kind = ? AND key = ? AND count < ?",
            (day, kind, key, limit),
        )
        if cur.rowcount == 0:
            raise VisitorLimit("오늘 새로 시작할 수 있는 면접 수를 모두 썼습니다.")

    # ------------------------------------------------------------------ 이벤트
    def submit(self, owner_id: str, session_id: str, key: str, body: dict) -> dict:
        hash_ = idempotency.body_hash(body)
        conn = connect(self.db_path)
        try:
            first = self._load_owned(conn, owner_id, session_id)   # 잠금 전에 소유권·만료부터 거른다
            action = body.get("action", "answer")
            # 요청 하나 = trace 하나. 추적 전용 세션 ID로 같은 세션의 요청들을 묶는다 (설계 §7.4-1)
            with self.locks.hold(f"session:{session_id}", self.lock_timeout), get_tracer().span(
                "session.event", trace_session_id=first["trace_session_id"], action=action
            ) as span:
                row = self._load_owned(conn, owner_id, session_id)   # 잠금을 기다리는 사이 삭제됐을 수 있다

                stored = idempotency.lookup(conn, owner_id, idempotency.EVENT_SCOPE, key)
                if stored is not None:
                    stored_hash, response = stored
                    if stored_hash != hash_:
                        raise KeyReused("같은 이벤트 키에 다른 요청 본문입니다.")
                    span.set(outcome="replay")
                    return response

                if action not in transitions.ACTIONS:
                    raise ServiceError(f"알 수 없는 행동입니다: {action}")
                if not transitions.can_act(row["status"], action):
                    raise Conflict(f"지금 상태에서는 할 수 없는 행동입니다: {row['status']}")
                if body.get("version") != row["version"]:
                    raise Conflict("세션이 이미 진행되었습니다. 최신 상태를 다시 불러오세요.")
                question = json.loads(row["current_question_json"])
                if body.get("question_id") != question["id"]:
                    raise Conflict("지금 질문에 대한 요청이 아닙니다.")

                state = {
                    "plan": json.loads(row["plan_json"]),
                    "cursor": json.loads(row["cursor_json"]),
                    "question": question,
                }
                answer = None
                if action == "answer":
                    answer = body.get("answer") or ""
                    if not answer.strip():
                        raise ServiceError("답변이 비어 있습니다.")
                    if len(answer) > self.max_answer_chars:
                        raise ServiceError(f"답변은 {self.max_answer_chars}자까지 보낼 수 있습니다.")
                    # 그래프를 실행하기 전에 판정 1회분을 예약한다. 예산이 없으면 여기서 429로 끝나고
                    # 아무것도 기록하지 않는다 (설계 §7.0)
                    reservation = llm.reserve_judgement()
                    with llm.reservation_scope(reservation):
                        result = self.engine.run_turn(state, answer)   # 트랜잭션 밖에서 실행
                elif action == "skip":
                    result = self.engine.skip(state)
                else:
                    result = {"outcome": "ended", "next_question": None, "next_cursor": state["cursor"]}

                record = {
                    "event": transitions.OUTCOME_EVENTS[result["outcome"]],
                    "question": question,
                    "answer": answer,
                    "judgement": result.get("judgement"),
                    "coaching": result.get("coaching"),
                    "coaching_skipped": result.get("coaching_skipped", False),
                }
                next_question = result["next_question"] if result["outcome"] != "ended" else None
                new_status = transitions.status_after(result["outcome"], next_question)
                with get_tracer().span("commit"):
                    response = self._commit_turn(conn, owner_id, session_id, row, key, hash_, record,
                                                 next_question, result["next_cursor"], new_status)
                span.set(outcome=result["outcome"], status=new_status,
                         budget_exhausted=record["coaching_skipped"] or None)
                return response
        finally:
            conn.close()

    def _commit_turn(self, conn, owner_id, session_id, row, key, hash_, record, next_question, next_cursor, new_status):
        conn.execute("BEGIN IMMEDIATE")
        try:
            if not self._exists(conn, session_id):
                raise NotFound("세션이 삭제되었습니다.")
            seq = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM turns WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO turns (session_id, seq, record_json) VALUES (?, ?, ?)",
                (session_id, seq, json.dumps(record, ensure_ascii=False)),
            )
            version = row["version"] + 1
            conn.execute(
                "UPDATE sessions SET status = ?, version = ?, cursor_json = ?, current_question_json = ? WHERE id = ?",
                (new_status, version, json.dumps(next_cursor),
                 json.dumps(next_question, ensure_ascii=False) if next_question else None, session_id),
            )
            response = {
                "session_id": session_id,
                "status": new_status,
                "version": version,
                "turn": {"seq": seq, **record},
                "next_question": next_question,
            }
            idempotency.store(conn, owner_id, idempotency.EVENT_SCOPE, key, hash_, response, session_id)
            conn.execute("COMMIT")
            return response
        except Exception:
            conn.execute("ROLLBACK")
            raise

    # ------------------------------------------------------------------ 조회·삭제
    def get(self, owner_id: str, session_id: str) -> dict:
        conn = connect(self.db_path)
        try:
            return self._view(conn, self._load_owned(conn, owner_id, session_id))
        finally:
            conn.close()

    def trace_session_id(self, session_id: str) -> str | None:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT trace_session_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return row["trace_session_id"] if row else None
        finally:
            conn.close()

    def delete(self, owner_id: str, session_id: str) -> None:
        conn = connect(self.db_path)
        try:
            self._load_owned(conn, owner_id, session_id, allow_expired=True)
            with self.locks.hold(f"session:{session_id}", self.lock_timeout):
                self._delete_locked(conn, session_id)
        finally:
            conn.close()

    def purge_expired(self) -> int:
        """만료된 세션을 지운다. 이벤트와 같은 잠금을 잡고, 잡은 뒤 만료 여부를 다시 확인한다."""
        conn = connect(self.db_path)
        removed = 0
        try:
            ids = [r["id"] for r in conn.execute("SELECT id FROM sessions WHERE expires_at <= ?", (self.clock(),))]
            for session_id in ids:
                with self.locks.hold(f"session:{session_id}", self.lock_timeout):
                    row = conn.execute("SELECT expires_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
                    if row is not None and row["expires_at"] <= self.clock():
                        self._delete_locked(conn, session_id)
                        removed += 1
            return removed
        finally:
            conn.close()

    def _delete_locked(self, conn, session_id: str) -> None:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))   # 턴·멱등 기록은 CASCADE
        conn.execute("COMMIT")
        self.locks.forget(f"session:{session_id}")

    # ------------------------------------------------------------------ 내부
    def _load_owned(self, conn, owner_id: str, session_id: str, allow_expired: bool = False):
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None or row["owner_id"] != owner_id:
            raise NotFound("세션을 찾을 수 없습니다.")   # 남의 세션도 존재 여부를 드러내지 않는다
        if not allow_expired and row["expires_at"] <= self.clock():
            raise Expired("만료된 세션입니다.")
        return row

    @staticmethod
    def _exists(conn, session_id: str) -> bool:
        return conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone() is not None

    @staticmethod
    def _view(conn, row) -> dict:
        turns = [
            {"seq": t["seq"], **json.loads(t["record_json"])}
            for t in conn.execute("SELECT seq, record_json FROM turns WHERE session_id = ? ORDER BY seq", (row["id"],))
        ]
        return {
            "session_id": row["id"],
            "status": row["status"],
            "version": row["version"],
            "current_question": json.loads(row["current_question_json"]) if row["current_question_json"] else None,
            "turns": turns,
        }
