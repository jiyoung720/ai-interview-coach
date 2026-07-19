# Spring 제어의 역전과 의존성 주입

Spring은 Java 기반 엔터프라이즈 애플리케이션 프레임워크로, 핵심 개념은 제어의 역전(IoC, Inversion of Control)과 의존성 주입(DI, Dependency Injection)이다. 객체 생성과 생명주기 관리를 개발자가 직접 하지 않고 Spring 컨테이너에 위임함으로써, 클래스 간 결합도를 낮추고 테스트하기 쉬운 구조를 만든다.

Spring에서는 @Autowired로 의존성을 주입하는데, 이는 FastAPI의 Depends()와 개념적으로 유사하다. 둘 다 객체 생성을 프레임워크에 위임해 결합도를 낮춘다.
