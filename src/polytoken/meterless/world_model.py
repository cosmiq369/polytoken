"""SQLite event log with replayable entities, contexts, and temporal edges."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from polytoken.logs import JsonlLogger


def normalize_name(name: str) -> str:
    value = unicodedata.normalize("NFKD", name)
    value = re.sub(r"[\u0300-\u036f\u200b-\u200d\ufeff]", "", value)
    return " ".join(value.lower().split())


def entity_id_from_name(type: str, name: str) -> str:
    return "ent_" + hashlib.sha256(f"{type}:{normalize_name(name)}".encode()).hexdigest()[:16]


def decide(score: float) -> str:
    if not 0 <= score <= 1:
        raise ValueError("similarity score must be between 0 and 1")
    return "auto-merge" if score >= .85 else "review" if score >= .82 else "new"


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorldModel:
    def __init__(self, path: str | Path = ".cache/state/world.sqlite", *,
                 storage: str | None = None, namespace: str = "polytoken",
                 logger: JsonlLogger | None = None):
        self.path = ":memory:" if storage == "memory" else str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.namespace = namespace
        self.logger = logger or JsonlLogger()
        self.commit_count = 0
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
              kind TEXT NOT NULL, item_key TEXT NOT NULL, payload TEXT NOT NULL,
              provenance TEXT NOT NULL, at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS events_key ON events(kind,item_key);
            CREATE TABLE IF NOT EXISTS entities (
              id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS contexts (
              id TEXT PRIMARY KEY, type TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS edges (
              id TEXT PRIMARY KEY, from_id TEXT NOT NULL, type TEXT NOT NULL,
              to_id TEXT NOT NULL, valid_from TEXT NOT NULL, valid_to TEXT,
              payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS edges_from ON edges(from_id,type,valid_from);
            CREATE TABLE IF NOT EXISTS audit (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL,
              action TEXT NOT NULL, at TEXT NOT NULL);
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @staticmethod
    def _provenance(source, *, strict=False):
        if not isinstance(source, dict) or not source.get("kind") or not source.get("at"):
            raise ValueError("source provenance requires kind and at")
        if strict and not all(source.get(key) for key in ("query", "time_window", "fetched_at")):
            raise ValueError("observation provenance requires query, time_window and fetched_at")
        return source

    def _append(self, kind, key, payload, source, *, cur=None):
        self._provenance(source)
        payload_json, source_json = _json(payload), _json(source)
        current = self.db.execute("SELECT event_id,payload,provenance FROM events WHERE kind=? AND item_key=? ORDER BY seq DESC LIMIT 1", (kind, key)).fetchone()
        if current and (current["payload"], current["provenance"]) == (payload_json, source_json):
            return None
        digest = hashlib.sha256(f"{kind}|{key}|{payload_json}|{source_json}".encode()).hexdigest()[:24]
        event_id = "evt_" + digest
        cursor = cur or self.db
        try:
            cursor.execute("INSERT INTO events(event_id,kind,item_key,payload,provenance,at) VALUES(?,?,?,?,?,?)",
                           (event_id, kind, key, payload_json, source_json, source["at"]))
        except sqlite3.IntegrityError:
            return None
        cursor.execute("INSERT INTO audit(event_id,action,at) VALUES(?,?,?)", (event_id, kind, _now()))
        return event_id

    def _log(self, kind, event_id, source):
        if event_id:
            self.logger.write("world_model", "mutation", action=kind, event_id=event_id,
                              source=source, namespace=self.namespace)

    def upsert_entity(self, *, type: str, name: str | None = None,
                      external_key: dict | None = None, attrs: dict | None = None,
                      source: dict | None = None) -> dict:
        self._provenance(source)
        if not name and not external_key:
            raise ValueError("entity needs name or external_key")
        eid = (f"{type}:{external_key['system']}:{external_key['id']}" if external_key
               else entity_id_from_name(type, name))
        payload = {"id": eid, "type": type, "name": name, "attrs": attrs or {}}
        with self.db:
            event_id = self._append("entity", eid, payload, source)
            if event_id:
                self.db.execute("INSERT INTO entities VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,name=excluded.name",
                                (eid, type, name, _json(payload)))
                self.commit_count += 1
        self._log("entity", event_id, source)
        return payload

    def upsert_context(self, *, type: str, key: str, attrs: dict | None = None, source: dict) -> dict:
        self._provenance(source)
        cid = f"{type}:{key}"
        payload = {"id": cid, "type": type, "attrs": attrs or {}}
        with self.db:
            event_id = self._append("context", cid, payload, source)
            if event_id:
                self.db.execute("INSERT INTO contexts VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                                (cid, type, _json(payload)))
                self.commit_count += 1
        self._log("context", event_id, source)
        return payload

    def relate(self, *, from_id: str, type: str, to_id: str, valid_from: str,
               source: dict, context: str = "") -> dict:
        self._provenance(source)
        eid = "rel_" + hashlib.sha256(f"{from_id}|{type}|{to_id}|{context}|{valid_from}".encode()).hexdigest()[:16]
        payload = {"id": eid, "from": from_id, "type": type, "to": to_id,
                   "validFrom": valid_from, "context": context}
        with self.db:
            event_id = self._append("relationship", eid, payload, source)
            if event_id:
                self.db.execute("UPDATE edges SET valid_to=? WHERE from_id=? AND type=? AND valid_to IS NULL AND to_id<>?",
                                (valid_from, from_id, type, to_id))
                self.db.execute("INSERT INTO edges VALUES(?,?,?,?,?,?,?)", (eid, from_id, type, to_id, valid_from, None, _json(payload)))
                self.commit_count += 1
        self._log("relationship", event_id, source)
        return payload

    def neighbors_of(self, entity_id: str, *, via: str, at: str | None = None) -> list[dict]:
        when = at or "9999-12-31T00:00:00Z"
        rows = self.db.execute("""SELECT e.payload FROM edges r JOIN entities e ON e.id=r.to_id
          WHERE r.from_id=? AND r.type=? AND r.valid_from<=? AND (r.valid_to IS NULL OR r.valid_to>?)""",
          (entity_id, via, when, when)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def ingest(self, observations: list[dict]) -> dict:
        logs = []
        with self.db:
            for item in observations:
                source = self._provenance(item.get("source"))
                key = str(item.get("externalId") or item.get("id") or hashlib.sha256(_json(item).encode()).hexdigest())
                event_id = self._append("observation", key, item, source, cur=self.db)
                if event_id:
                    logs.append(("observation", event_id, source))
                for entity in item.get("entities", []):
                    eid = entity_id_from_name(entity["type"], entity["name"])
                    payload = {"id": eid, "type": entity["type"], "name": entity["name"], "attrs": {}}
                    ee = self._append("entity", eid, payload, source, cur=self.db)
                    if ee:
                        self.db.execute("INSERT INTO entities VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                                        (eid, entity["type"], entity["name"], _json(payload)))
                        logs.append(("entity", ee, source))
            if logs:
                self.commit_count += 1
        for kind, event_id, source in logs:
            self._log(kind, event_id, source)
        return {"changed": bool(logs), "events": len(logs)}

    def evidence_event(self, kind: str, item_key: str, payload: dict, source: dict) -> str | None:
        self._provenance(source, strict=True)
        with self.db:
            event_id = self._append(kind, item_key, payload, source)
            if event_id:
                self.commit_count += 1
        self._log(kind, event_id, source)
        return event_id

    def evidence_batch(self, rows: list[tuple[str, str, dict, dict]]) -> list[str]:
        logs = []
        with self.db:
            for kind, key, payload, source in rows:
                self._provenance(source, strict=True)
                event_id = self._append(kind, key, payload, source, cur=self.db)
                if event_id:
                    logs.append((kind, event_id, source))
            if logs:
                self.commit_count += 1
        for kind, event_id, source in logs:
            self._log(kind, event_id, source)
        return [event_id for _, event_id, _ in logs]

    def events(self, kind: str | None = None) -> list[dict]:
        rows = self.db.execute("SELECT * FROM events WHERE (? IS NULL OR kind=?) ORDER BY seq", (kind, kind))
        return [{**dict(row), "payload": json.loads(row["payload"]),
                 "provenance": json.loads(row["provenance"])} for row in rows]

    def audit(self) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM audit ORDER BY seq")]

    def counts(self) -> dict:
        return {table: self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("entities", "contexts", "edges", "events", "audit")}

    def state_shape_canonical(self) -> str:
        return _json({table: [dict(row) for row in self.db.execute(f"SELECT * FROM {table} ORDER BY 1")]
                      for table in ("entities", "contexts", "edges", "events", "audit")})
