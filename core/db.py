# 앱 상태의 권위 저장소(SQLite).
#
# 세션·턴·멱등 기록·예산이 모두 여기 있다. v2는 LangGraph 체크포인터를 쓰지 않고
# 요청마다 이 DB에서 상태를 읽어 그래프를 한 턴 실행한 뒤 한 트랜잭션으로 저장한다 (설계 §5.4).
#
# 스키마 버전은 PRAGMA user_version으로 관리한다. MIGRATIONS에 순서대로 SQL을 추가하면
# init_db()가 아직 적용되지 않은 것만 실행한다.
import sqlite3
from pathlib import Path

# 인덱스 i의 SQL을 적용하면 user_version이 i + 1이 된다. 이미 배포된 항목은 고치지 말고 뒤에 추가한다.
MIGRATIONS: list[str] = [
    # 1: 세션, 턴, 멱등 기록 (M0 S2)
    """
    CREATE TABLE sessions (
        id                    TEXT PRIMARY KEY,
        owner_id              TEXT NOT NULL,
        status                TEXT NOT NULL,       -- planning | awaiting_answer | done | failed
        version               INTEGER NOT NULL,    -- 커밋마다 1씩 증가. 오래된 요청을 거르는 기준
        plan_json             TEXT,                -- 메인 질문 목록
        current_question_json TEXT,                -- 지금 답해야 할 질문 (꼬리질문 포함). 재시작 후 이것만 읽으면 이어진다
        cursor_json           TEXT NOT NULL,       -- 몇 번째 메인 질문, 꼬리질문 깊이 등
        trace_session_id      TEXT NOT NULL,       -- 추적 전용 무작위 ID. 앱 DB 밖으로 연결 정보를 내보내지 않는다
        create_key            TEXT NOT NULL,       -- 세션 생성 멱등 키
        create_body_hash      TEXT NOT NULL,       -- 같은 생성 키에 다른 본문이 오면 거부하기 위한 해시
        created_at            REAL NOT NULL,
        expires_at            REAL NOT NULL,
        UNIQUE (owner_id, create_key)
    );
    CREATE INDEX idx_sessions_expires ON sessions (expires_at);

    CREATE TABLE turns (
        session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        seq         INTEGER NOT NULL,
        record_json TEXT NOT NULL,                 -- 쓰고 나면 바꾸지 않는 턴 기록
        PRIMARY KEY (session_id, seq)
    );

    CREATE TABLE idempotency (
        owner_id      TEXT NOT NULL,
        scope         TEXT NOT NULL,               -- event (세션 생성은 sessions.create_key가 담당)
        key           TEXT NOT NULL,
        body_hash     TEXT NOT NULL,
        response_json TEXT NOT NULL,
        session_id    TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        PRIMARY KEY (owner_id, scope, key)
    )
    """,
    # 2: 하루 공용 예산, 방문자별 세션 수 (M0 S3)
    """
    CREATE TABLE budget_daily (
        day  TEXT PRIMARY KEY,                     -- 한국 시간 기준 YYYY-MM-DD
        used INTEGER NOT NULL
    );
    CREATE TABLE visitor_daily (
        day   TEXT NOT NULL,
        kind  TEXT NOT NULL,                       -- owner | ip
        key   TEXT NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (day, kind, key)
    )
    """,
]


def connect(db_path: Path) -> sqlite3.Connection:
    """설정이 적용된 연결을 연다. 트랜잭션은 호출자가 BEGIN으로 명시한다."""
    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db(db_path: Path) -> None:
    """DB 파일을 만들고 밀린 마이그레이션을 적용한다. 기동 시 한 번 부른다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        for version, sql in enumerate(MIGRATIONS[current:], start=current + 1):
            conn.execute("BEGIN IMMEDIATE")
            try:
                _run_script(conn, sql)
                conn.execute(f"PRAGMA user_version={version}")
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    finally:
        conn.close()


def _run_script(conn: sqlite3.Connection, sql: str) -> None:
    # executescript는 열린 트랜잭션을 먼저 커밋해버리므로, 문장을 나눠 같은 트랜잭션 안에서 실행한다.
    for statement in sql.split(";"):
        if statement.strip():
            conn.execute(statement)
