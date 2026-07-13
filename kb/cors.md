# CORS (Cross-Origin Resource Sharing)

브라우저는 보안을 위해 기본적으로 다른 출처(origin)로의 요청을 차단하는 동일 출처 정책(Same-Origin Policy)을 따른다. CORS는 서버가 특정 다른 출처의 요청을 명시적으로 허용할 수 있게 하는 메커니즘이다. 출처는 프로토콜, 도메인, 포트가 모두 같아야 동일한 것으로 간주된다.

서버는 응답 헤더에 `Access-Control-Allow-Origin`을 포함시켜 어떤 출처의 요청을 허용할지 지정한다. GET, POST 같은 단순 요청 외에 커스텀 헤더를 쓰거나 PUT/DELETE를 쓰는 경우, 브라우저는 실제 요청 전에 OPTIONS 메서드로 사전 요청(Preflight Request)을 보내 서버가 허용하는지 먼저 확인한다.

인증 토큰을 쿠키에 저장해 다른 출처로 요청을 보내는 경우, 기본적으로 쿠키는 요청에 포함되지 않는다. 클라이언트에서는 `credentials: 'include'`, 서버에서는 `Access-Control-Allow-Credentials: true`를 함께 설정해야 인증 정보가 포함된 요청이 정상적으로 처리된다.

JWT를 Authorization 헤더로 전달하는 방식은 쿠키 기반 인증보다 CORS 설정이 비교적 단순하다 — 헤더는 요청마다 명시적으로 담아 보내는 것이라 자동으로 전송되는 쿠키와 달리 Credential 관련 CORS 설정이 필요 없는 경우가 많다.
