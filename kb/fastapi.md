# FastAPI

FastAPI는 Python 기반의 비동기 웹 프레임워크로, ASGI(Asynchronous Server Gateway Interface) 위에서 동작한다. Flask나 Django REST Framework 같은 WSGI 기반 프레임워크와 비교했을 때, I/O 바운드 작업(DB 조회, 외부 API 호출 등)에서 더 높은 처리량을 낼 수 있다.

`async def`로 선언된 엔드포인트는 I/O 대기 중에도 다른 요청을 처리할 수 있어, LLM API 호출이나 외부 서비스 연동처럼 지연 시간이 긴 작업에 특히 유리하다. 다만 CPU 바운드 작업에는 비동기가 자동으로 이점을 주지 않으며, 별도의 스레드 풀이나 백그라운드 작업 큐가 필요하다.

FastAPI는 Pydantic을 기반으로 요청/응답 데이터를 검증한다. 타입 힌트만으로 자동으로 유효성 검사를 수행하고, 검증에 실패하면 422 에러를 자동으로 반환한다. 이 덕분에 별도의 검증 로직을 직접 작성할 필요가 줄어든다.

Dependency Injection(`Depends`)을 통해 DB 세션 관리, 인증 토큰 검증 같은 반복 로직을 엔드포인트 함수 밖으로 분리할 수 있다. 또한 타입 힌트 기반으로 OpenAPI(Swagger) 문서를 자동 생성해주기 때문에, 별도 문서화 작업 없이도 API 명세를 공유할 수 있다.
