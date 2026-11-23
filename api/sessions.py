"""v2 세션 API (설계 §8). 공통 라우터라 데모·로컬 모드 모두 등록된다.

M0에서는 가짜 판정으로 도는 골격 엔진에 연결된다. 진짜 판정·계획은 M2에서 엔진만 바꾼다.
같은 요청이 여러 번 와도 결과가 한 번만 반영되도록, 생성과 이벤트 모두 Idempotency-Key 헤더를 받는다.
"""
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from core.owner import owner_id_of

router = APIRouter(prefix="/sessions")


class CreateSessionRequest(BaseModel):
    sample_id: str | None = None
    document_id: str | None = None
    mode: str = "practice"


class EventRequest(BaseModel):
    question_id: str
    version: int
    action: str = "answer"            # answer | skip | end
    answer: str | None = Field(default=None)


def _service(request: Request):
    return request.app.state.session_service


def _require_key(key: str | None) -> str:
    if not key:
        raise HTTPException(status_code=400, detail="Idempotency-Key 헤더가 필요합니다.")
    return key


@router.post("")
def create_session(body: CreateSessionRequest, request: Request,
                   idempotency_key: str | None = Header(default=None)):
    client_ip = request.client.host if request.client else None
    return _service(request).create(owner_id_of(request), _require_key(idempotency_key),
                                    body.model_dump(), client_ip=client_ip)


@router.get("/{session_id}")
def get_session(session_id: str, request: Request):
    return _service(request).get(owner_id_of(request), session_id)


@router.post("/{session_id}/events")
def submit_event(session_id: str, body: EventRequest, request: Request,
                 idempotency_key: str | None = Header(default=None)):
    return _service(request).submit(owner_id_of(request), session_id, _require_key(idempotency_key),
                                    body.model_dump())


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str, request: Request):
    _service(request).delete(owner_id_of(request), session_id)
    return Response(status_code=204)
