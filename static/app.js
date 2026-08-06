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
let pendingOutOfScope = false;  // 직전 턴이 근거 부족으로 보류됐는가 (Phase 17)
// 끝난 뒤 요약을 만들려고 턴을 그대로 모아둔다. 서버의 history에는 마지막 턴이 없다.
// await_answer가 다음 턴을 기다리며 직전 턴을 기록하는 구조라, 마지막 턴은 거기 도달하지 못한다
let sessionTurns = [];

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
  // 다만 근거가 없어 보류된 상태는 예외다. 그때는 채점 자체가 없었고
  // 다른 질문으로 이어가는 것이 정해진 흐름이다 (Phase 17).
  //
  // 여기서 경고 문구를 띄우지 않는 이유: 목록을 잠근 모습(.locked)이 이미 보이고,
  // 끝내려면 "면접 종료" 버튼이라는 분명한 출구가 있다. 화면 맨 아래에 뜨는 문구는
  // 클릭한 지점에서 멀어 눈에 띄지도 않았다.
  if (sessionId && !pendingOutOfScope) return;
  currentQuestion = question;
  document.querySelectorAll(".question-list li").forEach((el) => el.classList.remove("selected"));
  li.classList.add("selected");

  $("interview-hint").textContent = pendingOutOfScope
    ? "이 질문으로 면접을 이어갑니다."
    : "아래 질문에 답하면 면접이 시작됩니다. 최대 3턴까지 이어집니다.";
  showCurrentQuestion(question, pendingOutOfScope ? "다음 질문" : "첫 질문");
  setStatus($("interview-status"), "", "");
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
    // 보류된 세션을 이어갈 때는 재개할 지점이 없어 새 질문을 함께 보내야 한다
    const data = sessionId
      ? await postJSON("/interview/answer", {
          session_id: sessionId,
          answer,
          ...(pendingOutOfScope ? { question: answeredQuestion } : {}),
        })
      : await postJSON("/interview/start", { question: answeredQuestion, answer });

    sessionId = data.session_id;
    pendingOutOfScope = data.status === "out_of_scope";
    appendTurn(data, answeredQuestion, answer);
    sessionTurns.push({
      turn: data.turn,
      question: answeredQuestion,
      answer,
      evaluation: data.evaluation,
      outOfScope: data.status === "out_of_scope",
    });
    lockQuestionList(true);

    if (data.status === "out_of_scope") {
      askScopeChoice(data);
    } else if (data.status === "awaiting_answer") {
      currentQuestion = data.next_question;
      showCurrentQuestion(data.next_question, `턴 ${data.turn + 1} 질문`);
      $("answer-input").value = "";
      $("submit-btn").textContent = "답변 제출";
      $("end-session-btn").hidden = false;   // 남은 턴을 채우지 않고 나갈 출구
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
  // 범위 밖 턴은 채점을 보류했으므로 면접 턴으로 세지 않는다
  no.textContent = data.status === "out_of_scope" ? "평가 보류" : `턴 ${data.turn}`;
  head.appendChild(no);
  if (data.evaluation) head.appendChild(scoreBadges(data.evaluation));
  turn.appendChild(head);

  turn.appendChild(bubble("질문", question, "q"));
  turn.appendChild(bubble("내 답변", answer, "a"));

  const result = document.createElement("div");
  result.className = "turn-result";

  // 고정 지식에 근거가 없으면 점수가 아예 없다. 틀린 문서로 매긴 점수를
  // 보여주느니 왜 보류했는지 알리고 다음 선택지를 준다
  if (!data.evaluation) {
    const notice = el("p", data.out_of_scope_message || "평가를 보류했습니다.");
    notice.className = "scope-notice";
    result.appendChild(notice);
    if (data.retrieved_sources?.length) {
      const s = el("p", "가장 가까운 자료: " + data.retrieved_sources.join(", ") + " (근거로 쓰기에는 멉니다)");
      s.className = "sources";
      result.appendChild(s);
    }
    turn.appendChild(result);
    $("timeline").appendChild(turn);
    return;
  }

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

// 세션이 도는 동안 질문 목록을 잠근다. 클릭이 막힌 이유를 문구로 설명하는 대신
// 목록 자체를 눌리지 않게 보여준다
function lockQuestionList(locked) {
  $("question-list").classList.toggle("locked", locked && !pendingOutOfScope);
}

// 남은 턴을 채우지 않고 중간에 끝낸다. 되돌릴 수 없으므로 한 번 확인받는다
$("end-session-btn").addEventListener("click", () => {
  const remaining = $("turn-badge").textContent;
  if (!confirm(`진행 중인 면접이 있습니다 (${remaining}).\n지금 종료하면 남은 턴은 진행되지 않습니다. 끝낼까요?`)) return;
  finishSession({ end_reason: "ended_by_user", max_turns: 0 });
});

// 근거가 없어 보류했을 때 다음 행동을 사용자가 고르게 한다.
// 자동으로 끝내지 않는 이유: 질문 하나가 KB 밖이었을 뿐 면접이 끝난 것은 아니다
function askScopeChoice(data) {
  $("current-question").hidden = true;
  $("answer-area").hidden = true;
  setStatus($("interview-status"), "", "");
  $("scope-message").textContent = data.out_of_scope_message || "평가를 보류했습니다.";
  $("scope-choice").hidden = false;
}

$("scope-continue-btn").addEventListener("click", () => {
  $("scope-choice").hidden = true;
  $("answer-area").hidden = false;
  $("answer-input").value = "";
  currentQuestion = null;
  lockQuestionList(false);   // 보류 상태에서는 다시 고를 수 있어야 한다
  document.querySelectorAll(".question-list li").forEach((el) => el.classList.remove("selected"));
  setStatus($("interview-status"), "위에서 다른 질문을 골라주세요.", "");
  $("step-questions").scrollIntoView({ behavior: "smooth", block: "center" });
});

$("scope-end-btn").addEventListener("click", () => {
  $("scope-choice").hidden = true;
  finishSession({ end_reason: "out_of_scope_ended", max_turns: 0 });
});

function finishSession(data) {
  $("current-question").hidden = true;
  $("answer-area").hidden = true;
  setStatus($("interview-status"), "", "");

  const reasons = {
    max_turns_reached: `${data.max_turns}턴을 모두 진행했습니다. 수고하셨습니다.`,
    fundamentals_no_followup: "기초 개념 설명으로 마무리했습니다. 개념을 익힌 뒤 다시 도전해보세요.",
    out_of_scope_ended: "고정 지식에 근거가 없는 주제라 평가를 보류하고 종료했습니다.",
    completed: "면접이 종료되었습니다.",
  };
  const reasonsWithUser = {
    ...reasons,
    ended_by_user: "면접을 중간에 종료했습니다.",
  };
  $("end-message").textContent = reasonsWithUser[data.end_reason] || reasons.completed;
  $("session-end").hidden = false;
  $("end-session-btn").hidden = true;
  showSummary();
}

// ---- 종료 후 요약 ----
// 타임라인은 세로로 길어 전체 흐름이 한눈에 안 들어온다.
// 끝난 시점에 질문·답변·점수를 한 화면으로 묶어 되짚게 한다
function showSummary() {
  const graded = sessionTurns.filter((t) => t.evaluation);
  const body = $("summary-body");
  body.innerHTML = "";

  if (!sessionTurns.length) {
    body.appendChild(el("p", "진행된 턴이 없습니다."));
  } else {
    body.appendChild(summaryOverview(graded));
    // 채점된 턴이 둘 이상일 때만 흐름이 의미를 갖는다
    if (graded.length > 1) body.appendChild(summaryTrend(graded));
    sessionTurns.forEach((t) => body.appendChild(summaryTurn(t)));
  }

  $("summary-modal").hidden = false;
  // 모달이 떠 있는 동안 뒤 페이지가 같이 스크롤되면 어디를 보고 있는지 놓친다
  document.body.classList.add("modal-open");
  $("summary-close").focus();
}

// 채점된 턴만 평균에 넣는다. 보류된 턴에는 점수가 없다
function summaryOverview(graded) {
  const box = document.createElement("div");
  box.className = "summary-overview";

  if (!graded.length) {
    box.appendChild(el("p", "채점된 턴이 없어 평균을 낼 수 없습니다."));
    return box;
  }

  const avg = (key) =>
    (graded.reduce((sum, t) => sum + t.evaluation[key], 0) / graded.length).toFixed(1);
  const tech = avg("technical_score");
  const comp = avg("completeness_score");

  box.innerHTML = `
    <div class="summary-stat"><span class="summary-stat-label">채점된 턴</span><strong>${graded.length}</strong></div>
    <div class="summary-stat"><span class="summary-stat-label">기술 평균</span><strong class="${scoreClass(Math.round(tech))}">${tech}</strong></div>
    <div class="summary-stat"><span class="summary-stat-label">완성도 평균</span><strong class="${scoreClass(Math.round(comp))}">${comp}</strong></div>
  `;
  return box;
}

// 턴별 점수를 한 줄로 늘어놓는다. 요약에서 가장 알고 싶은 것은 개별 점수가 아니라
// "어느 턴에서 흔들렸고 회복했는가"인데, 상세 블록만 쌓으면 스크롤하며 기억해야 한다.
// 탭이나 화살표로 한 턴씩 보여주는 방식을 쓰지 않은 이유도 같다. 비교가 사라진다.
//
// 보류된 턴은 여기 넣지 않는다. 점수가 없어 흐름에 보탤 것이 없는데 자리만 차지하고,
// 특히 첫 턴이 보류면 실제 1턴이 왼쪽에서 밀려난다. 상세 목록에는 그대로 남는다
function summaryTrend(graded) {
  const section = document.createElement("div");
  const caption = el("p", "턴별 기술 / 완성도");
  caption.className = "summary-trend-caption";
  section.appendChild(caption);

  const wrap = document.createElement("div");
  wrap.className = "summary-trend";

  graded.forEach((t, i) => {
    if (i > 0) {
      const sep = el("span", "›");
      sep.className = "summary-trend-sep";
      wrap.appendChild(sep);
    }
    const item = document.createElement("div");
    item.className = "summary-trend-item";
    const label = el("span", `턴 ${t.turn}`);
    label.className = "summary-trend-label";
    item.appendChild(label);

    const score = el("span", `${t.evaluation.technical_score} / ${t.evaluation.completeness_score}`);
    score.className = "summary-trend-score " + scoreClass(t.evaluation.technical_score);
    item.appendChild(score);
    wrap.appendChild(item);
  });

  section.appendChild(wrap);
  return section;
}

function summaryTurn(t) {
  const row = document.createElement("div");
  row.className = "summary-turn";

  const head = document.createElement("div");
  head.className = "summary-turn-head";
  const no = el("span", t.outOfScope ? "평가 보류" : `턴 ${t.turn}`);
  no.className = "turn-no";
  head.appendChild(no);
  if (t.evaluation) head.appendChild(scoreBadges(t.evaluation));
  row.appendChild(head);

  row.appendChild(summaryField("질문", t.question));
  row.appendChild(summaryField("내 답변", t.answer));
  if (t.evaluation?.overall_feedback) {
    row.appendChild(summaryField("총평", cleanText(t.evaluation.overall_feedback)));
  }
  if (t.evaluation?.improvements?.length) {
    const wrap = document.createElement("div");
    wrap.className = "summary-field";
    wrap.appendChild(el("span", "개선점"));
    wrap.appendChild(list(t.evaluation.improvements));
    row.appendChild(wrap);
  }
  return row;
}

function summaryField(label, text) {
  const wrap = document.createElement("div");
  wrap.className = "summary-field";
  wrap.appendChild(el("span", label));
  wrap.appendChild(el("p", text));
  return wrap;
}

function closeSummary() {
  $("summary-modal").hidden = true;
  document.body.classList.remove("modal-open");
}

$("summary-close").addEventListener("click", closeSummary);
$("summary-close-btn").addEventListener("click", closeSummary);
$("summary-btn").addEventListener("click", showSummary);
$("summary-modal").addEventListener("click", (e) => {
  if (e.target === $("summary-modal")) closeSummary();   // 바깥을 누르면 닫는다
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("summary-modal").hidden) closeSummary();
});
$("summary-restart-btn").addEventListener("click", () => {
  closeSummary();
  $("restart-btn").click();
});

$("restart-btn").addEventListener("click", () => {
  sessionId = null;
  currentQuestion = null;
  pendingOutOfScope = false;
  sessionTurns = [];
  lockQuestionList(false);
  $("timeline").innerHTML = "";
  $("answer-input").value = "";
  $("answer-area").hidden = false;
  $("end-session-btn").hidden = true;
  $("scope-choice").hidden = true;
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
