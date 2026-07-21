# uv 공식 이미지를 베이스로 사용 (로컬과 동일한 패키지 매니저로 통일)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# UV_COMPILE_BYTECODE: 기동 속도를 위해 빌드 시점에 .pyc 생성
# UV_LINK_MODE=copy: 캐시 마운트와 다른 파일시스템일 때 뜨는 하드링크 경고 방지
# HF_HOME: 임베딩 모델 캐시 위치를 이미지 안으로 고정 (런타임 다운로드 없이 동작)
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/app/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# 의존성만 먼저 설치해 레이어 캐시를 활용한다.
# 코드만 바뀌면 이 레이어는 재사용되므로 재빌드가 빨라진다.
COPY pyproject.toml uv.lock ./

# 이 이미지에 한해 CPU 전용 torch를 쓴다.
# PyPI 기본 torch 휠은 linux에서 CUDA 스택을 함께 설치하는데(nvidia 2.9GB + triton 652MB),
# 배포 대상(EC2)에는 GPU가 없어 3.5GB가 전부 쓰이지 않는 용량이었다.
# pyproject.toml 자체를 고치지 않고 여기서만 처리하는 이유:
# 로컬(macOS)과 Colab(GPU 사용) 환경까지 CPU torch로 묶이는 것을 피하기 위함.
#
# 두 가지가 함께 필요하다:
#  1) torch를 직접 의존성으로 추가. tool.uv.sources는 직접 의존성에만 적용되는데
#     torch는 sentence-transformers를 통한 전이 의존성이라 그냥 두면 무시된다.
#  2) 인덱스를 explicit = true로 제한. 그러지 않으면 requests 등 다른 패키지까지
#     pytorch 인덱스에서 찾으려다 resolve가 실패한다.
RUN awk '!done && /^]/ { print "    \"torch==2.13.0\","; done=1 } { print }' pyproject.toml > /tmp/p \
    && mv /tmp/p pyproject.toml \
    && printf '\n[[tool.uv.index]]\nname = "pytorch-cpu"\nurl = "https://download.pytorch.org/whl/cpu"\nexplicit = true\n\n[tool.uv.sources]\ntorch = { index = "pytorch-cpu" }\n' >> pyproject.toml \
    && uv lock

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# 애플리케이션 코드
COPY app/ app/
COPY api/ api/
COPY rag/ rag/
COPY kb/ kb/
COPY scripts/ scripts/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# 임베딩 모델(ko-sroberta-multitask)을 빌드 시점에 미리 받아둔다.
# 런타임에 받게 하면 첫 요청이 크게 느려지고, 네트워크에 의존하게 된다.
RUN python -c "from rag.embeddings import get_embeddings; get_embeddings()"

# volume 마운트 지점. 컨테이너를 지워도 인덱스와 업로드 파일은 남는다
VOLUME ["/app/chroma_db", "/app/data/uploads"]

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
