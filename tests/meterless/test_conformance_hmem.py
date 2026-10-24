"""Faithful Python ports of all 13 H-MEM vectors and runner assertions at 1742dec."""

import pytest

from polytoken.logs import JsonlLogger
from polytoken.meterless.hmem import DAY_MS, HMem

T0 = 1_750_000_000_000


def memory(tmp_path, clock=None):
    return HMem(clock=clock or (lambda: T0), logger=JsonlLogger(tmp_path))


def test_rv_001_no_source_rejected(tmp_path):
    with pytest.raises(ValueError):
        memory(tmp_path).add(content="no source here", source="")


def test_rv_002_sourced_record_accepted(tmp_path):
    assert memory(tmp_path).add(content="valid record", source="test")


def _feedback(tmp_path, start, kind, expected, access=0, tag=None):
    h = memory(tmp_path)
    m = h.add(content="feedback target record", confidence=start, source="conformance")
    before = m.accessCount
    h.feedback(m.id, kind)
    after = h.store.get(m.id)
    assert after.confidence == pytest.approx(expected)
    assert after.accessCount - before == access
    if tag:
        assert tag in after.tags


def test_fd_001_helpful_delta(tmp_path):
    _feedback(tmp_path, .7, "helpful", .75, access=1)


def test_fd_002_not_helpful_delta(tmp_path):
    _feedback(tmp_path, .7, "not_helpful", .67)


def test_fd_003_wrong_delta_and_review_tag(tmp_path):
    _feedback(tmp_path, .7, "wrong", .5, tag="review")


def test_fd_004_clamp_at_zero(tmp_path):
    _feedback(tmp_path, .1, "wrong", 0)


def test_fd_005_clamp_at_one(tmp_path):
    _feedback(tmp_path, .98, "helpful", 1, access=1)


def test_ro_001_superseded_penalty_dominates(tmp_path):
    h = memory(tmp_path)
    fresh = h.add(content="we deploy the api with docker on mondays", confidence=.9, layer="long_term", source="conformance")
    old = h.add(content="we deploy the api with docker on fridays", confidence=.9, layer="long_term", source="conformance")
    old.supersededBy = fresh.id
    ranked = [r["memory"].id for r in h.query("when do we deploy the api with docker", threshold=0, top_n=10)["memories"]]
    assert ranked.index(fresh.id) < ranked.index(old.id)


def test_ro_002_confidence_multiplies_score(tmp_path):
    h = memory(tmp_path)
    high = h.add(content="the deploy window is monday morning", confidence=.9, layer="working", source="conformance")
    low = h.add(content="the deploy window is monday morning", confidence=.4, layer="working", source="conformance")
    ranked = [r["memory"].id for r in h.query("deploy window", threshold=0, top_n=10)["memories"]]
    assert ranked.index(high.id) < ranked.index(low.id)


def test_sg_001_archive_plain_protect_derived(tmp_path):
    now = T0
    h = memory(tmp_path, clock=lambda: now)
    plain = h.add(content="random one-off note about parking near the office", source="chat")
    derived = h.add(content="synthesized insight about the quarterly roadmap", source="dreaming", derived_from=["mem-x"])
    now = T0 + 40 * DAY_MS
    before = sorted(m.id for m in h.store.all())
    preview = h.sleep.preview()
    assert sorted(m.id for m in h.store.all()) == before
    assert plain.id in preview["toArchive"]
    assert derived.id not in preview["toArchive"]
    report = h.sleep.execute(preview)
    assert h.store.get(derived.id)
    assert isinstance(report["backupId"], str) and report["backupId"]


def test_cg_001_conflict_gate_keeps_both(tmp_path):
    h = memory(tmp_path)
    a = h.add(content="always enable telemetry uploads for diagnostics", confidence=.95, source="conformance")
    b = h.add(content="never enable telemetry uploads for diagnostics", confidence=.2, source="conformance")
    found = h.conflicts.scan()
    assert found
    outcome = h.conflicts.auto_resolve(found[0])
    assert outcome in ("resolved", "queued")
    if outcome == "resolved":
        assert h.store.get(a.id).supersededBy or h.store.get(b.id).supersededBy
    assert h.store.get(a.id) and h.store.get(b.id)


def test_la_001_ledger_order_and_state(tmp_path):
    h = memory(tmp_path)
    m = h.add(content="audited record", confidence=.7, source="conformance")
    h.feedback(m.id, "wrong")
    history = h.ledger.history(m.id)
    assert [entry["action"] for entry in history] == ["create", "feedback"]
    assert history[-1]["previousState"]["confidence"] == pytest.approx(.7)
    assert history[-1]["newState"]["confidence"] == pytest.approx(.5)


def test_db_001_dream_boundary_and_lineage(tmp_path):
    h = memory(tmp_path)
    h.add(content="prefer short bullet answers", type="preference", source="conformance")
    h.add(content="prefer python for scripting", type="preference", source="conformance")
    before = len(h.store.all())
    proposals = h.dreaming.dream()
    assert proposals
    assert len(h.store.all()) == before
    created = h.dreaming.approve(proposals[0]["id"])
    assert created.layer == "long_term"
    assert created.derivedFrom
