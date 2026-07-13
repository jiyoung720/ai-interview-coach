# HTTP와 REST

HTTP 메서드는 클라이언트가 서버에 요청하는 작업의 종류를 나타낸다. GET은 리소스 조회, POST는 리소스 생성, PUT은 리소스 전체 교체, PATCH는 리소스 일부 수정, DELETE는 리소스 삭제에 사용된다. GET과 달리 POST, PUT, DELETE 등은 서버 상태를 변경할 수 있다.

HTTP 상태 코드는 응답의 결과를 숫자로 나타낸다. 2xx는 성공(200 OK, 201 Created), 3xx는 리다이렉션, 4xx는 클라이언트 오류(400 Bad Request, 401 Unauthorized, 404 Not Found), 5xx는 서버 오류(500 Internal Server Error)를 의미한다. 401은 인증 실패, 403은 권한 부족을 나타내며 이 둘은 자주 혼동된다.

REST(Representational State Transfer)는 자원을 URI로 표현하고 HTTP 메서드로 행위를 표현하는 아키텍처 스타일이다. 예를 들어 `/users/1`이라는 URI에 GET을 보내면 조회, DELETE를 보내면 삭제로 해석되며, URI 자체에 동사를 넣지 않는 것이 REST 원칙에 부합한다.

멱등성(Idempotency)은 같은 요청을 여러 번 보내도 결과가 동일한 성질을 말한다. GET, PUT, DELETE는 멱등하지만 POST는 멱등하지 않다 — 같은 POST 요청을 두 번 보내면 리소스가 두 번 생성될 수 있기 때문이다. 인증이 필요한 요청에서는 일반적으로 `Authorization: Bearer <토큰>` 형태의 헤더에 Access Token을 담아 전달한다.
