"""H-MEM adapter for sourced company profiles and past findings."""

from __future__ import annotations

from .hmem import HMem


class CompanyMemory:
    def __init__(self, hmem: HMem):
        self.hmem = hmem

    def remember_profile(self, company: str, *, monthly_volume: int, reply_time_target_ms: int,
                         model: str, constraints: list[str], source: str,
                         confidence: float = 1.0):
        content = (f"{company}: monthly volume {monthly_volume}; reply-time target "
                   f"{reply_time_target_ms} ms; model {model}; constraints: {', '.join(constraints)}")
        return self.hmem.add(content=content, source=source, confidence=confidence,
                             layer="long_term", domain="company", entities=[company], type="profile")

    def remember_finding(self, company: str, finding: str, *, evidence_ids: list[str],
                         source: str, confidence: float):
        if not evidence_ids:
            raise ValueError("finding requires World Model evidence ids")
        return self.hmem.add(content=f"{company}: {finding}", source=source,
                             confidence=confidence, layer="working", domain="investigation",
                             entities=[company], derived_from=evidence_ids, type="finding")
