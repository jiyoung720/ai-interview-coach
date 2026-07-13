# OAuth 2.0

OAuth 2.0은 사용자가 자신의 비밀번호를 제3자 애플리케이션에 직접 노출하지 않고도, 특정 서비스에 대한 접근 권한을 위임할 수 있게 하는 인가(Authorization) 프로토콜이다. "OAuth로 로그인하기" 버튼이 대표적인 사용 예시다.
핵심 참여자는 네 가지다. Resource Owner(사용자), Client(권한을 위임받으려는 애플리케이션), Authorization Server(권한을 발급하는 서버), Resource Server(실제 데이터를 가진 서버)로 구성된다.
가장 널리 쓰이는 흐름은 Authorization Code Grant다. 사용자가 Authorization Server에서 로그인하고 동의하면, Client는 Authorization Code를 받고, 이 코드를 다시 Access Token으로 교환한다. 이 과정에서 Access Token이 브라우저를 통해 직접 노출되지 않아 보안성이 높다.
OAuth는 "인증(누구인지 확인)"이 아니라 "인가(무엇을 할 수 있는지 허용)"를 위한 프로토콜이라는 점이 중요하다. OAuth 위에 신원 확인 계층을 얹은 것이 OpenID Connect(OIDC)이며, 실제 서비스에서는 이 둘을 함께 쓰는 경우가 많다.
OAuth는 권한 위임을 위한 프로토콜이고, JWT는 토큰의 형식을 정의하는 표준이다. 서로 다른 계층의 개념이라, OAuth의 Access Token을 JWT 형식으로 발급할 수도 있고, 서버가 별도로 관리하는 불투명(opaque) 토큰으로 발급할 수도 있다.
