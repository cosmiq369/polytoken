"""Append-only JSONL telemetry with recursive secret redaction."""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from dotenv import dotenv_values

_LOCK = threading.Lock()
_SENSITIVE = re.compile(r"(?:api_?key|password|secret|authorization|credential|(?:^|_)\w*token$)", re.I)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_BEARER = re.compile(r"\bBearer\s+[^\s\"',;]+", re.I)
_JSON_SECRET = re.compile(
    r'("[^"\\]*(?:token|password|secret|api_?key|authorization)[^"\\]*"\s*:\s*)"(?:\\.|[^"\\])*"',
    re.I,
)


class JsonlLogger:
    def __init__(
        self, directory: str | Path = "logs", *, run_id: str | None = None,
        secrets: Iterable[str] = (), env_file: str | Path = ".env",
    ) -> None:
        self.directory = Path(directory)
        self.run_id = run_id or str(uuid4())
        env_items = [*dotenv_values(env_file, interpolate=False).items(), *os.environ.items()]
        self._secrets = set(v for k, v in env_items if v and _SENSITIVE.search(k))
        self._secrets.update(v for v in secrets if v)

    def add_secrets(self, *values: str) -> None:
        with _LOCK:
            self._secrets.update(v for v in values if v)

    def redact(self, value: Any) -> Any:
        if isinstance(value, str):
            for secret in sorted(self._secrets, key=len, reverse=True):
                value = value.replace(secret, "[REDACTED]")
            value = _JSON_SECRET.sub(r'\1"[REDACTED]"', value)
            return _BEARER.sub("Bearer [REDACTED]", _JWT.sub("[REDACTED]", value))
        if isinstance(value, dict):
            return {
                self.redact(str(k)): "[REDACTED]" if _SENSITIVE.search(str(k)) else self.redact(v)
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self.redact(v) for v in value]
        return value

    def write(self, stream: str, event: str, **fields: Any) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", stream):
            raise ValueError("Invalid JSONL stream name")
        with _LOCK:
            row = self.redact({
                **fields, "ts": datetime.now(timezone.utc).isoformat(),
                "run_id": self.run_id, "event": event,
            })
            line = json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"
            self.directory.mkdir(parents=True, exist_ok=True)
            with (self.directory / f"{stream}.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(line)
