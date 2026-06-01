from __future__ import annotations

import json
import re
from pathlib import Path


AREA_RELATION_HINTS = {
    "VLM Foundations": ("foundation", "builds the representation base for later VLM work"),
    "Visual Instruction Tuning": ("enables", "turns visual features into instruction-following behavior"),
    "PEFT": ("implementation_support", "can be used as an efficient adaptation recipe"),
    "Preference Alignment": ("alignment_pipeline", "extends the alignment and preference optimization pipeline"),
    "Multimodal Alignment": ("extends", "broadens alignment beyond image-text pairs"),
}


class PaperBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.data_dir = root / "data"
        self.notes_dir = root / "notes"
        self.template_path = self.notes_dir / "_paper_note_template.html"

    def analyze(self, payload: dict) -> dict:
        papers = self._load_json(self.data_dir / "papers.json")
        relations = self._load_json(self.data_dir / "relations.json")

        title = (payload.get("title") or "").strip()
        full_title = (payload.get("fullTitle") or title).strip()
        year = int(payload.get("year") or 0)
        area = (payload.get("area") or "VLM Foundations").strip()
        keywords = self._normalize_keywords(payload.get("keywords", []))
        core_question = (payload.get("coreQuestion") or "").strip()
        contribution = (payload.get("contribution") or "").strip()
        pdf = (payload.get("pdf") or "").strip()
        folder = (payload.get("folder") or "").strip()

        paper_id = payload.get("id") or self._build_paper_id(title, year)
        note_filename = f"{paper_id}.html"
        note_path = f"notes/{note_filename}"
        order = max((item.get("order", 0) for item in papers), default=0) + 1

        paper_record = {
            "id": paper_id,
            "title": title,
            "fullTitle": full_title,
            "year": year,
            "area": area,
            "folder": folder,
            "keywords": keywords,
            "coreQuestion": core_question,
            "contribution": contribution,
            "pdf": pdf,
            "note": note_path,
            "status": "todo",
            "order": order,
        }

        refined_questions = self._build_refined_questions(paper_record)
        suggested_relations = self._suggest_relations(paper_record, papers, relations)
        note_html = self._render_note(paper_record, refined_questions, suggested_relations)

        return {
            "paper": paper_record,
            "refinedQuestions": refined_questions,
            "suggestedRelations": suggested_relations,
            "notePath": note_path,
            "notePreview": note_html,
        }

    def apply(self, payload: dict) -> dict:
        analysis = self.analyze(payload)
        paper = analysis["paper"]
        relations = analysis["suggestedRelations"]

        papers_path = self.data_dir / "papers.json"
        relations_path = self.data_dir / "relations.json"
        papers = self._load_json(papers_path)
        all_relations = self._load_json(relations_path)

        if any(item.get("id") == paper["id"] for item in papers):
            raise ValueError(f"Paper id already exists: {paper['id']}")

        papers.append(paper)
        all_relations.extend(relations)

        self._write_json(papers_path, papers)
        self._write_json(relations_path, all_relations)
        (self.notes_dir / f"{paper['id']}.html").write_text(analysis["notePreview"], encoding="utf-8")

        return {
            "ok": True,
            "paper": paper,
            "notePath": analysis["notePath"],
            "relationsAdded": len(relations),
        }

    def _build_paper_id(self, title: str, year: int) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        slug = re.sub(r"_+", "_", slug)
        return f"{slug}_{year}" if year else slug

    def _normalize_keywords(self, raw: list[str] | str) -> list[str]:
        if isinstance(raw, str):
            items = [item.strip() for item in raw.split(",")]
        else:
            items = [str(item).strip() for item in raw]
        return [item for item in items if item]

    def _build_refined_questions(self, paper: dict) -> list[dict]:
        keywords = paper["keywords"]
        first = keywords[0] if keywords else "核心方法"
        second = keywords[1] if len(keywords) > 1 else paper["area"]
        third = keywords[2] if len(keywords) > 2 else paper["title"]
        return [
            {
                "id": "problem",
                "title": "问题定义",
                "prompt": f"这篇论文到底在解决什么问题？它为什么值得单独做一篇 paper，而不是继续沿用上一代方案？读的时候尤其注意作者如何描述旧方法的缺口。",
                "keywords": [paper["title"].lower(), first.lower(), second.lower()],
            },
            {
                "id": "method",
                "title": "方法主干",
                "prompt": f"核心结构、训练目标或关键机制是什么？试着把 {first}、{second}、{third} 串成一条清晰的数据流或因果链。",
                "keywords": [item.lower() for item in keywords[:4]],
            },
            {
                "id": "meaning",
                "title": "路线价值",
                "prompt": f"它对后续路线的意义是什么？如果把这篇论文拿掉，{paper['area']} 这条线会缺哪一块能力或认知转折？",
                "keywords": [paper["area"].lower(), paper["title"].lower(), third.lower()],
            },
        ]

    def _suggest_relations(self, paper: dict, papers: list[dict], relations: list[dict]) -> list[dict]:
        same_area = [item for item in papers if item.get("area") == paper["area"]]
        suggestions: list[dict] = []

        if same_area:
            latest_same_area = sorted(same_area, key=lambda item: item.get("order", 0))[-1]
            rel_type, rel_label = AREA_RELATION_HINTS.get(paper["area"], ("extends", "extends the current line of work"))
            suggestions.append({
                "source": latest_same_area["id"],
                "target": paper["id"],
                "type": rel_type,
                "label": rel_label,
            })

        cross_area_source = self._cross_area_anchor(paper, papers)
        if cross_area_source:
            source_id, rel_type, label = cross_area_source
            if not any(item["source"] == source_id and item["target"] == paper["id"] for item in suggestions):
                suggestions.append({
                    "source": source_id,
                    "target": paper["id"],
                    "type": rel_type,
                    "label": label,
                })

        existing_pairs = {(item["source"], item["target"], item["type"]) for item in relations}
        return [item for item in suggestions if (item["source"], item["target"], item["type"]) not in existing_pairs]

    def _cross_area_anchor(self, paper: dict, papers: list[dict]) -> tuple[str, str, str] | None:
        area = paper["area"]
        if area == "Visual Instruction Tuning":
            anchor = next((item for item in papers if item["id"] == "blip2_2023"), None)
            if anchor:
                return (anchor["id"], "enables", "bridging vision features into instruction-tuned models")
        if area == "PEFT":
            anchor = next((item for item in papers if item["id"] == "llava_2023"), None)
            if anchor:
                return (anchor["id"], "implementation_support", "practical VLM adaptation can use this PEFT recipe")
        if area == "Preference Alignment":
            anchor = next((item for item in papers if item["id"] == "instructgpt_2022"), None)
            if anchor and paper["id"] != "instructgpt_2022":
                return (anchor["id"], "alternative", "compares or extends the main preference alignment pipeline")
        if area == "Multimodal Alignment":
            anchor = next((item for item in papers if item["id"] == "clip_2021"), None)
            if anchor:
                return (anchor["id"], "extends", "broadens representation alignment beyond the original image-text setup")
        return None

    def _render_note(self, paper: dict, questions: list[dict], relations: list[dict]) -> str:
        relation_lines = "".join(
            f"<li><strong>{item['type']}</strong>：{item['label']}</li>" for item in relations
        ) or "<li>待补充和现有图谱的关系。</li>"

        question_cards = "".join(
            f"""
              <div class="study-card">
                <h3>{index + 1}. {item['title']}</h3>
                <p>{item['prompt']}</p>
                <textarea data-question-id="{item['id']}" data-keywords="{','.join(item['keywords'])}"></textarea>
              </div>
            """
            for index, item in enumerate(questions)
        )

        keyword_pills = "".join(f'<span class="pill">关键词：{keyword}</span>' for keyword in paper["keywords"][:4])
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{paper['title']} 阅读笔记</title>
  <link rel="stylesheet" href="../assets/paper-note.css">
  <link rel="stylesheet" href="../assets/paper-study-check.css">
</head>
<body data-paper-id="{paper['id']}">
  <div class="page">
    <header>
      <p class="eyebrow">多模态论文阅读笔记</p>
      <h1>{paper['title']}: {paper['fullTitle']}</h1>
      <p class="subtitle">这是一份自动生成的初始笔记模板。先带着关键问题过一遍 paper，再逐步把问题、方法和路线关系写成自己的解释。</p>
      <div class="meta">
        <span class="pill">方向：{paper['area']}</span>
        <span class="pill">年份：{paper['year']}</span>
        {keyword_pills}
      </div>
    </header>

    <main>
      <nav aria-label="目录">
        <h2>阅读目录</h2>
        <a href="#summary">1. 一句话主结论</a>
        <a href="#problem">2. 问题背景</a>
        <a href="#method">3. 核心方法</a>
        <a href="#relation">4. 图谱关系</a>
        <a href="#questions">5. 关键阅读问题</a>
        <a href="#understanding-check">6. 理解检查</a>
      </nav>

      <div class="note-resizer" aria-hidden="true"></div>

      <div class="content">
        <section id="summary">
          <h2>1. 一句话主结论</h2>
          <p class="lead">{paper['contribution'] or '在这里补一句这篇论文最值得记住的结论。'}</p>
        </section>

        <section id="problem">
          <h2>2. 问题背景</h2>
          <p>{paper['coreQuestion'] or '在这里写这篇论文在解决什么问题，以及原方案的缺口。'}</p>
        </section>

        <section id="method">
          <h2>3. 核心方法</h2>
          <p>先写主结构、训练目标或关键机制，再回头补实验和细节。</p>
        </section>

        <section id="relation">
          <h2>4. 图谱关系</h2>
          <p>添加 paper 时，系统建议了这些关系，读完后可以再微调：</p>
          <ul>{relation_lines}</ul>
        </section>

        <section id="questions">
          <h2>5. 关键阅读问题</h2>
          <div class="grid">
            {''.join(f'<div class="mini"><strong>{item["title"]}</strong>{item["prompt"]}</div>' for item in questions)}
          </div>
        </section>

        <section id="understanding-check">
          <h2>6. 理解检查</h2>
          <div class="study-check" data-study-check>
            <div class="study-check-grid">
              {question_cards}
            </div>
            <div class="study-toolbar">
              <button class="study-button" type="button" data-save-study>保存草稿</button>
              <button class="study-button primary" type="button" data-submit-study>提交检查</button>
            </div>
            <div data-study-result></div>
          </div>
        </section>
      </div>
    </main>
  </div>
  <script src="../assets/paper-note-resize.js"></script>
  <script src="../assets/paper-study-check.js"></script>
</body>
</html>
"""

    def _load_json(self, path: Path) -> list[dict]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, data: list[dict]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
