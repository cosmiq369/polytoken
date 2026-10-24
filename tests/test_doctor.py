import json
from unittest.mock import Mock

import pytest

from polytoken import cli
from polytoken.config import ConfigError


def test_doctor_pass_output_and_audit(settings, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda path: settings)
    for name in ("check_zetaris", "check_nvidia", "check_tokenizer"):
        monkeypatch.setattr(cli, name, lambda settings, logger, name=name: name + " passed")
    assert cli.main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert sum(line.startswith("  PASS  ") for line in output.splitlines()) == 4
    assert "All 4 checks passed." in output
    assert settings.nvidia_api_key not in output
    assert settings.zetaris_password not in output
    rows = [json.loads(line) for line in (tmp_path / "logs/doctor.jsonl").read_text().splitlines()]
    assert len(rows) == 4
    assert len({r["run_id"] for r in rows}) == 1


def test_doctor_reports_failures_and_nonzero(settings, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda path: settings)
    monkeypatch.setattr(cli, "check_zetaris", Mock(side_effect=OSError(settings.zetaris_password)))
    monkeypatch.setattr(cli, "check_nvidia", Mock(return_value="NVIDIA passed"))
    monkeypatch.setattr(cli, "check_tokenizer", Mock(return_value="tokenizer passed"))
    assert cli.doctor() == 1
    output = capsys.readouterr().out
    assert "FAIL  Zetaris: OSError" in output
    assert "1 of 4 checks failed." in output
    assert settings.zetaris_password not in output


def test_missing_config_does_not_call_services(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_settings", Mock(side_effect=ConfigError("Missing required environment variables: AGENT_MODEL")))
    zetaris = Mock()
    nvidia = Mock()
    monkeypatch.setattr(cli, "check_zetaris", zetaris)
    monkeypatch.setattr(cli, "check_nvidia", nvidia)
    monkeypatch.setattr(cli, "check_tokenizer", Mock(return_value="tokenizer passed"))
    assert cli.doctor() == 1
    zetaris.assert_not_called()
    nvidia.assert_not_called()
    assert "AGENT_MODEL" in capsys.readouterr().out


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
