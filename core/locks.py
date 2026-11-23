# 세션 단위 프로세스 내 잠금 (설계 §5.4).
#
# 같은 세션의 요청은 한 번에 하나만 처리한다. uvicorn 워커를 1개로 고정하는 이유가 이것이다.
# 세션 생성은 (owner_id, 생성 키) 단위로 잠가, 같은 키의 동시 요청이 계획을 두 번 실행하지 않게 한다.
import threading
from contextlib import contextmanager


class LockTimeout(Exception):
    """잠금을 제한 시간 안에 얻지 못했다. API는 409로 응답하고 클라이언트는 같은 키로 재시도한다."""


class KeyedLocks:
    def __init__(self):
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    def _lock_for(self, key: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    @contextmanager
    def hold(self, key: str, timeout: float = 30.0):
        lock = self._lock_for(key)
        if not lock.acquire(timeout=timeout):
            raise LockTimeout(key)
        try:
            yield
        finally:
            lock.release()

    def forget(self, key: str) -> None:
        """삭제된 세션의 잠금 객체를 치운다. 잠금을 쥔 상태에서 불러도 안전하다(다음 요청은 새 잠금을 쓴다)."""
        with self._guard:
            self._locks.pop(key, None)
