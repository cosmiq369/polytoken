# Meterless engines in PolyToken

These are independent Python implementations of the Meterless reference architecture specifications and conformance checks at commit [`1742dec56a66e58eef9dda2d2b865823758ca8cd`](https://github.com/Meterless/Meterless/tree/1742dec56a66e58eef9dda2d2b865823758ca8cd). The specifications and ported checks are attributed to Meterless under Apache-2.0. No Meterless implementation code is vendored or run by PolyToken.

## Markovian

`src/polytoken/meterless/markovian.py` runs bounded investigation chunks through one injected callable. It removes the checkpoint and completion markers from display text, bounds carried state, records a config snapshot on every run, and labels tokens `measured` only when the generator returns prompt and completion usage. `model_totals` is the documented symbolic projection; `run_efficiency` uses the actual run tokens and its own config snapshot. Both figures go to `logs/markovian.jsonl`. The CLI's `engines-demo` exercises it offline or with the production `NvidiaGenerator`.

The spec lists UI slider steps for `chunkSize` and `carryoverTokens`, but the documented default carryover of 800 is not on a strict 128-token grid. Following the reference ruling, the implementation validates integer bounds and the framing/carryover/output budget without treating slider steps as a hard constraint. A nonzero `overlapTokens` raises `ConfigValidationError` naming that field. Reflection failures are logged and do not invalidate the run.

| Check | Python test | Status |
|---|---|---|
| eff-001 | `test_eff_001_worked_example` | PASS |
| snap-001 | `test_snap_001_run_config_snapshot` | PASS |
| snap-002 | `test_snap_002_historical_efficiency_uses_snapshot` | PASS |
| ovl-001 | `test_ovl_001_nonzero_overlap_rejected` | PASS |
| lab-001 | `test_lab_001_token_label` | PASS |
| ref-001 | `test_ref_001_reflection_failure_does_not_fail` | PASS |
| mrk-001 | `test_mrk_001_markers_drive_completion_and_are_cleaned` | PASS |
| cfg-001 | `test_cfg_001_out_of_bounds_typed_error` | PASS |

## World Model

`world_model.py` keeps canonical events in SQLite and derives entity, context, and edge read tables. Every mutation receives an ordered audit entry in SQLite and `logs/world_model.jsonl`. Re-ingesting an identical batch gives an empty diff. Edges close when a successor of the same type is added; point-in-time neighbor queries use validity bounds. `evidence.py` maps `measurement`, `query_result`, `price`, `timed_call`, `quality_verdict`, and `claim` to sourced events. It requires `source`, `query`, `time_window`, and `fetched_at` for evidence, and `evidence_for(claim_id)` returns only recorded supporting events. The checker in PROMPT-04 can use this read surface. The offline demo imports the two saved Zetaris federation snapshots as 96 query-result events, with company and tokenizer entities.

The upstream conformance fixtures use only `{kind, at}` for provenance; PolyToken's evidence adapter adds the stricter query, time window, and fetch time required by this project. `normalize_name` follows the reference's NFKD normalization and strips only U+0300–U+036F plus zero-width U+200B–U+200D and U+FEFF. It preserves Indic vowel signs and virama. The extra Indic test checks `दवा`/`दव`, `किताब`/`कताब`, and `రేషన్ కార్డు`/`రషన కరడ` remain distinct.

| Check | Python test | Status |
|---|---|---|
| sid-001 | `test_sid_001_diacritics_and_nbsp` | PASS |
| sid-002 | `test_sid_002_distinct_names_and_types` | PASS |
| band-001 | `test_band_001_merge_boundaries` | PASS |
| prov-001 | `test_prov_001_missing_provenance_rejected` | PASS |
| idem-001 | `test_idem_001_same_batch_empty_diff` | PASS |
| idem-002 | `test_idem_002_mutated_batch_changes_shape` | PASS |
| bitemp-001 | `test_bitemp_001_superseding_edge_and_point_in_time` | PASS |
| audit-001 | `test_audit_001_every_mutation_audited_in_order` | PASS |

## H-MEM

`hmem.py` keeps sourced records in `short_term`, `working`, and `long_term` tiers. The latter two can persist in a caller-supplied SQLite path. Retrieval combines a deterministic local hashed character trigram vector with the spec's keyword, tag, domain, entity, layer, recency, confidence, and supersession signals. Feedback applies exact deltas and clamps. Sleep previews before changing records, preserves derived and linked memories, and creates a backup. Conflict resolution retains both records and marks the loser. Dream synthesis proposes candidates without writing memories until human approval. Every trust ledger action is appended to `logs/hmem.jsonl` and, when configured, SQLite. `company_memory.py` stores company profiles and findings with sources, confidence, and World Model evidence IDs.

| Check | Python test | Status |
|---|---|---|
| rv-001 | `test_rv_001_no_source_rejected` | PASS |
| rv-002 | `test_rv_002_sourced_record_accepted` | PASS |
| fd-001 | `test_fd_001_helpful_delta` | PASS |
| fd-002 | `test_fd_002_not_helpful_delta` | PASS |
| fd-003 | `test_fd_003_wrong_delta_and_review_tag` | PASS |
| fd-004 | `test_fd_004_clamp_at_zero` | PASS |
| fd-005 | `test_fd_005_clamp_at_one` | PASS |
| ro-001 | `test_ro_001_superseded_penalty_dominates` | PASS |
| ro-002 | `test_ro_002_confidence_multiplies_score` | PASS |
| sg-001 | `test_sg_001_archive_plain_protect_derived` | PASS |
| cg-001 | `test_cg_001_conflict_gate_keeps_both` | PASS |
| la-001 | `test_la_001_ledger_order_and_state` | PASS |
| db-001 | `test_db_001_dream_boundary_and_lineage` | PASS |

## Scope and verification

Scout Intent is outside PolyToken's required engine set. H-MEM model-driven acquisition, full relationship discovery, UI features, and synthesis beyond the conformance surface are deferred: company profiles and evidence-linked investigation findings are stored directly. Generic World Model clustering and enrichment pipelines are likewise outside the evidence adapter. These are deliberate scope limits, not relaxed conformance assertions.

`tests/meterless/test_production.py` additionally verifies a 7,168-row evidence batch uses at most ten commits and finishes under five seconds, a run never calls its generator more than `maxChunks` plus one reflection, provider usage labels a run `measured`, claim support retrieval, and durable company memory. All 29 pinned conformance checks are ported with their original IDs and expected boundaries. No pinned check was omitted or weakened.
