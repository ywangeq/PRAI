#!/usr/bin/env python3
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from evaluator import StudyCheckEvaluator
from paper_builder import PaperBuilder


EVALUATOR = StudyCheckEvaluator()
PAPER_BUILDER = PaperBuilder(Path(__file__).resolve().parent.parent)


class StudyCheckHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self._send(200, {"ok": True, "provider": EVALUATOR.provider_name, "paperBuilder": True})
            return
        self._send(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/api/study-check", "/api/paper/analyze", "/api/paper/apply"}:
            self._send(404, {"ok": False, "error": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length or 0)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, {"ok": False, "error": "Invalid JSON"})
            return

        try:
            if self.path == "/api/study-check":
                result = EVALUATOR.evaluate(payload)
            elif self.path == "/api/paper/analyze":
                result = PAPER_BUILDER.analyze(payload)
            else:
                result = PAPER_BUILDER.apply(payload)
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": str(exc)})
            return

        self._send(200, result)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8130), StudyCheckHandler)
    print("Study-check backend listening on http://127.0.0.1:8130")
    server.serve_forever()


if __name__ == "__main__":
    main()
