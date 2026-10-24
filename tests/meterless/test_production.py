"""Integration properties that matter at PolyToken's measured workload size."""

import time

from polytoken.logs import JsonlLogger
from polytoken.meterless.evidence import EvidenceStore, ingest_federation_sample
from polytoken.meterless.company_memory import CompanyMemory
from polytoken.meterless.hmem import HMem
from polytoken.meterless.markovian import Markovian
from polytoken.meterless.world_model import WorldModel


def test_7168_evidence_rows_batched_under_five_seconds(tmp_path):
    source = {"kind": "zetaris", "at": "2026-10-24T00:00:00Z",
              "query": "SELECT * FROM measurements", "time_window": "demo corpus",
              "fetched_at": "2026-10-24T00:00:00Z"}
    rows = [{"measurement_id": i, "native_tokens": i % 29 + 1} for i in range(7168)]
    start = time.monotonic()
    with WorldModel(tmp_path / "world.sqlite", logger=JsonlLogger(tmp_path / "logs")) as world:
        ids = EvidenceStore(world).add_batch("measurement", rows, source=source)
        assert len(ids) == 7168
        assert world.commit_count <= 10
        assert world.counts()["events"] == 7168
    assert time.monotonic() - start < 5


def test_generator_never_exceeds_chunk_cap_plus_reflection(tmp_path):
    calls = 0
    def generate(_prompt):
        nonlocal calls
        calls += 1
        return {"text": "Still working [STATE_CHECKPOINT] state"}
    run = Markovian({"maxChunks": 3}, logger=JsonlLogger(tmp_path)).run("bounded", generate)
    assert len(run["chunks"]) == 3
    assert calls <= run["chunkConfig"]["maxChunks"] + 1


def test_measured_provider_usage_sets_label(tmp_path):
    run = Markovian({"maxChunks": 1}, logger=JsonlLogger(tmp_path)).run(
        "usage", lambda _: {"text": "Done [TASK_COMPLETE]", "usage": {"prompt_tokens": 10, "completion_tokens": 5}}, reflect=False)
    assert run["tokenLabel"] == "measured"
    assert run["chunks"][0]["tokens"] == 15


def test_claim_supports_only_recorded_events(tmp_path):
    source = {"kind": "zetaris", "at": "2026-10-24T00:00:00Z", "query": "select 1",
              "time_window": "2026-10-24", "fetched_at": "2026-10-24T00:00:00Z"}
    with WorldModel(tmp_path / "world.sqlite", logger=JsonlLogger(tmp_path / "logs")) as world:
        evidence = EvidenceStore(world)
        measurement_id = evidence.add("measurement", {"native_tokens": 4}, source=source)
        evidence.add("claim", {"text": "four tokens"}, source=source,
                     evidence_id="claim-1", supports=[measurement_id])
        assert [e["event_id"] for e in evidence.evidence_for("claim-1")] == [measurement_id]


def test_company_profile_and_finding_survive_restart(tmp_path):
    path = tmp_path / "hmem.sqlite"
    with HMem(path=path, logger=JsonlLogger(tmp_path / "logs")) as hmem:
        memory = CompanyMemory(hmem)
        profile = memory.remember_profile("samudra", monthly_volume=10000,
                  reply_time_target_ms=800, model="a-model", constraints=["replies stay in Telugu"],
                  source="company.bot_config", confidence=.9)
        finding = memory.remember_finding("samudra", "native tokens exceed English",
                  evidence_ids=["evt-1"], source="investigation-1", confidence=.8)
    with HMem(path=path, logger=JsonlLogger(tmp_path / "logs")) as hmem:
        assert hmem.store.get(profile.id).confidence == .9
        assert hmem.store.get(finding.id).derivedFrom == ["evt-1"]
        assert len(hmem.ledger.history(profile.id)) == 1


def test_saved_federation_provenance_and_idempotence(tmp_path):
    from pathlib import Path
    sample = Path(__file__).resolve().parents[2] / "logs/sample/federation.jsonl"
    with WorldModel(tmp_path / "world.sqlite", logger=JsonlLogger(tmp_path / "logs")) as world:
        assert len(ingest_federation_sample(world, sample)) == 96
        assert ingest_federation_sample(world, sample) == []
        assert world.counts()["entities"] == 10
        event = world.events("query_result")[0]
        assert event["provenance"]["kind"] == "Zetaris SQL"
        assert event["provenance"]["time_window"]["start"]
