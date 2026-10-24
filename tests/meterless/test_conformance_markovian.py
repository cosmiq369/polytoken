"""Faithful Python ports of Markovian conformance/runner.ts at 1742dec."""

import pytest

from polytoken.meterless.markovian import (ChunkConfig, ConfigValidationError,
                                          Markovian, model_totals, run_efficiency)


def step_gen(total):
    calls = 0
    def generate(_prompt):
        nonlocal calls
        calls += 1
        done = calls >= total
        body = (f"Output for step {calls} with enough text to register in the accounting math. " * 10)
        marker = "[TASK_COMPLETE]" if done else (f"[STATE_CHECKPOINT]\nCOMPLETED: steps 1-{calls}\n"
                    f"REMAINING: {total-calls}\nDECISIONS: none\nCONTEXT: conformance")
        return {"text": body + "\n" + marker}
    return generate


def test_eff_001_worked_example(tmp_path):
    result = model_totals(20)
    assert result["naiveTotal"] == 246_000
    assert result["markovianTotal"] == 34_000
    assert abs(result["efficiency"] * 100 - 86.18) < .5


def test_snap_001_run_config_snapshot(tmp_path):
    run = Markovian({"chunkSize": 4000, "carryoverTokens": 640}).run("snapshot check", step_gen(3), reflect=False)
    assert run["chunkConfig"]["carryoverTokens"] == 640


def test_snap_002_historical_efficiency_uses_snapshot():
    chunks = [{"id": i, "tokens": 1000, "carryover": "", "content": ""} for i in range(1, 5)]
    a = run_efficiency(chunks, {"chunkSize": 8000, "maxChunks": 24, "carryoverTokens": 512, "overlapTokens": 0})
    b = run_efficiency(chunks, {"chunkSize": 8000, "maxChunks": 24, "carryoverTokens": 2048, "overlapTokens": 0})
    assert a["standardCost"] == 10_000
    assert a["markovianCost"] == 6_048
    assert a["tokensSaved"] != b["tokensSaved"]


def test_ovl_001_nonzero_overlap_rejected():
    with pytest.raises(ConfigValidationError, match="overlapTokens"):
        Markovian({"chunkSize": 4000, "carryoverTokens": 640, "overlapTokens": 64})


def test_lab_001_token_label():
    run = Markovian({"chunkSize": 4000, "carryoverTokens": 640}).run("label check", step_gen(2), reflect=False)
    assert run["tokenLabel"] in ("estimated", "measured")


def test_ref_001_reflection_failure_does_not_fail():
    calls = 0
    def generate(_prompt):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("provider exploded in reflection")
        return {"text": "done in one chunk [TASK_COMPLETE]"}
    run = Markovian({"chunkSize": 4000, "carryoverTokens": 640}).run("reflection failure", generate)
    assert run["status"] == "completed"


def test_mrk_001_markers_drive_completion_and_are_cleaned():
    run = Markovian({"chunkSize": 4000, "carryoverTokens": 640}).run("marker cleaning", step_gen(3), reflect=False)
    assert run["status"] == "completed"
    assert "STATE_CHECKPOINT" not in run["output"] and "TASK_COMPLETE" not in run["output"]
    assert len(run["chunks"]) == 3


def test_cfg_001_out_of_bounds_typed_error():
    with pytest.raises(ConfigValidationError):
        Markovian({"chunkSize": 128, "carryoverTokens": 640})
