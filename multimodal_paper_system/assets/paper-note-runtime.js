(async function () {
  const params = new URLSearchParams(window.location.search);
  const paperId = params.get("paperId");
  const content = document.getElementById("runtimeContent");
  const header = document.getElementById("noteHeader");
  const meta = header?.querySelector(".meta");

  function loadStudyScript() {
    const script = document.createElement("script");
    script.src = "../assets/paper-study-check.js";
    document.body.appendChild(script);
  }

  if (!paperId) {
    if (content) {
      content.innerHTML = "<section><h2>缺少 paperId</h2><p>请从图谱页面进入这篇初始化笔记。</p></section>";
    }
    return;
  }

  try {
    const res = await fetch("../data/papers.json");
    if (!res.ok) throw new Error("无法读取 papers.json");
    const papers = await res.json();
    const paper = papers.find(item => item.id === paperId);
    if (!paper) throw new Error("没有找到对应论文");

    document.body.setAttribute("data-paper-id", paper.id);
    document.title = `${paper.title} 初始化笔记`;

    const h1 = header?.querySelector("h1");
    const subtitle = header?.querySelector(".subtitle");
    if (h1) h1.textContent = `${paper.title}: ${paper.fullTitle || paper.title}`;
    if (subtitle) {
      subtitle.textContent = "这是一张初始化阅读卡片。先带着问题过一遍论文，再在读完时填写理解检查。只有通过检查，图谱里才会算作真正完成。";
    }
    if (meta) {
      meta.innerHTML = [
        `<span class="pill">方向：${paper.area}</span>`,
        `<span class="pill">年份：${paper.year}</span>`,
        ...paper.keywords.map(keyword => `<span class="pill">关键词：${keyword}</span>`)
      ].join("");
    }

    const questionKeywords = {
      problem: [paper.title.toLowerCase(), ...paper.keywords.slice(0, 2).map(item => item.toLowerCase())],
      method: paper.keywords.map(item => item.toLowerCase()),
      meaning: [paper.area.toLowerCase(), ...paper.title.toLowerCase().split(/\s+/).slice(0, 3)]
    };

    content.innerHTML = `
      <section id="snapshot">
        <h2>1. 开始前先抓什么</h2>
        <p class="lead">${paper.coreQuestion}</p>
        <div class="callout">
          <strong>先别急着啃实验表：</strong>
          <p>第一遍只要回答三个问题就够了：它到底在解决什么问题？它用了什么结构或训练机制？它为什么会进入这条技术路线？</p>
        </div>
        <div class="grid">
          <div class="mini">
            <strong>主问题</strong>
            ${paper.coreQuestion}
          </div>
          <div class="mini">
            <strong>一句话贡献</strong>
            ${paper.contribution}
          </div>
          <div class="mini">
            <strong>建议重点</strong>
            Abstract、Introduction、Method、Conclusion 先过一遍，再回头看关键图和训练目标。
          </div>
          <div class="mini">
            <strong>这一轮目标</strong>
            先形成自己的解释，不追求一上来就把每个实验数字记住。
          </div>
        </div>
      </section>

      <section id="questions">
        <h2>2. 阅读时保留的问题</h2>
        <ul class="checklist">
          <li>这篇论文具体在修补上一代方法的哪一个短板？</li>
          <li>它的核心结构或训练目标，和关键词 <strong>${paper.keywords.join(" / ")}</strong> 是怎么对应上的？</li>
          <li>如果把它删掉，这条路线后面的论文会缺哪一块能力？</li>
        </ul>
        <div class="callout warn">
          <strong>理解要求：</strong>
          <p>完成阅读时，至少要能用自己的话把“问题 - 方法 - 价值”讲清楚。只勾选完成、不回答问题，不会计入掌握度。</p>
        </div>
      </section>

      <section id="relation">
        <h2>3. 和路线图的关系</h2>
        <p>这篇论文属于 <strong>${paper.area}</strong>。读的时候特别留意：它是在打基础、做能力扩展、还是在优化训练/对齐范式。后面我们会把你的得分累计到这个方向的掌握度仪表盘里。</p>
        <p>你可以在图谱页里继续看它和前后论文的边，帮助自己判断“这篇 paper 在链路里到底扮演什么角色”。</p>
      </section>

      <section id="check">
        <h2>4. 理解检查</h2>
        <p>读完以后，再填写下面的问题并提交检查。系统会根据回答完整度、关键词覆盖和解释逻辑给出通过/未通过结果、分数，以及为什么分低和下一步怎么补。</p>

        <form class="study-check" data-study-check>
          <div class="study-check-grid">
            <article class="study-card">
              <h3>问题 1：它到底在解决什么问题？</h3>
              <p>别只抄标题，尽量写出它想补哪一个缺口，为什么原来的办法不够。</p>
              <textarea data-question-id="problem" data-keywords="${questionKeywords.problem.join(",")}" placeholder="用你自己的话写：这篇论文在解决什么问题，原来的方法哪里不够。"></textarea>
            </article>

            <article class="study-card">
              <h3>问题 2：核心方法或训练机制是什么？</h3>
              <p>写出最关键的模块、训练目标或数据组织方式，不需要面面俱到，但要抓住主干。</p>
              <textarea data-question-id="method" data-keywords="${questionKeywords.method.join(",")}" placeholder="描述它的核心结构、训练目标或关键机制。"></textarea>
            </article>

            <article class="study-card">
              <h3>问题 3：为什么它重要？和后续路线有什么关系？</h3>
              <p>尽量联系这个方向里前后的论文，说明它的价值。</p>
              <textarea data-question-id="meaning" data-keywords="${questionKeywords.meaning.join(",")}" placeholder="说明它的重要性，以及它和这条技术路线的关系。"></textarea>
            </article>
          </div>

          <div class="study-toolbar">
            <button class="study-button" type="button" data-save-study>先保存草稿</button>
            <button class="study-button primary" type="button" data-submit-study>提交理解检查</button>
          </div>
          <div data-study-result></div>
        </form>
      </section>
    `;
    loadStudyScript();
  } catch (error) {
    if (content) {
      content.innerHTML = `<section><h2>初始化失败</h2><p>${error.message}</p></section>`;
    }
  }
})();
