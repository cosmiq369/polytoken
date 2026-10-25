import json
from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from polytoken import cli, doctor


@pytest.fixture
def local_doctor(monkeypatch):
    distribution=Mock()
    distribution.read_text.return_value=json.dumps({'url':'https://github.com/cosmiq369/indic-inference-tax','vcs_info':{'commit_id':doctor.INDICTAX_PIN}})
    monkeypatch.setattr(doctor.importlib.metadata,'distribution',lambda name:distribution)
    monkeypatch.setattr(doctor.socket,'socket',lambda *args:nullcontext(Mock()))
    return distribution


def test_offline_doctor_without_env_or_network(tmp_path,monkeypatch,capsys,local_doctor):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('NVIDIA_API_KEY',raising=False)
    for name in ('check_zetaris','check_nvidia'):
        monkeypatch.setattr(cli,name,Mock(side_effect=AssertionError('No network probes offline')))
    assert cli.main(['doctor'])==0
    output=capsys.readouterr().out
    assert 'WARN' in output and 'Not probed in offline mode' in output
    rows=[json.loads(l) for l in (tmp_path/'logs/doctor.jsonl').read_text().splitlines()]
    assert {r['check'] for r in rows}>={'Python','SQLite','Meterless','Pinned indictax','Price source','App port','Disk space'}
    assert len({r['run_id'] for r in rows})==1
    cli.check_zetaris.assert_not_called();cli.check_nvidia.assert_not_called()


def test_doctor_bad_pin_and_missing_live_config(tmp_path,monkeypatch,capsys,local_doctor):
    monkeypatch.chdir(tmp_path);local_doctor.read_text.return_value='{}'
    monkeypatch.setattr(doctor,'load_settings',Mock(side_effect=ValueError('do-not-print-secret')))
    assert cli.main(['doctor','--live'])==1
    output=capsys.readouterr().out
    assert 'FAIL  Pinned indictax' in output and 'FAIL  Live configuration' in output
    assert 'do-not-print-secret' not in output


def test_doctor_port_failure_has_fix(tmp_path,monkeypatch,capsys,local_doctor):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(doctor.socket,'socket',Mock(side_effect=OSError('do-not-print-secret')))
    assert doctor.run_doctor()==1
    output=capsys.readouterr().out
    assert 'FAIL  App port' in output and '--port' in output and 'do-not-print-secret' not in output


def test_nvidia_probe_uses_generator_and_eight_token_cap(settings, logger, monkeypatch):
    generator = Mock()
    generator.__enter__ = Mock(return_value=generator)
    generator.__exit__ = Mock(return_value=False)
    constructor = Mock(return_value=generator)
    monkeypatch.setattr(cli, "NvidiaGenerator", constructor)
    cli.check_nvidia(settings, logger)
    assert constructor.call_args.kwargs["max_tokens"] == 8
    generator.generate.assert_called_once()


@pytest.mark.parametrize("records", [[], [{"seven": "8"}], [{"seven": "7"}, {"seven": "7"}]])
def test_zetaris_probe_rejects_wrong_results(settings, logger, monkeypatch, records):
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.query.return_value = records
    monkeypatch.setattr(cli, "ZetarisClient", Mock(return_value=client))
    with pytest.raises(RuntimeError, match="did not return 7"):
        cli.check_zetaris(settings, logger)


def test_tokenizer_probe_logs_real_count(settings, logger, monkeypatch):
    from polytoken import tokens

    monkeypatch.setattr(tokens, "count", Mock(return_value=9))
    assert "9 tokens" in cli.check_tokenizer(settings, logger)
    tokens.count.assert_called_once_with("unsloth/gemma-3-4b-it", cli.TOKENIZER_SENTENCE)
    row = json.loads((logger.directory / "doctor.jsonl").read_text().splitlines()[0])
    assert row["token_count"] == 9
    assert row["source"] == "unsloth/gemma-3-4b-it"
