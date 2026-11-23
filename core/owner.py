# 익명 사용자 식별: 서명된 owner_id 쿠키 (설계 §7.3).
#
# 로그인이 없으므로 브라우저마다 무작위 owner_id를 발급하고, 위조를 막으려고 HMAC 서명을 붙인다.
# 서명이 맞지 않거나 쿠키가 없으면 새로 발급한다. 세션·리포트는 이 값이 같아야 접근할 수 있다.
import hashlib
import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

COOKIE_NAME = "owner_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30   # 30일. 세션 자체의 만료(7일)와는 별개다


def sign(owner_id: str, secret: str) -> str:
    mac = hmac.new(secret.encode(), owner_id.encode(), hashlib.sha256).hexdigest()
    return f"{owner_id}.{mac}"


def verify(cookie: str | None, secret: str) -> str | None:
    """서명이 맞으면 owner_id를, 아니면 None을 돌려준다."""
    if not cookie or "." not in cookie:
        return None
    owner_id, _, _ = cookie.partition(".")
    return owner_id if hmac.compare_digest(sign(owner_id, secret), cookie) else None


class OwnerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret: str, secure: bool):
        super().__init__(app)
        self.secret = secret
        self.secure = secure

    async def dispatch(self, request: Request, call_next):
        owner_id = verify(request.cookies.get(COOKIE_NAME), self.secret)
        issued = owner_id is None
        if issued:
            owner_id = secrets.token_urlsafe(16)
        request.state.owner_id = owner_id

        response = await call_next(request)
        if issued:
            response.set_cookie(
                COOKIE_NAME,
                sign(owner_id, self.secret),
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
                secure=self.secure,   # 공개 서버(HTTPS)에서만 Secure. 로컬 http에서는 쿠키가 안 붙으므로 끈다
            )
        return response


def owner_id_of(request: Request) -> str:
    return request.state.owner_id
