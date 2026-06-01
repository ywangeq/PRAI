from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class QuestionInput:
    id: str
    label: str
    answer: str
    keywords: list[str]


class StudyCheckEvaluator:
    def __init__(self) -> None:
        self.cli_command = os.environ.get("CODEX_STUDY_CHECK_CMD", "").strip()

    @property
    def provider_name(self) -> str:
        return "cli-provider" if self.cli_command else "backend-heuristic"

    def evaluate(self, payload: dict) -> dict:
        if self.cli_command:
            return self._evaluate_with_cli(payload)
        return self._evaluate_with_heuristic(payload)

    def _evaluate_with_cli(self, payload: dict) -> dict:
        proc = subprocess.run(
            self.cli_command,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            shell=True,
            check=True,
        )
        result = json.loads(proc.stdout)
        result.setdefault("source", "cli-provider")
        result.setdefault("updatedAt", self._now())
        return result

    def _evaluate_with_heuristic(self, payload: dict) -> dict:
        questions = [
            QuestionInput(
                id=item.get("id", ""),
                label=item.get("label", "未命名问题"),
                answer=item.get("answer", ""),
                keywords=item.get("keywords", []),
            )
            for item in payload.get("questions", [])
        ]

        details = [self._evaluate_question(item) for item in questions]
        score = round(sum(item["score"] for item in details) / max(len(details), 1))
        passed = all(item["pass"] for item in details) and score >= 70
        overall_feedback = self._build_overall_feedback(details, score, passed)

        return {
            "paperId": payload.get("paperId"),
            "answers": {item.id: item.answer for item in questions},
            "details": details,
            "score": score,
            "pass": passed,
            "overallFeedback": overall_feedback,
            "source": "backend-heuristic",
            "updatedAt": self._now(),
        }

    def _evaluate_question(self, question: QuestionInput) -> dict:
        text = question.answer.strip()
        normalized_keywords = self._unique_keywords(question.keywords)
        lowered = text.lower()
        matched = [keyword for keyword in normalized_keywords if keyword in lowered]
        missing = [keyword for keyword in normalized_keywords if keyword not in matched]

        if not text:
            score = 0
            reasons = [f"{question.label} 还是空的，所以系统没法确认你是否真的理解了。"]
            hints = ["先用自己的话写满 2 到 4 句话，再回来提交。"]
        else:
            length_score = min(1, len(text) / 180) * 70
            keyword_score = (len(matched) / max(len(normalized_keywords), 1)) * 30 if normalized_keywords else min(30, len(text) / 8)
            score = round(length_score + keyword_score)
            reasons, hints = self._diagnose(question.label, text, normalized_keywords, matched, missing)

        passed = len(text) >= 60 and score >= 55
        return {
            "id": question.id,
            "label": question.label,
            "answer": question.answer,
            "keywords": normalized_keywords,
            "keywordHits": len(matched),
            "pass": passed,
            "score": score,
            "feedback": {
                "matchedKeywords": matched,
                "missingKeywords": missing,
                "reasons": reasons,
                "hints": hints,
            },
        }

    def _diagnose(self, label: str, text: str, keywords: list[str], matched: list[str], missing: list[str]) -> tuple[list[str], list[str]]:
        reasons: list[str] = []
        hints: list[str] = []
        length = len(text)

        if length < 60:
            reasons.append(f"{label} 写得太短，更像提词，还没有形成完整解释。")
            hints.append("先补到至少 60 字，最好说清楚“为什么”和“怎么做”。")
        elif length < 110:
            reasons.append(f"{label} 有基本回答，但解释还偏薄，支撑细节不够。")
            hints.append("再补一层因果，比如“原方法哪里不够”或“这个模块为什么有效”。")

        if keywords and not matched:
            reasons.append(f"{label} 里几乎没有提到关键概念，所以系统判断你可能还没抓住这篇论文的主干。")
            hints.append(f"试着把这些关键词串进解释里：{' / '.join(keywords[:3])}。")
        elif len(missing) >= 2:
            reasons.append(f"{label} 提到了一部分重点，但还漏掉了几个关键概念。")
            hints.append(f"可以补上这些词背后的意思：{' / '.join(missing[:3])}。")

        if not self._has_logic_connectors(text):
            reasons.append(f"{label} 更像列点，还没有把逻辑关系讲顺。")
            hints.append("试着用“因为…所以…”或“它通过…实现…”这样的句式。")

        if not reasons:
            reasons.append(f"{label} 基本讲清楚了，系统能看出你已经不是在机械复述。")
        if not hints:
            hints.append("继续保持这种“问题 - 方法 - 价值”的解释方式。")
        return reasons, hints

    def _build_overall_feedback(self, details: list[dict], score: int, passed: bool) -> dict:
        weakest = sorted(details, key=lambda item: item["score"])[:2]
        reasons: list[str] = []
        next_actions: list[str] = []

        if passed:
            reasons.append("这次通过了，说明你已经能把主问题、核心方法和路线价值讲成自己的话。")
        elif score < 50:
            reasons.append("整体分数偏低，说明目前更像是刚读过，还没有把问题、方法、价值连成自己的解释。")
        elif score < 70:
            reasons.append("你已经抓到一部分主线，但解释还不够稳，所以系统没有判定为真正理解通过。")
        else:
            reasons.append("总分不算差，但至少有一题还不够扎实，所以这次没有判定通过。")

        for item in weakest:
            if not item["pass"]:
                next_actions.append(f"优先重写“{item['label']}”，它现在是最明显的短板。")
            hints = item.get("feedback", {}).get("hints", [])
            if hints:
                next_actions.append(hints[0])

        return {
            "overallReasons": reasons,
            "nextActions": self._unique_keywords(next_actions)[:4],
        }

    def _has_logic_connectors(self, text: str) -> bool:
        markers = ("因为", "所以", "因此", "为了", "通过", "从而", "使得", "本质上", "意味着")
        return any(marker in text for marker in markers)

    def _unique_keywords(self, values: list[str]) -> list[str]:
        seen: list[str] = []
        for value in values:
          cleaned = (value or "").strip().lower()
          if cleaned and cleaned not in seen:
            seen.append(cleaned)
        return seen

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
