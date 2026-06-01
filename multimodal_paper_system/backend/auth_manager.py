from __future__ import annotations

import re
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timezone


STATUS_RE = re.compile(r"Logged in using (?P<mode>.+)")
URL_RE = re.compile(r"https://auth\.openai\.com/codex/device")
CODE_RE = re.compile(r"\b[A-Z0-9]{4,5}-[A-Z0-9]{4,6}\b")


@dataclass
class AuthSession:
    process: subprocess.Popen[str]
    url: str | None = None
    code: str | None = None
    started_at: str | None = None
    output: str = ""
    completed: bool = False


class CodexAuthManager:
    def __init__(self) -> None:
        self._session: AuthSession | None = None
        self._lock = threading.Lock()

    def status(self) -> dict:
        output = self._run_status()
        logged_in = False
        mode = "unknown"
        if output:
            match = STATUS_RE.search(output)
            if match:
                logged_in = True
                mode = match.group("mode").strip()

        session = self._session_payload()
        if self._session and self._session.process.poll() is not None:
            session["processExited"] = True
        return {
            "loggedIn": logged_in,
            "mode": mode,
            "rawStatus": output.strip(),
            "session": session,
        }

    def start_device_auth(self) -> dict:
        with self._lock:
            if self._session and self._session.process.poll() is None and self._session.url and self._session.code:
                return self._session_payload()

            process = subprocess.Popen(
                ["codex", "login", "--device-auth"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
            )
            session = AuthSession(
                process=process,
                started_at=self._now(),
            )
            self._session = session

            while True:
                line = process.stdout.readline() if process.stdout else ""
                if not line:
                    break
                session.output += line
                if not session.url:
                    found_url = URL_RE.search(line)
                    if found_url:
                        session.url = found_url.group(0)
                if not session.code:
                    found_code = CODE_RE.search(line)
                    if found_code:
                        session.code = found_code.group(0)
                if session.url and session.code:
                    break

            return self._session_payload()

    def clear_finished_session(self) -> None:
        with self._lock:
            if self._session and self._session.process.poll() is not None:
                self._session = None

    def _run_status(self) -> str:
        proc = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            check=False,
        )
        return (proc.stdout or proc.stderr or "").strip()

    def _session_payload(self) -> dict:
        if not self._session:
            return {"active": False}
        return {
            "active": self._session.process.poll() is None,
            "url": self._session.url,
            "code": self._session.code,
            "startedAt": self._session.started_at,
            "output": self._session.output[-1200:],
            "processExited": self._session.process.poll() is not None,
        }

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
