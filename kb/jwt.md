# JWT (JSON Web Token)

JWT는 사용자 인증 정보를 안전하게 전달하기 위한 토큰 기반 인증 방식이다. Header, Payload, Signature 세 부분이 점(.)으로 구분되어 하나의 문자열로 구성되며, 서버는 별도의 세션 저장소 없이도 토큰 자체에 담긴 서명을 검증해 사용자를 인증할 수 있다.

Access Token은 짧은 만료 시간을 가지며 실제 API 요청 인증에 사용된다. Refresh Token은 상대적으로 긴 만료 시간을 가지며, Access Token이 만료됐을 때 재발급을 위해서만 사용된다. 이렇게 역할을 분리하면 Access Token이 탈취되더라도 피해 시간을 짧게 제한할 수 있다.

JWT를 저장하는 위치는 보안과 직결된다. LocalStorage에 저장하면 XSS 공격에 취약하고, 일반 Cookie에 저장하면 CSRF 공격에 취약하다. 이를 보완하기 위해 HttpOnly + Secure + SameSite 속성을 적용한 Cookie에 저장하는 방식이 널리 권장된다.

JWT는 발급 이후 서버가 강제로 무효화하기 어렵다는 한계가 있다. 로그아웃이나 토큰 탈취 상황에 대응하기 위해 Refresh Token을 DB에 저장해두고 블랙리스트로 관리하는 방식이 흔히 사용된다.
