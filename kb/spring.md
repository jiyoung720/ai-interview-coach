# Spring / Spring Boot

Spring은 Java 기반 엔터프라이즈 애플리케이션 프레임워크로, 핵심 개념은 제어의 역전(IoC, Inversion of Control)과 의존성 주입(DI, Dependency Injection)이다. 객체 생성과 생명주기 관리를 개발자가 직접 하지 않고 Spring 컨테이너에 위임함으로써, 클래스 간 결합도를 낮추고 테스트하기 쉬운 구조를 만든다.

Spring Boot는 Spring의 복잡한 설정을 자동화한 확장판이다. 별도의 XML 설정 없이 어노테이션(`@SpringBootApplication`, `@RestController` 등) 기반으로 애플리케이션을 빠르게 구성할 수 있고, 내장 톰캣 서버 덕분에 별도의 WAS 설치 없이 바로 실행 가능하다.

Bean은 Spring 컨테이너가 관리하는 객체를 말한다. `@Component`, `@Service`, `@Repository` 같은 어노테이션을 붙이면 컴포넌트 스캔을 통해 자동으로 Bean으로 등록된다. Spring에서는 `@Autowired`로 의존성을 주입하는데, 이는 FastAPI의 `Depends()`와 개념적으로 유사하다 — 둘 다 객체 생성을 프레임워크에 위임해 결합도를 낮춘다.

계층형 아키텍처(Controller-Service-Repository)를 통해 관심사를 분리하는 것이 Spring의 일반적인 설계 패턴이다. Controller는 요청/응답 처리, Service는 비즈니스 로직, Repository는 데이터 접근을 담당해 각 계층의 책임을 명확히 나눈다.
