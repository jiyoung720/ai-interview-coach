# ai-interview-coach

RAG 기반 AI 면접 코치 — 사용자의 이력서/포트폴리오 문서를 기반으로 개인화된 기술 면접 질문을 생성하고, 답변을 평가하는 서비스입니다.

메인 프로젝트(`korean-chatbot`, GPT-style Transformer 직접 구현)와는 별도로, 기성 LLM(Gemini API)을 활용한 실서비스형 AI 시스템 구축·서빙·평가 경험을 보여주기 위한 프로젝트입니다.

## 기술 스택

- Backend: FastAPI
- RAG: LangChain, Chroma (`hnsw:space=cosine`)
- Embedding: `ko-sroberta-multitask`
- LLM: Gemini API (`gemini-3.5-flash`, structured output)

## 진행 상황

- [x] 문서 업로드 + 인덱싱 (`POST /documents`)
- [x] User Docs Retriever 의미 기반 검색 검증
- [x] Gemini 연동 + Chain A 질문 생성 (`POST /generate-question`)
- [ ] Interview KB 구축
- [ ] Chain B 답변 평가
- [ ] RAGAS 평가 + Judge Calibration

## API

### `POST /documents`
```bash
curl -X POST http://127.0.0.1:8000/documents -F "file=@tests/fixtures/sample_user_doc.md"
```

### `POST /generate-question`
```bash
curl -X POST http://127.0.0.1:8000/generate-question \
  -H "Content-Type: application/json" \
  -d '{"query": "JWT 관련 경험"}'
```
응답: `{"questions": ["...", "...", ...]}`

## 실행 방법

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # GEMINI_API_KEY 채우기
uvicorn app.main:app --reload
```

## 문서

- [프로젝트 명세서](docs/project_spec_v1.md)
- [실험 로그](docs/experiment_log.md)
