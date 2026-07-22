"""API 응답 시간 측정.

`/evaluate-answer`는 technical_score 구간에 따라 실행되는 노드가 달라지고,
그에 따라 Gemini 호출 횟수도 달라진다.

    0~3점  : Judge + Fundamentals        = 2회
    4~6점  : Judge + LearningTip + Followup = 3회
    7~10점 : Judge + Advanced            = 2회

즉 같은 엔드포인트인데도 분기에 따라 지연이 달라질 것으로 예상된다.
Agent를 순차 설계한 대가(일관성 확보 vs 지연 증가)를 정성적 설명이 아니라
수치로 확인하는 것이 목적이다.

사용법:
    BASE_URL=http://<퍼블릭IP>:8000 uv run python -m scripts.measure_api_latency
    (미지정 시 http://127.0.0.1:8000)
"""
import json
import os
import statistics
import time
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
REPEAT = int(os.getenv("REPEAT", "3"))

# 각 구간의 점수가 나오도록 설계한 답변들.
# Day 4 경계값 탐색과 Phase 7 분기 검증에서 쓰던 것과 같은 답변을 재사용한다.
CASES = [
    (
        "0~3점 (Judge + Fundamentals, 2회 호출)",
        "잘 모르겠습니다.",
    ),
    (
        "4~6점 (Judge + LearningTip + Followup, 3회 호출)",
        "JWT는 Payload에 사용자 정보를 담은 토큰으로, 서버가 이 토큰을 검증해서 "
        "사용자를 인증합니다. 다만 토큰이 만료되면 자동으로 갱신됩니다.",
    ),
    (
        "7~10점 (Judge + Advanced, 2회 호출)",
        "JWT는 JSON Web Token의 약자로 Header, Payload, Signature 세 부분으로 "
        "구성됩니다. 서버가 비밀키로 서명하고, 검증 시 서명을 확인하므로 별도의 "
        "세션 저장소 없이 stateless하게 사용자를 인증할 수 있습니다.",
    ),
]

QUESTION = "JWT란 무엇인가?"


def post_json(path: str, payload: dict, timeout: int = 180):
    """요청을 보내고 (소요 시간, 응답)을 반환한다."""
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = json.loads(res.read().decode("utf-8"))
    return time.perf_counter() - start, body


def measure_health():
    """헬스체크 지연. LLM 호출이 없는 기준선이라, 순수 네트워크 왕복 시간에 가깝다.
    이 값을 빼면 평가 엔드포인트에서 LLM 처리가 차지하는 비중을 가늠할 수 있다."""
    times = []
    for _ in range(5):
        start = time.perf_counter()
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=30) as res:
            res.read()
        times.append(time.perf_counter() - start)
    return times


def main():
    print(f"대상: {BASE_URL}")
    print(f"케이스당 반복: {REPEAT}회\n")

    print("=" * 64)
    print("[기준선] GET / (LLM 호출 없음)")
    print("=" * 64)
    health = measure_health()
    baseline = statistics.median(health)
    print(f"  중앙값 {baseline*1000:.1f}ms  (최소 {min(health)*1000:.1f} / 최대 {max(health)*1000:.1f})")

    print()
    print("=" * 64)
    print("[평가] POST /evaluate-answer (분기별)")
    print("=" * 64)

    results = []
    for label, answer in CASES:
        times = []
        action = None
        score = None
        for _ in range(REPEAT):
            elapsed, body = post_json(
                "/evaluate-answer", {"question": QUESTION, "answer": answer}
            )
            times.append(elapsed)
            action = body.get("next_action")
            score = body.get("technical_score")

        median = statistics.median(times)
        results.append((label, score, action, median, times))

        print(f"\n{label}")
        print(f"  technical_score={score}  next_action={action}")
        print(f"  중앙값 {median:.2f}s  (최소 {min(times):.2f} / 최대 {max(times):.2f})")
        print(f"  개별: {', '.join(f'{t:.2f}s' for t in times)}")

    print()
    print("=" * 64)
    print("요약")
    print("=" * 64)
    print(f"{'분기':<40} {'중앙값':>10} {'기준선 제외':>12}")
    for label, _, _, median, _ in results:
        short = label.split(" (")[0]
        print(f"{short:<40} {median:>9.2f}s {median-baseline:>11.2f}s")

    fastest = min(results, key=lambda r: r[3])
    slowest = max(results, key=lambda r: r[3])
    print(f"\n가장 느린 분기가 가장 빠른 분기의 {slowest[3]/fastest[3]:.2f}배")
    print(f"  빠름: {fastest[0].split(' (')[0]} ({fastest[3]:.2f}s)")
    print(f"  느림: {slowest[0].split(' (')[0]} ({slowest[3]:.2f}s)")


if __name__ == "__main__":
    main()
