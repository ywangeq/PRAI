(function () {
  const root = document.querySelector("[data-paper-id]");
  const form = document.querySelector("[data-study-check]");
  if (!root || !form) return;

  const paperId = root.getAttribute("data-paper-id");
  const storageKey = `paper-study-check:${paperId}`;
  const currentPaperKey = "multimodal_paper_graph_current_note";
  const backendEndpoint = "http://localhost:8130/api/study-check";
  const resultBox = form.querySelector("[data-study-result]");
  const textareas = [...form.querySelectorAll("textarea[data-question-id]")];

  localStorage.setItem(currentPaperKey, paperId);

  const defaultQuestions = [
    {
      id: "problem",
      label: "论文到底在解决什么问题",
      keywords: []
    },
    {
      id: "method",
      label: "核心方法或训练机制是什么",
      keywords: []
    },
    {
      id: "meaning",
      label: "为什么这篇论文重要，和后续路线有什么关系",
      keywords: []
    }
  ];

  function readState() {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || "{}");
    } catch {
      return {};
    }
  }

  function writeState(next) {
    localStorage.setItem(storageKey, JSON.stringify(next));
  }

  function getKeywords(textarea) {
    const raw = textarea.getAttribute("data-keywords") || "";
    return raw.split(",").map(item => item.trim().toLowerCase()).filter(Boolean);
  }

  function uniqueKeywords(keywords) {
    return [...new Set((keywords || []).filter(Boolean))];
  }

  function scoreAnswer(answer, keywords) {
    const text = answer.trim();
    if (!text) return { score: 0, keywordHits: 0 };
    const lengthScore = Math.min(1, text.length / 180) * 70;
    const hitCount = keywords.filter(keyword => text.toLowerCase().includes(keyword)).length;
    const keywordScore = keywords.length ? (hitCount / keywords.length) * 30 : Math.min(30, text.length / 8);
    return {
      score: Math.round(lengthScore + keywordScore),
      keywordHits: hitCount
    };
  }

  function diagnoseAnswer(answer, keywords, questionLabel) {
    const text = answer.trim();
    const normalizedKeywords = uniqueKeywords(keywords);
    const matchedKeywords = normalizedKeywords.filter(keyword => text.toLowerCase().includes(keyword));
    const missingKeywords = normalizedKeywords.filter(keyword => !matchedKeywords.includes(keyword));
    const length = text.length;
    const reasons = [];
    const hints = [];

    if (!text) {
      reasons.push(`${questionLabel} 还是空的，所以系统没法判断你是否真的理解了。`);
      hints.push("先用自己的话写满 2 到 4 句话，不要只留标题或关键词。");
    } else {
      if (length < 60) {
        reasons.push(`${questionLabel} 写得太短，更像提词，不像完整解释。`);
        hints.push("先补到至少 60 字，最好把“为什么”和“怎么做”都说出来。");
      } else if (length < 110) {
        reasons.push(`${questionLabel} 有基本回答，但解释还偏薄，细节支撑不够。`);
        hints.push("再补一层因果，比如“原方法哪里不够”或“这个模块为什么有效”。");
      }

      if (normalizedKeywords.length && matchedKeywords.length === 0) {
        reasons.push(`${questionLabel} 里几乎没有提到这篇论文的关键概念，所以系统判断你可能还没抓住主干。`);
        hints.push(`试着把这些关键词串进解释里：${normalizedKeywords.slice(0, 3).join(" / ")}。`);
      } else if (missingKeywords.length >= 2) {
        reasons.push(`${questionLabel} 提到了一部分重点，但还漏掉了几个关键概念。`);
        hints.push(`可以补上这些词背后的意思：${missingKeywords.slice(0, 3).join(" / ")}。`);
      }

      const hasConnector = /因为|所以|因此|为了|通过|从而|使得|本质上|意味着/.test(text);
      if (!hasConnector) {
        reasons.push(`${questionLabel} 更像列要点，还没有把逻辑关系说顺。`);
        hints.push("试着加上“因为…所以…”或“它通过…实现…”这样的句式。");
      }
    }

    if (!reasons.length) {
      reasons.push(`${questionLabel} 基本讲清楚了，系统能看出你已经不是在机械复述。`);
    }

    if (!hints.length) {
      hints.push("继续保持这种“问题 - 方法 - 价值”的解释方式，已经比较像真正理解后的表达了。");
    }

    return {
      matchedKeywords,
      missingKeywords,
      reasons,
      hints
    };
  }

  function buildOverallFeedback(details, overallScore, pass) {
    const weakest = [...details].sort((a, b) => a.score - b.score).slice(0, 2);
    const overallReasons = [];
    const nextActions = [];

    if (!pass) {
      if (overallScore < 50) {
        overallReasons.push("整体分数偏低，说明目前更像是刚读过，还没有把问题、方法、价值连成自己的解释。");
      } else if (overallScore < 70) {
        overallReasons.push("你已经抓到了一部分主线，但解释还不够稳，所以系统没有判定为真正理解通过。");
      } else {
        overallReasons.push("总分不算差，但至少有一题没有达到通过线，所以系统认为理解还不够均衡。");
      }
    } else {
      overallReasons.push("这次通过了，说明你已经能把主问题、核心方法和路线价值讲成一套自己的话。");
    }

    weakest.forEach(item => {
      const label = item.label || item.id;
      if (!item.pass) {
        nextActions.push(`优先重写“${label}”这一题，它现在是最明显的短板。`);
      }
      if (item.feedback?.hints?.length) {
        nextActions.push(item.feedback.hints[0]);
      }
    });

    return {
      overallReasons,
      nextActions: uniqueKeywords(nextActions).slice(0, 4)
    };
  }

  function evaluate() {
    const details = textareas.map((textarea, index) => {
      const answer = textarea.value || "";
      const keywords = getKeywords(textarea);
      const scored = scoreAnswer(answer, keywords);
      const minLengthPass = answer.trim().length >= 60;
      const pass = minLengthPass && scored.score >= 55;
      const label = textarea.closest(".study-card")?.querySelector("h3")?.textContent?.trim()
        || defaultQuestions[index]?.label
        || `问题 ${index + 1}`;
      const feedback = diagnoseAnswer(answer, keywords, label);
      return {
        id: textarea.getAttribute("data-question-id") || defaultQuestions[index]?.id || `q${index}`,
        label,
        answer,
        keywords,
        keywordHits: scored.keywordHits,
        pass,
        score: scored.score,
        feedback
      };
    });

    const total = details.length || 1;
    const rawScore = details.reduce((sum, item) => sum + item.score, 0) / total;
    const allPassed = details.every(item => item.pass);
    const overallScore = Math.round(rawScore);
    const overallFeedback = buildOverallFeedback(details, overallScore, allPassed && overallScore >= 70);
    return {
      paperId,
      answers: Object.fromEntries(details.map(item => [item.id, item.answer])),
      details,
      score: overallScore,
      pass: allPassed && overallScore >= 70,
      overallFeedback,
      updatedAt: new Date().toISOString()
    };
  }

  function buildPayload() {
    return {
      paperId,
      questions: textareas.map((textarea, index) => ({
        id: textarea.getAttribute("data-question-id") || defaultQuestions[index]?.id || `q${index}`,
        label: textarea.closest(".study-card")?.querySelector("h3")?.textContent?.trim()
          || defaultQuestions[index]?.label
          || `问题 ${index + 1}`,
        answer: textarea.value || "",
        keywords: getKeywords(textarea)
      }))
    };
  }

  async function evaluateWithBackend() {
    const response = await fetch(backendEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(buildPayload())
    });
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    const payload = await response.json();
    return {
      ...payload,
      paperId,
      updatedAt: payload.updatedAt || new Date().toISOString()
    };
  }

  function renderDetailFeedback(state) {
    if (!state?.details?.length) return "";

    const overall = state.overallFeedback || { overallReasons: [], nextActions: [] };
    return `
      <div class="study-diagnostics">
        <div class="study-panel">
          <h4>系统判断</h4>
          <ul>
            ${overall.overallReasons.map(item => `<li>${item}</li>`).join("")}
          </ul>
        </div>
        <div class="study-panel">
          <h4>下一步建议</h4>
          <ul>
            ${overall.nextActions.map(item => `<li>${item}</li>`).join("")}
          </ul>
        </div>
        ${state.details.map(item => `
          <article class="study-breakdown ${item.pass ? "pass" : "fail"}">
            <div class="study-breakdown-head">
              <strong>${item.label}</strong>
              <span class="study-pill ${item.pass ? "pass" : "fail"}">${item.score} / 100</span>
            </div>
            <p class="study-breakdown-summary">${item.feedback.reasons[0]}</p>
            <ul class="study-breakdown-list">
              ${item.feedback.reasons.slice(1, 3).map(reason => `<li>${reason}</li>`).join("")}
            </ul>
            <p class="study-breakdown-hint"><strong>提示：</strong>${item.feedback.hints[0] || ""}</p>
          </article>
        `).join("")}
      </div>
    `;
  }

  function renderResult(state) {
    if (!resultBox) return;
    if (!state || !state.updatedAt) {
      resultBox.innerHTML = '<span class="study-note">先回答问题并保存，读完后再提交检查。</span>';
      return;
    }

    const date = state.updatedAt.slice(0, 10);
    const pillClass = state.pass ? "pass" : "fail";
    const pillText = state.pass ? "通过" : "未通过";
    const sourceText = state.source === "cli-provider"
      ? "来源：后台 CLI 点评"
      : state.source === "backend-heuristic"
        ? "来源：本地后端规则点评"
        : "来源：页面本地规则点评";
    resultBox.innerHTML = `
      <div class="study-status">
        <span class="study-pill ${pillClass}">理解检查 ${pillText}</span>
        <span class="study-pill">${state.score} / 100</span>
        <span class="study-note">最近更新：${date}</span>
        <span class="study-note">${sourceText}</span>
      </div>
      ${renderDetailFeedback(state)}
    `;
  }

  function hydrate() {
    const saved = readState();
    if (saved.answers) {
      textareas.forEach(textarea => {
        const id = textarea.getAttribute("data-question-id");
        textarea.value = saved.answers[id] || "";
      });
    }
    renderResult(saved);
  }

  form.querySelector("[data-save-study]")?.addEventListener("click", () => {
    const next = {
      ...readState(),
      paperId,
      answers: Object.fromEntries(textareas.map(textarea => [
        textarea.getAttribute("data-question-id"),
        textarea.value || ""
      ])),
      updatedAt: new Date().toISOString()
    };
    writeState(next);
    renderResult(next);
  });

  form.querySelector("[data-submit-study]")?.addEventListener("click", async () => {
    let evaluated;
    try {
      evaluated = await evaluateWithBackend();
    } catch {
      evaluated = {
        ...evaluate(),
        source: "frontend-heuristic"
      };
    }
    writeState(evaluated);
    renderResult(evaluated);
  });

  hydrate();
})();
