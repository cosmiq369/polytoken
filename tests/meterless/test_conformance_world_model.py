"""Faithful Python ports of World Model conformance/runner.ts at 1742dec."""

from polytoken.meterless.world_model import WorldModel, decide, entity_id_from_name, normalize_name


OBSERVATIONS = [
    {"externalId": "a1", "title": "Fed holds rates", "at": "2026-05-17T14:00:00.000Z",
     "source": {"kind": "rss", "at": "2026-05-17T14:00:00.000Z"},
     "entities": [{"type": "person", "name": "Jerome Powell"}]},
    {"externalId": "a2", "title": "Powell signals patience", "at": "2026-05-17T16:30:00.000Z",
     "source": {"kind": "rss", "at": "2026-05-17T16:30:00.000Z"},
     "entities": [{"type": "person", "name": "Jerome Powell"}]},
]


def test_sid_001_diacritics_and_nbsp():
    assert normalize_name("José\u00a0\u00a0García") == normalize_name("Jose Garcia")
    assert entity_id_from_name("person", "José García") == entity_id_from_name("person", "jose garcia")


def test_sid_002_distinct_names_and_types():
    assert entity_id_from_name("org", "Acme Corp") != entity_id_from_name("org", "Acme Corporation")
    assert entity_id_from_name("person", "x") != entity_id_from_name("org", "x")


def test_band_001_merge_boundaries():
    assert [decide(v) for v in (.85, .84, .82, .81)] == ["auto-merge", "review", "review", "new"]


def test_prov_001_missing_provenance_rejected(tmp_path):
    with WorldModel(tmp_path / "world.sqlite") as world:
        try:
            world.upsert_entity(type="person", name="No Provenance")
        except ValueError:
            rejected = True
        else:
            rejected = False
        assert rejected


def test_idem_001_same_batch_empty_diff(tmp_path):
    with WorldModel(tmp_path / "world.sqlite") as world:
        world.ingest(OBSERVATIONS)
        shape = world.state_shape_canonical()
        result = world.ingest(OBSERVATIONS)
        assert result["changed"] is False
        assert world.state_shape_canonical() == shape


def test_idem_002_mutated_batch_changes_shape(tmp_path):
    with WorldModel(tmp_path / "world.sqlite") as world:
        world.ingest(OBSERVATIONS)
        shape = world.state_shape_canonical()
        mutated = [{**OBSERVATIONS[0], "title": OBSERVATIONS[0]["title"] + " (edited)"}, OBSERVATIONS[1]]
        assert world.ingest(mutated)["changed"] is True
        assert world.state_shape_canonical() != shape


def test_bitemp_001_superseding_edge_and_point_in_time(tmp_path):
    def at(value):
        return {"kind": "manual", "at": value}
    with WorldModel(tmp_path / "world.sqlite") as world:
        world.upsert_entity(type="player", external_key={"system": "g", "id": "p1"}, source=at("2087-01-01T00:00:00.000Z"))
        world.upsert_entity(type="team", external_key={"system": "g", "id": "a"}, source=at("2087-01-01T00:00:00.000Z"))
        world.upsert_entity(type="team", external_key={"system": "g", "id": "b"}, source=at("2088-03-01T00:00:00.000Z"))
        world.relate(from_id="player:g:p1", type="plays-for", to_id="team:g:a",
                     valid_from="2087-01-01T00:00:00.000Z", source=at("2087-01-01T00:00:00.000Z"))
        world.relate(from_id="player:g:p1", type="plays-for", to_id="team:g:b",
                     valid_from="2088-03-01T00:00:00.000Z", source=at("2088-03-01T00:00:00.000Z"))
        assert [e["id"] for e in world.neighbors_of("player:g:p1", via="plays-for")] == ["team:g:b"]
        assert [e["id"] for e in world.neighbors_of("player:g:p1", via="plays-for", at="2087-06-01T00:00:00.000Z")] == ["team:g:a"]


def test_audit_001_every_mutation_audited_in_order(tmp_path):
    with WorldModel(tmp_path / "world.sqlite") as world:
        world.upsert_entity(type="x", name="Audit One", source={"kind": "manual", "at": "2026-01-01T00:00:00.000Z"})
        world.upsert_entity(type="x", name="Audit Two", source={"kind": "manual", "at": "2026-01-02T00:00:00.000Z"})
        audit = world.audit()
        assert len(audit) >= 2
        assert all(audit[i]["seq"] > audit[i-1]["seq"] for i in range(1, len(audit)))


def test_indic_stable_ids_keep_vowel_signs_and_virama():
    for a, b in (("दवा", "दव"), ("किताब", "कताब"), ("రేషన్ కార్డు", "రషన కరడ")):
        assert entity_id_from_name("term", a) != entity_id_from_name("term", b)
