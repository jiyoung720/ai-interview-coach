# .env 파일의 값을 환경변수로 읽어오는 설정 파일
import os
from dotenv import load_dotenv

load_dotenv()   # .env 파일을 읽어 os.environ에 채움

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# 모델을 코드에 하드코딩하지 않고 .env로 분리 (없으면 gemini-3.5-flash).
# gemini-flash-latest 같은 auto-update alias를 안 쓰는 이유: Google이 가리키는 모델이
# 바뀌면 평가 기준 모델도 바뀌어 RAGAS 결과의 재현성이 깨지므로 버전을 명시적으로 고정
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
