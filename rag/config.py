# .env 파일의 값을 환경변수로 읽어오는 설정 파일
import os
from dotenv import load_dotenv

load_dotenv()   # .env 파일을 읽어 os.environ에 채움

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# 모델을 코드에 하드코딩하지 않고 .env로 분리 (없으면 gemini-3.5-flash).
# gemini-flash-latest 같은 auto-update alias를 안 쓰는 이유: Google이 가리키는 모델이
# 바뀌면 평가 기준 모델도 바뀌어 RAGAS 결과의 재현성이 깨지므로 버전을 명시적으로 고정
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# 1순위 문서와의 거리가 이 값 이상이면 "고정 지식에 근거가 없다"로 보고 채점을 보류한다 (Phase 17).
# 65문항 평가셋(범위 안 38 / 범위 밖 27)에서 group 5-fold 교차 검증으로 정했다.
#   재현율 100%, 정밀도 93.8%, 범위 안 통과 93.3%
# 거리 절대값은 임베딩 모델과 KB 내용에 종속되므로, 둘 중 하나라도 바뀌면
# scripts/calibrate_scope_threshold.py --refresh 로 다시 정해야 한다.
SCOPE_DISTANCE_THRESHOLD = float(os.getenv("SCOPE_DISTANCE_THRESHOLD", "0.311"))
