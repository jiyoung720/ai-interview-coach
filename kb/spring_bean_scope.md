# Spring Bean과 Scope

Bean은 Spring 컨테이너가 관리하는 객체를 말한다. @Component, @Service, @Repository 같은 어노테이션을 붙이면 컴포넌트 스캔을 통해 자동으로 Bean으로 등록된다.

Bean은 기본적으로 싱글톤 스코프로 관리되어, 애플리케이션 전체에서 하나의 인스턴스만 생성되고 재사용된다.
