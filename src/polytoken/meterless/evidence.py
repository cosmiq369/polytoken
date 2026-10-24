"""PolyToken evidence adapter; checker input is the World Model event log."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .world_model import WorldModel

KINDS = frozenset({"measurement", "query_result", "price", "timed_call", "quality_verdict", "claim"})


class EvidenceStore:
    def __init__(self, world: WorldModel):
        self.world = world

    def add(self, kind: str, payload: dict, *, source: dict, evidence_id: str | None = None,
            supports: list[str] | None = None) -> str | None:
        if kind not in KINDS:
            raise ValueError(f"unsupported evidence kind: {kind}")
        eid = evidence_id or hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
        record = {**payload, "supports": supports or []}
        return self.world.evidence_event(kind, eid, record, source)

    def add_batch(self, kind: str, payloads: list[dict], *, source: dict) -> list[str]:
        if kind not in KINDS:
            raise ValueError(f"unsupported evidence kind: {kind}")
        rows = []
        for payload in payloads:
            eid = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
            rows.append((kind, eid, {**payload, "supports": payload.get("supports", [])}, source))
        return self.world.evidence_batch(rows)

    def evidence_for(self, claim_id: str) -> list[dict]:
        claims = [event for event in self.world.events("claim") if event["item_key"] == claim_id]
        if not claims:
            return []
        wanted = set(claims[-1]["payload"].get("supports", []))
        return [event for event in self.world.events() if event["event_id"] in wanted]


def ingest_federation_sample(world: WorldModel, path: str | Path) -> list[str]:
    """Ingest the saved Zetaris result rows without claiming live measurement."""
    added = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        source = {"kind": record["source"], "at": record["ts"],
                  "query": record["query"], "time_window": record["time_window"],
                  "fetched_at": record["fetched_at"]}
        payloads = record["rows"]
        for company in sorted({row["company"] for row in payloads}):
            world.upsert_entity(type="company", name=company, source=source)
        for tokenizer in sorted({row["tokenizer_spec"] for row in payloads}):
            world.upsert_entity(type="tokenizer", name=tokenizer, source=source)
        added.extend(EvidenceStore(world).add_batch("query_result", payloads, source=source))
    return added
