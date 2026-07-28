"""시연·테스트용 가상 이력서 PDF를 만든다.

실제 사람의 이력서를 테스트에 쓰지 않으려고 둔 스크립트다. 내용은 Interview KB
(jwt, fastapi, postgresql_index, docker, caching, async_sync 등)와 주제가 맞물리도록
구성해, 생성되는 질문과 채점이 근거를 갖도록 했다.

reportlab은 이 스크립트에서만 쓰는 도구라 프로젝트 의존성에 넣지 않는다.
실행 전에 임시로 설치하고 끝나면 제거한다 (lock 파일을 오염시키지 않기 위함).

    uv pip install reportlab
    uv run python -m scripts.make_sample_resume
    uv pip uninstall reportlab

macOS 기본 도구인 cupsfilter로 만든 PDF는 한글 폰트를 제대로 임베딩하지 못해
텍스트 추출 시 글자가 깨진다(Phase 9에서 확인). 그래서 AppleGothic을 명시적으로
등록해 사용한다.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
FONT_NAME = "AppleGothic"
OUTPUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_resume_ko.pdf"

# 실존 인물로 오해되지 않도록 관용적인 가명을 쓴다
RESUME = [
    ("title", "홍길동 (가상 인물 · 테스트용 이력서)"),
    ("sub", "백엔드 개발자 지원 | example@test.invalid"),
    ("h", "기술 스택"),
    ("p", "Python, FastAPI, Spring Boot, PostgreSQL, Redis, Docker, GitHub Actions"),
    ("h", "프로젝트 1. 커뮤니티 API 서버"),
    ("p", "FastAPI로 게시판·댓글 API를 구현했습니다. 인증은 JWT 기반으로 처리했고, "
          "Access Token과 Refresh Token을 분리해 발급했습니다. 토큰이 탈취됐을 때 "
          "서버에서 무효화할 방법이 없다는 점이 문제가 되어, 로그아웃 시 Refresh Token을 "
          "블랙리스트로 관리하는 방식을 적용했습니다."),
    ("p", "게시글 목록 조회가 느려져 원인을 확인해보니 정렬 컬럼에 인덱스가 없었습니다. "
          "PostgreSQL에서 실행 계획을 확인하고 인덱스를 추가해 응답 시간을 줄였습니다. "
          "조회가 잦은 인기글 목록은 Redis에 캐싱했습니다."),
    ("p", "배포는 Docker로 이미지를 만들어 진행했고, GitHub Actions로 테스트와 "
          "빌드를 자동화했습니다."),
    ("h", "프로젝트 2. 실시간 알림 서비스"),
    ("p", "외부 API를 호출해 알림을 보내는 서비스입니다. 요청이 몰릴 때 응답이 "
          "느려지는 문제가 있어, 동기 처리와 비동기 처리의 차이를 확인하고 "
          "async/await 기반으로 전환했습니다. I/O 대기가 대부분인 작업이라 "
          "동시 처리량이 개선됐습니다."),
    ("p", "프론트엔드와 서버의 출처가 달라 브라우저에서 요청이 차단되는 문제를 겪었고, "
          "CORS 설정을 통해 허용 출처를 명시하는 방식으로 해결했습니다."),
    ("h", "프로젝트 3. 사내 관리 도구 (Spring Boot)"),
    ("p", "Spring Boot로 관리자 페이지를 개발했습니다. 컨트롤러·서비스·리포지토리로 "
          "계층을 나누어 구성했고, 의존성 주입을 활용해 테스트 시 외부 연동을 "
          "대체할 수 있도록 했습니다. 세션 기반 인증을 사용했는데, 서버가 여러 대로 "
          "늘어나면 세션 공유가 필요하다는 점을 확인했습니다."),
    ("h", "관심 분야"),
    ("p", "서비스가 왜 느린지, 왜 그렇게 동작하는지를 추측이 아니라 측정으로 "
          "확인하는 작업에 관심이 있습니다."),
]


def build() -> None:
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle("t", parent=base["Title"], fontName=FONT_NAME, fontSize=17, spaceAfter=4),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontName=FONT_NAME, fontSize=10,
                              textColor="#555555", spaceAfter=14),
        "h": ParagraphStyle("h", parent=base["Heading2"], fontName=FONT_NAME, fontSize=12,
                            spaceBefore=12, spaceAfter=5),
        "p": ParagraphStyle("p", parent=base["Normal"], fontName=FONT_NAME, fontSize=10,
                            leading=16, spaceAfter=7),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
        title="샘플 이력서 (테스트용)",
    )

    flow = []
    for kind, text in RESUME:
        flow.append(Paragraph(text, styles[kind]))
    flow.append(Spacer(1, 6 * mm))

    doc.build(flow)
    print(f"생성 완료: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
