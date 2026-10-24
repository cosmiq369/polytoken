import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from dotenv import dotenv_values

from polytoken.logs import JsonlLogger


def test_valid_append_only_jsonl_with_redaction(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("NVIDIA_API_KEY=never-record-this\nZETARIS_PASSWORD=also-private\nHF_TOKEN=private-hf\n")
    monkeypatch.setenv("ANOTHER_SECRET", "process-private")
    log = JsonlLogger(tmp_path / "logs", run_id="audit-run", env_file=env)
    log.write("audit", "first", nested={"password": "unknown-password", "text": "never-record-this also-private private-hf process-private"}, prompt_tokens=12)
    before = (tmp_path / "logs/audit.jsonl").read_bytes()
    log.write("audit", "second", authorization="Bearer unknown-credential")
    data = (tmp_path / "logs/audit.jsonl").read_bytes()
    assert data.startswith(before)
    for value in dotenv_values(env).values():
        assert value.encode() not in data
    assert b"process-private" not in data
    assert b"unknown-password" not in data
    assert b"unknown-credential" not in data
    rows = [json.loads(line) for line in data.splitlines()]
    assert [r["event"] for r in rows] == ["first", "second"]
    assert all(r["run_id"] == "audit-run" for r in rows)
    assert all(datetime.fromisoformat(r["ts"]).utcoffset().total_seconds() == 0 for r in rows)
    assert rows[0]["prompt_tokens"] == 12


def test_concurrent_loggers_keep_valid_rows(tmp_path):
    writers = [JsonlLogger(tmp_path) for _ in range(3)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: writers[n % 3].write("audit", "row", number=n), range(100)))
    rows = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert sorted(r["number"] for r in rows) == list(range(100))


def test_invalid_stream_cannot_escape_log_directory(tmp_path):
    with pytest.raises(ValueError):
        JsonlLogger(tmp_path).write("../bad", "row")
