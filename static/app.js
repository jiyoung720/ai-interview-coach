// FastAPI가 이 파일을 같은 서버(localhost:8000)에서 서빙하므로,
// API 호출도 같은 origin으로 나간다 → CORS 문제가 없다.

const $ = (id) => document.getElementById(id);

// 현재 선택된 질문을 기억 (평가 요청 시 question으로 보냄)
let selectedQuestion = null;

// 공통 유틸: status 영역에 메시지 표시
function setStatus(el, message, type = "") {
  el.textContent = message;
  el.className = "status" + (type ? " " + type : "");
}

// 공통 유틸: 카드 활성화/비활성화
function enableStep(id) {
  $(id).classList.remove("disabled");
}

// ---- STEP 1: 문서 업로드 ----
$("upload-btn").addEventListener("click", async () => {
  const fileInput = $("file-input");
  const file = fileInput.files[0];
  if (!file) {
    setStatus($("upload-status"), "파일을 선택하세요.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  setStatus($("upload-status"), "업로드 중...", "loading");
  $("upload-btn").disabled = true;

  try {
    const res = await fetch("/documents", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `업로드 실패 (${res.status})`);
    }
    const data = await res.json();
    setStatus(
      $("upload-status"),
      `업로드 완료: ${data.filename} (chunk ${data.chunks_added}개 인덱싱)`,
      "success"
    );
    enableStep("step-questions");
  } catch (e) {
    setStatus($("upload-status"), e.message, "error");
  } finally {
    $("upload-btn").disabled = false;
  }
});

// ---- STEP 2: 질문 생성 ----
$("generate-btn").addEventListener("click", async () => {
  const query = $("query-input").value.trim() || "프로젝트 기술 스택";

  setStatus($("generate-status"), "질문 생성 중... (Gemini 호출, 몇 초 걸립니다)", "loading");
  $("generate-btn").disabled = true;

  try {
    const res = await fetch("/generate-question", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error(`질문 생성 실패 (${res.status})`);
    const data = await res.json();
    renderQuestions(data.questions);
    setStatus($("generate-status"), `질문 ${data.questions.length}개 생성됨. 하나를 선택하세요.`, "success");
    enableStep("step-answer");
  } catch (e) {
    setStatus($("generate-status"), e.message, "error");
  } finally {
    $("generate-btn").disabled = false;
  }
});

function renderQuestions(questions) {
  const list = $("question-list");
  list.innerHTML = "";
  questions.forEach((q) => {
    const li = document.createElement("li");
    li.textContent = q;
    li.addEventListener("click", () => selectQuestion(q, li));
    list.appendChild(li);
  });
}

function selectQuestion(question, li) {
  selectedQuestion = question;
  document.querySelectorAll(".question-list li").forEach((el) => el.classList.remove("selected"));
  li.classList.add("selected");
  const sel = $("selected-question");
  sel.textContent = "선택한 질문: " + question;
  sel.classList.add("active");
}

// ---- STEP 3: 답변 평가 ----
$("evaluate-btn").addEventListener("click", async () => {
  if (!selectedQuestion) {
    setStatus($("evaluate-status"), "위에서 질문을 먼저 선택하세요.", "error");
    return;
  }
  const answer = $("answer-input").value.trim();
  if (!answer) {
    setStatus($("evaluate-status"), "답변을 입력하세요.", "error");
    return;
  }

  setStatus($("evaluate-status"), "평가 중... (점수에 따라 Gemini를 여러 번 호출해 오래 걸릴 수 있습니다)", "loading");
  $("evaluate-btn").disabled = true;
  $("result").innerHTML = "";

  try {
    const res = await fetch("/evaluate-answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: selectedQuestion, answer }),
    });
    if (!res.ok) throw new Error(`평가 실패 (${res.status})`);
    const data = await res.json();
    renderResult(data);
    setStatus($("evaluate-status"), "", "");
  } catch (e) {
    setStatus($("evaluate-status"), e.message, "error");
  } finally {
    $("evaluate-btn").disabled = false;
  }
});

// 점수 구간에 따라 뱃지 색을 다르게
function scoreClass(score) {
  if (score >= 7) return "good";
  if (score >= 4) return "mid";
  return "bad";
}

function renderResult(data) {
  const box = document.createElement("div");
  box.className = "result-box";

  // 점수 뱃지
  const scores = document.createElement("div");
  scores.className = "score-row";
  scores.innerHTML = `
    <span class="score-badge ${scoreClass(data.technical_score)}">기술 정확성 ${data.technical_score}/10</span>
    <span class="score-badge ${scoreClass(data.completeness_score)}">완성도 ${data.completeness_score}/10</span>
  `;
  box.appendChild(scores);

  // 전반 피드백
  if (data.overall_feedback) {
    box.appendChild(el("p", data.overall_feedback));
  }
  // 강점 / 개선점
  if (data.strengths?.length) {
    box.appendChild(el("h4", "강점"));
    box.appendChild(list(data.strengths));
  }
  if (data.improvements?.length) {
    box.appendChild(el("h4", "개선점"));
    box.appendChild(list(data.improvements));
  }

  // 점수 구간별 코칭 (셋 중 하나만 채워짐)
  if (data.concept_explanation) {
    box.appendChild(conceptBlock(data.concept_explanation));
  }
  if (data.learning_tip) {
    box.appendChild(learningTipBlock(data.learning_tip, data.followup_question));
  }
  if (data.advanced_question) {
    box.appendChild(advancedBlock(data.advanced_question));
  }

  // 검색 출처
  if (data.retrieved_sources?.length) {
    const s = el("p", "참고한 자료: " + data.retrieved_sources.join(", "));
    s.className = "sources";
    box.appendChild(s);
  }

  $("result").appendChild(box);
}

// 0~3점: 개념 설명
function conceptBlock(c) {
  const d = document.createElement("div");
  d.className = "coaching";
  d.innerHTML = `<span class="tag">기초 개념 설명</span>`;
  d.appendChild(el("h4", c.concept));
  d.appendChild(el("p", c.explanation));
  if (c.key_points?.length) {
    d.appendChild(el("h4", "핵심 포인트"));
    d.appendChild(list(c.key_points));
  }
  return d;
}

// 4~6점: 학습 팁 + 꼬리질문
function learningTipBlock(tip, followup) {
  const d = document.createElement("div");
  d.className = "coaching";
  d.innerHTML = `<span class="tag">학습 팁</span>`;
  d.appendChild(el("h4", tip.topic));
  d.appendChild(el("p", tip.reason));
  if (tip.recommended_sections?.length) {
    d.appendChild(el("p", "추천 학습: " + tip.recommended_sections.join(", ")));
  }
  if (followup) {
    d.appendChild(el("h4", "꼬리 질문"));
    d.appendChild(el("p", followup));
  }
  return d;
}

// 7~10점: 심화 질문
function advancedBlock(adv) {
  const d = document.createElement("div");
  d.className = "coaching";
  d.innerHTML = `<span class="tag">심화 질문</span>`;
  d.appendChild(el("p", adv.question));
  if (adv.intent) {
    d.appendChild(el("p", "출제 의도: " + adv.intent));
  }
  return d;
}

// 작은 헬퍼들
function el(tag, text) {
  const e = document.createElement(tag);
  e.textContent = text;
  return e;
}
function list(items) {
  const ul = document.createElement("ul");
  items.forEach((it) => ul.appendChild(el("li", it)));
  return ul;
}
