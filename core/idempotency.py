# 이벤트 멱등 기록 (설계 §5.4, §8).
#
# 같은 키 + 같은 본문이 다시 오면 저장해 둔 응답을 그대로 돌려준다. 응답이 유실돼 클라이언트가
# 재전송해도 턴이 두 번 반영되지 않는다. 같은 키에 다른 본문이 오면 거부한다(422).
import hashlib
import json
import sqlite3

EVENT_SCOPE = "event"


def body_hash(body: dict) -> str:
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def lookup(conn: sqlite3.Connection, owner_id: str, scope: str, key: str) -> tuple[str, dict] | None:
    row = conn.execute(
        "SELECT body_hash, response_json FROM idempotency WHERE owner_id = ? AND scope = ? AND key = ?",
        (owner_id, scope, key),
    ).fetchone()
    if row is None:
        return None
    return row["body_hash"], json.loads(row["response_json"])


def store(conn, owner_id: str, scope: str, key: str, hash_: str, response: dict, session_id: str) -> None:
    """호출자가 연 트랜잭션 안에서 턴·세션 갱신과 함께 저장한다."""
    conn.execute(
        "INSERT INTO idempotency (owner_id, scope, key, body_hash, response_json, session_id) VALUES (?, ?, ?, ?, ?, ?)",
        (owner_id, scope, key, hash_, json.dumps(response, ensure_ascii=False), session_id),
    )
