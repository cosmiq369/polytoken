"""Tiered, sourced memory with deterministic retrieval and audited governance."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

from polytoken.logs import JsonlLogger

LAYERS = frozenset({"short_term", "working", "long_term"})
DAY_MS = 86_400_000


def _clamp(value):
    return max(0.0, min(1.0, value))


def _words(text):
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _embed(text: str) -> dict[int, float]:
    """Small deterministic hashed character trigram vector, no downloaded model."""
    normalized = " ".join(_words(text))
    vector = {}
    for i in range(max(0, len(normalized) - 2)):
        key = int.from_bytes(hashlib.sha256(normalized[i:i + 3].encode()).digest()[:2], "big")
        vector[key] = vector.get(key, 0) + 1
    norm = math.sqrt(sum(v * v for v in vector.values())) or 1
    return {k: v / norm for k, v in vector.items()}


def _cosine(a, b):
    return sum(v * b.get(k, 0) for k, v in a.items())


@dataclass
class Memory:
    id: str
    content: str
    source: str
    confidence: float
    layer: str
    createdAt: int
    lastAccessed: int
    accessCount: int = 0
    tags: list[str] = field(default_factory=list)
    domain: str = "general"
    entities: list[str] = field(default_factory=list)
    type: str = "fact"
    derivedFrom: list[str] = field(default_factory=list)
    supersededBy: str | None = None
    provenance: dict = field(default_factory=dict)
    relatedTo: list[str] = field(default_factory=list)
    supersedes: str | None = None


class Ledger:
    def __init__(self, logger, db=None):
        self.db = db
        self.entries = ([json.loads(row[0]) for row in db.execute("SELECT entry FROM ledger ORDER BY seq")]
                        if db else [])
        self.logger = logger

    def record(self, memory_id, action, actor, timestamp, previous=None, new=None, **details):
        entry = {"memoryId": memory_id, "action": action, "actor": actor,
                 "timestamp": timestamp, "previousState": previous, "newState": new,
                 "details": details}
        self.entries.append(entry)
        if self.db:
            with self.db:
                self.db.execute("INSERT INTO ledger(entry) VALUES(?)", (json.dumps(entry, ensure_ascii=False),))
        self.logger.write("hmem", "audit", **entry)

    def history(self, memory_id):
        return [entry for entry in self.entries if entry["memoryId"] == memory_id]


class Store:
    def __init__(self):
        self.records = {}

    def get(self, memory_id):
        return self.records.get(memory_id)

    def all(self):
        return list(self.records.values())


class Sleep:
    def __init__(self, owner):
        self.owner = owner
        self.backups = {}

    def preview(self):
        now = self.owner.clock()
        referenced = {id for m in self.owner.store.all() for id in m.derivedFrom}
        referenced.update(m.supersededBy for m in self.owner.store.all() if m.supersededBy)
        archivable = []
        consolidate = []
        for m in self.owner.store.all():
            age = (now - m.createdAt) / DAY_MS
            if m.layer == "short_term" and age >= 7:
                consolidate.append(m.id)
            if (age >= 30 and m.accessCount <= 2 and not m.derivedFrom and
                not m.supersededBy and m.id not in referenced and m.type != "profile"):
                archivable.append(m.id)
        return {"toArchive": archivable, "toConsolidate": consolidate, "toSynthesize": []}

    def execute(self, preview):
        backup_id = "backup_" + uuid4().hex
        self.backups[backup_id] = copy.deepcopy(self.owner.store.records)
        for mid in preview["toConsolidate"]:
            m = self.owner.store.get(mid)
            if m and mid not in preview["toArchive"]:
                before = copy.deepcopy(m.__dict__)
                m.layer = "long_term"
                self.owner.ledger.record(mid, "sleep_consolidate", "system", self.owner.clock(), before, copy.deepcopy(m.__dict__))
        for mid in preview["toArchive"]:
            m = self.owner.store.records.pop(mid, None)
            if m:
                self.owner.ledger.record(mid, "sleep_archive", "system", self.owner.clock(), copy.deepcopy(m.__dict__), None)
        self.owner._persist()
        return {"backupId": backup_id, "archived": len(preview["toArchive"])}

    def restore(self, backup_id):
        self.owner.store.records = copy.deepcopy(self.backups[backup_id])
        self.owner._persist()
        self.owner.ledger.record(None, "restore", "system", self.owner.clock(), backupId=backup_id)


class Conflicts:
    def __init__(self, owner):
        self.owner = owner

    def scan(self):
        found = []
        records = self.owner.store.all()
        for i, a in enumerate(records):
            for b in records[i + 1:]:
                wa, wb = set(_words(a.content)), set(_words(b.content))
                if (("always" in wa and "never" in wb) or ("never" in wa and "always" in wb)):
                    rest_a, rest_b = wa - {"always", "never"}, wb - {"always", "never"}
                    if len(rest_a & rest_b) / max(1, len(rest_a | rest_b)) >= .6:
                        conflict = {"a": a.id, "b": b.id, "reason": "always/never contradiction"}
                        found.append(conflict)
                        self.owner.ledger.record(a.id, "conflict_detected", "system", self.owner.clock(), **conflict)
        return found

    def auto_resolve(self, conflict):
        a, b = (self.owner.store.get(conflict[key]) for key in ("a", "b"))
        decision_confidence = abs(a.confidence - b.confidence)
        if decision_confidence < .70:
            return "queued"
        winner, loser = (a, b) if a.confidence >= b.confidence else (b, a)
        before = copy.deepcopy(loser.__dict__)
        loser.supersededBy = winner.id
        self.owner._persist()
        self.owner.ledger.record(loser.id, "conflict_resolved", "system", self.owner.clock(),
                                 before, copy.deepcopy(loser.__dict__), decisionConfidence=decision_confidence)
        return "resolved"


class Dreaming:
    def __init__(self, owner):
        self.owner = owner
        self.proposals = {}

    def dream(self):
        groups = {}
        for m in self.owner.store.all():
            if m.type in ("preference", "personal", "correction"):
                groups.setdefault(m.type, []).append(m)
        created = []
        for typ, records in groups.items():
            if len(records) < 2:
                continue
            proposal = {"id": "dream_" + uuid4().hex, "type": "invariant",
                        "content": "; ".join(m.content for m in records[:8]),
                        "derivedFrom": [m.id for m in records[:8]]}
            self.proposals[proposal["id"]] = proposal
            created.append(proposal)
            self.owner.ledger.record(None, "dream_proposed", "system", self.owner.clock(), proposalId=proposal["id"])
        return created

    def approve(self, proposal_id):
        proposal = self.proposals.pop(proposal_id)
        m = self.owner.add(content=proposal["content"], source="dreaming", confidence=.8,
                           layer="long_term", type="preference", derived_from=proposal["derivedFrom"])
        self.owner.ledger.record(m.id, "dream_approved", "human", self.owner.clock(), proposalId=proposal_id)
        return m

    def reject(self, proposal_id):
        self.proposals.pop(proposal_id)
        self.owner.ledger.record(None, "dream_rejected", "human", self.owner.clock(), proposalId=proposal_id)


class HMem:
    def __init__(self, *, clock=None, logger: JsonlLogger | None = None, path: str | Path | None = None):
        self.clock = clock or (lambda: int(time.time() * 1000))
        self.logger = logger or JsonlLogger()
        self.db = None
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path)
            self.db.execute("CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, record TEXT NOT NULL)")
            self.db.execute("CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT, entry TEXT NOT NULL)")
            self.db.commit()
        self.store = Store()
        if self.db:
            for row in self.db.execute("SELECT record FROM memories"):
                data = json.loads(row[0])
                self.store.records[data["id"]] = Memory(**data)
        self.ledger = Ledger(self.logger, self.db)
        self.sleep = Sleep(self)
        self.conflicts = Conflicts(self)
        self.dreaming = Dreaming(self)

    def _persist(self):
        if self.db is None:
            return
        with self.db:
            self.db.execute("DELETE FROM memories")
            self.db.executemany("INSERT INTO memories VALUES(?,?)",
                                ((m.id, json.dumps(asdict(m), ensure_ascii=False))
                                 for m in self.store.all() if m.layer != "short_term"))

    def close(self):
        if self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def add(self, *, content: str, source: str, confidence: float = .7,
            layer: str = "short_term", tags=None, domain="general", entities=None,
            type="fact", derived_from=None):
        if not source or not source.strip():
            raise ValueError("memory source is required")
        if not content or not content.strip():
            raise ValueError("memory content is required")
        if layer not in LAYERS or not 0 <= confidence <= 1:
            raise ValueError("invalid layer or confidence")
        now = self.clock()
        m = Memory("mem_" + uuid4().hex, content, source, confidence, layer, now, now,
                   tags=list(tags or []), domain=domain, entities=list(entities or []),
                   type=type, derivedFrom=list(derived_from or []),
                   provenance={"origin": source, "learnedAt": now, "label": source})
        self.store.records[m.id] = m
        self._persist()
        self.ledger.record(m.id, "create", "system", now, None, copy.deepcopy(m.__dict__))
        return m

    def feedback(self, memory_id, kind):
        m = self.store.get(memory_id)
        if m is None:
            raise KeyError(memory_id)
        if kind not in ("helpful", "not_helpful", "wrong"):
            raise ValueError("unknown feedback")
        before = copy.deepcopy(m.__dict__)
        m.confidence = _clamp(m.confidence + {"helpful": .05, "not_helpful": -.03, "wrong": -.20}[kind])
        if kind == "helpful":
            m.accessCount += 1
            m.lastAccessed = self.clock()
        if kind == "wrong" and "review" not in m.tags:
            m.tags.append("review")
        self._persist()
        self.ledger.record(m.id, "feedback", "user", self.clock(), before, copy.deepcopy(m.__dict__), kind=kind)

    def query(self, query: str, *, threshold=.35, top_n=5):
        query_vec = _embed(query)
        keywords = set(_words(query)[:8])
        ranked = []
        for m in self.store.all():
            words = set(_words(m.content))
            keyword = len(keywords & words) / max(1, len(keywords | words))
            semantic = _cosine(query_vec, _embed(m.content))
            tag = float(bool(keywords & set(m.tags)))
            domain = float(m.domain in keywords)
            entity = float(bool(keywords & {x.lower() for x in m.entities}))
            layer = {"long_term": 1, "working": .8, "short_term": .6}[m.layer]
            recency = math.exp(-max(0, self.clock() - m.lastAccessed) / (14 * DAY_MS))
            raw = (.35 * semantic + .20 * keyword + .10 * tag + .10 * domain +
                   .15 * entity + .05 * layer + .05 * recency - .20 * bool(m.supersededBy))
            score = _clamp(raw) * m.confidence
            if score >= threshold:
                ranked.append({"memory": m, "score": score, "retrievalReason": "hybrid"})
        ranked.sort(key=lambda row: (-row["score"], row["memory"].id))
        return {"memories": ranked[:top_n], "strategy": "hybrid"}
