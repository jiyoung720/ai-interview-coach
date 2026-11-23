"""세션 생성·이벤트·조회·삭제의 계약 (설계 §5.4, §8).

상태는 SQLite 하나에만 있다. 이벤트 하나는 다음 순서로 처리한다.

    소유권·만료 확인 → 세션 잠금 → (잠금 안에서) 멱등 조회 → 버전·질문 검사
    → 엔진으로 한 턴 실행 → 턴·세션·멱등 기록을 한 트랜잭션으로 커밋

커밋 전에 실패하면 턴·버전·멱등 응답은 반영되지 않는다. 같은 키로 다시 보내면 처음부터 다시 처리한다.
커밋 후 응답이 유실되면 같은 키 재전송에 저장된 응답을 그대로 돌려준다.
"""
import json
import secrets
import time
import uuid
from pathlib import Path

from core import idempotency
from core.db import connect
from core.locks import KeyedLocks

SESSION_TTL_SECONDS = 7 * 24 * 60 * 60   # 데모 세션 7일 (설계 §2.5)


class ServiceError(Exception):
    status_code = 400


class NotFound(ServiceError):
    status_code = 404


class Expired(ServiceError):
    status_code = 410


class Conflict(ServiceError):
    """오래된 버전, 다른 질문에 대한 답, 진행할 수 없는 상태, 잠금 대기 초과."""
    status_code = 409


class KeyReused(ServiceError):
    """같은 멱등 키에 다른 본문."""
    status_code = 422


class SessionService:
    def __init__(self, db_path: Path, engine, *, locks: KeyedLocks | None = None, clock=time.time,
                 ttl_seconds: int = SESSION_TTL_SECONDS, lock_timeout: float = 30.0):
        self.db_path = db_path
        self.engine = engine
        self.locks = locks or KeyedLocks()
        self.clock = clock
        self.ttl = ttl_seconds
        self.lock_timeout = lock_timeout

    # ------------------------------------------------------------------ 생성
    def create(self, owner_id: str, create_key: str, body: dict) -> dict:
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
                    session_id = self._insert_planning(conn, owner_id, create_key, hash_)

                plan = self.engine.plan(body)   # 외부 호출이 생길 수 있어 트랜잭션 밖에서 실행
                with self.locks.hold(f"session:{session_id}", self.lock_timeout):
                    conn.execute("BEGIN IMMEDIATE")
                    if not self._exists(conn, session_id):
                        conn.execute("ROLLBACK")
                        raise NotFound("세션이 삭제되었습니다.")
                    if not plan:
                        conn.execute("UPDATE sessions SET status = 'failed', version = version + 1 WHERE id = ?", (session_id,))
                    else:
                        conn.execute(
                            "UPDATE sessions SET status = 'awaiting_answer', version = version + 1, plan_json = ?, "
                            "current_question_json = ? WHERE id = ?",
                            (json.dumps(plan, ensure_ascii=False), json.dumps(plan[0], ensure_ascii=False), session_id),
                        )
                    conn.execute("COMMIT")
                    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
                    return self._view(conn, row)
            finally:
                conn.close()

    def _insert_planning(self, conn, owner_id: str, create_key: str, hash_: str) -> str:
        session_id = str(uuid.uuid4())
        now = self.clock()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO sessions (id, owner_id, status, version, cursor_json, trace_session_id, create_key, "
            "create_body_hash, created_at, expires_at) VALUES (?, ?, 'planning', 0, ?, ?, ?, ?, ?, ?)",
            (session_id, owner_id, json.dumps({"main_index": 0, "depth": 0}), secrets.token_hex(16),
             create_key, hash_, now, now + self.ttl),
        )
        conn.execute("COMMIT")
        return session_id

    # ------------------------------------------------------------------ 이벤트
    def submit(self, owner_id: str, session_id: str, key: str, body: dict) -> dict:
        hash_ = idempotency.body_hash(body)
        conn = connect(self.db_path)
        try:
            self._load_owned(conn, owner_id, session_id)   # 잠금 전에 소유권·만료부터 거른다
            with self.locks.hold(f"session:{session_id}", self.lock_timeout):
                row = self._load_owned(conn, owner_id, session_id)   # 잠금을 기다리는 사이 삭제됐을 수 있다

                stored = idempotency.lookup(conn, owner_id, idempotency.EVENT_SCOPE, key)
                if stored is not None:
                    stored_hash, response = stored
                    if stored_hash != hash_:
                        raise KeyReused("같은 이벤트 키에 다른 요청 본문입니다.")
                    return response

                if row["status"] != "awaiting_answer":
                    raise Conflict(f"답변을 받을 수 없는 상태입니다: {row['status']}")
                if body.get("version") != row["version"]:
                    raise Conflict("세션이 이미 진행되었습니다. 최신 상태를 다시 불러오세요.")
                question = json.loads(row["current_question_json"])
                if body.get("question_id") != question["id"]:
                    raise Conflict("지금 질문에 대한 답변이 아닙니다.")

                state = {
                    "plan": json.loads(row["plan_json"]),
                    "cursor": json.loads(row["cursor_json"]),
                    "question": question,
                }
                result = self.engine.run_turn(state, body["answer"])   # 트랜잭션 밖에서 실행

                record = {
                    "question": question,
                    "answer": body["answer"],
                    "judgement": result["judgement"],
                }
                next_question = result["next_question"]
                new_status = "awaiting_answer" if next_question else "done"

                conn.execute("BEGIN IMMEDIATE")
                if not self._exists(conn, session_id):
                    conn.execute("ROLLBACK")
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
                    (new_status, version, json.dumps(result["next_cursor"]),
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
        finally:
            conn.close()

    # ------------------------------------------------------------------ 조회·삭제
    def get(self, owner_id: str, session_id: str) -> dict:
        conn = connect(self.db_path)
        try:
            return self._view(conn, self._load_owned(conn, owner_id, session_id))
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
