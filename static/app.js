// FastAPI가 이 파일을 같은 서버(localhost:8000)에서 서빙하므로,
// API 호출도 같은 origin으로 나간다 → CORS 문제가 없다.

const $ = (id) => document.getElementById(id);

// ---- 테마(라이트/다크) 토글 ----
// 사용자의 선택을 localStorage에 저장해 새로고침해도 유지한다.
(function initTheme() {
  const saved = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);

  const toggle = document.getElementById("theme-toggle");
  toggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  });
})();

// ---- 면접 세션 상태 ----
// sessionId가 없으면 아직 시작 전이라 /interview/start로, 있으면 /interview/answer로 보낸다.
let sessionId = null;
let currentQuestion = null;   // 지금 화면에서 답해야 할 질문

// 공통 유틸: status 영역에 메시지 표시.
// label을 주면 그 부분만 굵게 나온다 (예: "업로드 완료:" + 파일명).
// textContent로만 넣어 사용자 입력이 HTML로 해석되지 않게 한다.
function setStatus(el, message, type = "", label = "") {
  el.className = "status" + (type ? " " + type : "");
  el.textContent = "";
  if (label) {
    const strong = document.createElement("strong");
    strong.textContent = label;
    el.appendChild(strong);
    el.appendChild(document.createTextNode(" " + message));
  } else {
    el.textContent = message;
  }
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
      `${data.filename} (chunk ${data.chunks_added}개 인덱싱)`,
      "success",
      "업로드 완료:"
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
    setStatus(
      $("generate-status"),
      "아래에서 하나를 선택하세요.",
      "success",
      `질문 ${data.questions.length}개 생성됨.`
    );
    enableStep("step-interview");
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
  // 세션이 진행 중이면 질문을 바꿀 수 없다. 그래프가 그 세션의 흐름을 들고 있기 때문에,
  // 중간에 다른 질문으로 갈아타면 이어지던 맥락이 깨진다.
  if (sessionId) {
    setStatus($("interview-status"), "진행 중인 면접이 있습니다. 끝내거나 다시 시작해주세요.", "error");
    return;
  }
  currentQuestion = question;
  document.querySelectorAll(".question-list li").forEach((el) => el.classList.remove("selected"));
  li.classList.add("selected");

  $("interview-hint").textContent = "아래 질문에 답하면 면접이 시작됩니다. 최대 3턴까지 이어집니다.";
  showCurrentQuestion(question, "첫 질문");
}

// ---- STEP 3: 멀티턴 면접 ----
$("submit-btn").addEventListener("click", async () => {
  if (!currentQuestion) {
    setStatus($("interview-status"), "위에서 질문을 먼저 선택하세요.", "error");
    return;
  }
  const answer = $("answer-input").value.trim();
  if (!answer) {
    setStatus($("interview-status"), "답변을 입력하세요.", "error");
    return;
  }

  setStatus($("interview-status"), "평가 중... (Gemini를 여러 번 호출해 시간이 걸립니다)", "loading");
  $("submit-btn").disabled = true;

  // 이 답변이 어느 질문에 대한 것인지 미리 잡아둔다.
  // 응답이 오면 currentQuestion은 다음 질문으로 바뀌기 때문이다.
  const answeredQuestion = currentQuestion;

  try {
    const data = sessionId
      ? await postJSON("/interview/answer", { session_id: sessionId, answer })
      : await postJSON("/interview/start", { question: answeredQuestion, answer });

    sessionId = data.session_id;
    appendTurn(data, answeredQuestion, answer);

    if (data.status === "awaiting_answer") {
      currentQuestion = data.next_question;
      showCurrentQuestion(data.next_question, `턴 ${data.turn + 1} 질문`);
      $("answer-input").value = "";
      $("submit-btn").textContent = "답변 제출";
      setStatus($("interview-status"), "", "");
    } else {
      finishSession(data);
    }
  } catch (e) {
    setStatus($("interview-status"), e.message, "error");
  } finally {
    $("submit-btn").disabled = false;
  }
});

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `요청 실패 (${res.status})`);
  }
  return res.json();
}

// 지금 답해야 할 질문을 입력창 위에 띄운다
function showCurrentQuestion(question, label) {
  const box = $("current-question");
  box.innerHTML = "";
  const tag = document.createElement("span");
  tag.className = "q-label";
  tag.textContent = label;
  box.appendChild(tag);
  box.appendChild(el("p", question));
  box.hidden = false;
}

// 방금 끝난 한 턴을 타임라인에 쌓는다
function appendTurn(data, question, answer) {
  const turn = document.createElement("div");
  turn.className = "turn";

  const head = document.createElement("div");
  head.className = "turn-head";
  const no = document.createElement("span");
  no.className = "turn-no";
  no.textContent = `턴 ${data.turn}`;
  head.appendChild(no);
  head.appendChild(scoreBadges(data.evaluation));
  turn.appendChild(head);

  turn.appendChild(bubble("질문", question, "q"));
  turn.appendChild(bubble("내 답변", answer, "a"));

  const result = document.createElement("div");
  result.className = "turn-result";

  const evaluation = data.evaluation;
  if (evaluation.overall_feedback) result.appendChild(el("p", evaluation.overall_feedback));
  // 감점 내역을 강점·개선점보다 앞에 둔다. 점수를 본 직후에 "왜"가 바로 이어져야
  // 납득이 되고, 뒤로 밀리면 점수와 근거가 따로 읽힌다
  if (evaluation.deductions?.length) {
    result.appendChild(deductionBlock(evaluation.deductions));
  }
  if (evaluation.strengths?.length) {
    result.appendChild(el("h4", "강점"));
    result.appendChild(list(evaluation.strengths));
  }
  if (evaluation.improvements?.length) {
    result.appendChild(el("h4", "개선점"));
    result.appendChild(list(evaluation.improvements));
  }

  // 점수 구간별 코칭. 다음 질문 자체는 입력창 위에 따로 띄우므로 여기서는 뺀다
  // (같은 문장이 두 군데 나오면 어디에 답해야 하는지 헷갈린다)
  if (data.concept_explanation) result.appendChild(conceptBlock(data.concept_explanation));
  if (data.learning_tip) result.appendChild(learningTipBlock(data.learning_tip));
  if (data.advanced_question) result.appendChild(advancedIntentBlock(data.advanced_question));

  if (data.retrieved_sources?.length) {
    const s = el("p", "참고한 자료: " + data.retrieved_sources.join(", "));
    s.className = "sources";
    result.appendChild(s);
  }

  turn.appendChild(result);
  $("timeline").appendChild(turn);

  $("turn-badge").textContent = `턴 ${data.turn} / ${data.max_turns}`;
  $("turn-badge").hidden = false;
}

function finishSession(data) {
  $("current-question").hidden = true;
  $("answer-area").hidden = true;
  setStatus($("interview-status"), "", "");

  const reasons = {
    max_turns_reached: `${data.max_turns}턴을 모두 진행했습니다. 수고하셨습니다.`,
    fundamentals_no_followup: "기초 개념 설명으로 마무리했습니다. 개념을 익힌 뒤 다시 도전해보세요.",
    completed: "면접이 종료되었습니다.",
  };
  $("end-message").textContent = reasons[data.end_reason] || reasons.completed;
  $("session-end").hidden = false;
}

$("restart-btn").addEventListener("click", () => {
  sessionId = null;
  currentQuestion = null;
  $("timeline").innerHTML = "";
  $("answer-input").value = "";
  $("answer-area").hidden = false;
  $("session-end").hidden = true;
  $("current-question").hidden = true;
  $("turn-badge").hidden = true;
  $("submit-btn").textContent = "면접 시작";
  $("interview-hint").textContent = "위에서 질문을 선택하세요.";
  setStatus($("interview-status"), "", "");
  document.querySelectorAll(".question-list li").forEach((el) => el.classList.remove("selected"));
  $("step-questions").scrollIntoView({ behavior: "smooth", block: "center" });
});

// 점수 구간에 따라 뱃지 색을 다르게
function scoreClass(score) {
  if (score >= 7) return "good";
  if (score >= 4) return "mid";
  return "bad";
}

// 연차 레벨 표기. 서버는 영문 값으로 주고 화면에서만 한글로 바꾼다
// (값이 화면 문구와 묶이면 나중에 표현을 바꿀 때 서버까지 건드려야 한다)
const LEVEL_LABEL = { junior: "주니어 수준", middle: "미들 수준", senior: "시니어 수준" };

function scoreBadges(evaluation) {
  const wrap = document.createElement("div");
  wrap.className = "score-row";
  wrap.innerHTML = `
    <span class="score-badge ${scoreClass(evaluation.technical_score)}">기술 ${evaluation.technical_score}/10</span>
    <span class="score-badge ${scoreClass(evaluation.completeness_score)}">완성도 ${evaluation.completeness_score}/10</span>
  `;
  if (evaluation.level && LEVEL_LABEL[evaluation.level]) {
    const lv = document.createElement("span");
    lv.className = "level-badge " + evaluation.level;
    lv.textContent = LEVEL_LABEL[evaluation.level];
    wrap.appendChild(lv);
  }
  return wrap;
}

// 만점에서 무엇 때문에 깎였는지 보여준다.
// 점수만 주면 납득이 안 되므로, 감점 항목을 근거로 제시한다
function deductionBlock(deductions) {
  const d = document.createElement("div");
  d.className = "deductions";
  d.appendChild(el("h4", "감점 내역"));

  const list = document.createElement("ul");
  deductions.forEach((item) => {
    const li = document.createElement("li");
    const pts = document.createElement("span");
    pts.className = "deduct-points";
    pts.textContent = `-${item.points}`;
    li.appendChild(pts);
    li.appendChild(document.createTextNode(cleanText(item.reason)));
    list.appendChild(li);
  });
  d.appendChild(list);
  return d;
}

function bubble(label, text, kind) {
  const d = document.createElement("div");
  d.className = "bubble " + kind;
  const l = document.createElement("span");
  l.className = "bubble-label";
  l.textContent = label;
  d.appendChild(l);
  d.appendChild(el("p", text));
  return d;
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

// 4~6점: 학습 팁 (꼬리질문 자체는 다음 질문 자리에 표시된다)
function learningTipBlock(tip) {
  const d = document.createElement("div");
  d.className = "coaching";
  d.innerHTML = `<span class="tag">학습 팁</span>`;
  d.appendChild(el("h4", tip.topic));
  d.appendChild(el("p", tip.reason));
  if (tip.recommended_sections?.length) {
    d.appendChild(el("p", "추천 학습: " + tip.recommended_sections.join(", ")));
  }
  return d;
}

// 7~10점: 심화 질문의 출제 의도 (질문 자체는 다음 질문 자리에 표시된다)
function advancedIntentBlock(adv) {
  const d = document.createElement("div");
  d.className = "coaching";
  d.innerHTML = `<span class="tag">심화 질문 출제</span>`;
  if (adv.intent) d.appendChild(el("p", "출제 의도: " + adv.intent));
  return d;
}

// LLM 생성 텍스트에 가끔 섞여 나오는 서식 군더더기를 제거한다.
// followup은 structured output이 아니라 자유 텍스트라, 프롬프트로 막아도
// 100% 보장되지 않으므로 표시 계층에서 한 번 더 방어한다.
function cleanText(text) {
  if (typeof text !== "string") return text;
  return text
    .replace(/\*\*/g, "")                 // 볼드 마크다운(**)
    .replace(/^#+\s*/gm, "")              // 헤더(#)
    .replace(/\[?꼬리\s*질문\]?\s*[:：]?/g, "")  // "[꼬리 질문]" 같은 라벨
    .replace(/^["'“”]|["'“”]$/g, "")      // 양끝 따옴표
    .trim();
}

// 작은 헬퍼들
function el(tag, text) {
  const e = document.createElement(tag);
  e.textContent = cleanText(text);
  return e;
}
function list(items) {
  const ul = document.createElement("ul");
  items.forEach((it) => ul.appendChild(el("li", it)));
  return ul;
}
