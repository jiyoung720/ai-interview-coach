# 하루 공용 예산 (설계 §2.5 비용 차단).
#
# 공개 데모의 진짜 차단 장치다. 모든 외부 모델 호출(생성·임베딩) 직전에 한 번씩 차감한다.
# 차감은 SQLite의 조건부 UPDATE 한 문장이라, 스레드가 동시에 몰려도 상한을 넘지 않는다.
# 카운터가 DB에 있으므로 서버를 재시작해도 그날 쓴 양이 유지된다.
import datetime as dt
import time
from pathlib import Path

from core.db import connect

KST = dt.timezone(dt.timedelta(hours=9))


class BudgetExhausted(Exception):
    """오늘 공용 예산을 다 썼다. API는 429로 응답한다."""
    status_code = 429


def kst_day(epoch: float) -> str:
    return dt.datetime.fromtimestamp(epoch, KST).strftime("%Y-%m-%d")


class Reservation:
    """판정 1회분을 미리 차감해 둔 표. 첫 외부 호출이 이것을 쓰고, 이중 차감하지 않는다."""

    def __init__(self):
        self.used = False

    def take(self) -> bool:
        if self.used:
            return False
        self.used = True
        return True


class BudgetGate:
    def __init__(self, db_path: Path, daily_limit: int, clock=time.time):
        self.db_path = db_path
        self.daily_limit = daily_limit
        self.clock = clock

    def consume(self) -> None:
        """외부 호출 1회분을 차감한다. 남은 예산이 없으면 BudgetExhausted."""
        day = kst_day(self.clock())
        conn = connect(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("INSERT OR IGNORE INTO budget_daily (day, used) VALUES (?, 0)", (day,))
            cur = conn.execute(
                "UPDATE budget_daily SET used = used + 1 WHERE day = ? AND used < ?", (day, self.daily_limit)
            )
            conn.execute("COMMIT")
        finally:
            conn.close()
        if cur.rowcount == 0:
            raise BudgetExhausted("오늘 체험 한도에 도달했습니다.")

    def reserve(self) -> Reservation:
        """그래프를 실행하기 전에 판정 1회분을 미리 차감한다(설계 §7.0)."""
        self.consume()
        return Reservation()

    def used_today(self) -> int:
        conn = connect(self.db_path)
        try:
            row = conn.execute("SELECT used FROM budget_daily WHERE day = ?", (kst_day(self.clock()),)).fetchone()
            return row["used"] if row else 0
        finally:
            conn.close()
