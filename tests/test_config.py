import pytest

from polytoken.config import ConfigError, REQUIRED_VARIABLES, load_settings


def env_values():
    return {
        "NVIDIA_API_KEY": "private-nvidia-key", "NVIDIA_BASE_URL": "https://example.com/v1",
        "AGENT_MODEL": "test/model", "ZETARIS_URL": "http://localhost:3000",
        "ZETARIS_USER": "admin", "ZETARIS_PASSWORD": "private-password",
    }


@pytest.mark.parametrize("name", REQUIRED_VARIABLES)
def test_missing_variable_names_only(tmp_path, name):
    env = env_values()
    del env[name]
    with pytest.raises(ConfigError, match=name) as exc:
        load_settings(tmp_path / "absent", environ=env)
    assert "private" not in str(exc.value)


def test_dotenv_precedence_and_secret_repr(tmp_path):
    path = tmp_path / ".env"
    path.write_text("\n".join(f'{k}="{v}"' for k, v in env_values().items()))
    settings = load_settings(path, environ={"AGENT_MODEL": "override"})
    assert settings.agent_model == "override"
    assert settings.nvidia_rpm == 40
    assert "private" not in repr(settings)


@pytest.mark.parametrize("rpm", ["0", "-1", "nan", "inf", "garbage"])
def test_invalid_rpm(tmp_path, rpm):
    with pytest.raises(ConfigError, match="NVIDIA_RPM"):
        load_settings(tmp_path / "absent", environ={**env_values(), "NVIDIA_RPM": rpm})


@pytest.mark.parametrize("url", ["ftp://server", "http://", "http://user:secret@server", "https://server?key=secret"])
def test_invalid_url_never_echoes_value(tmp_path, url):
    with pytest.raises(ConfigError, match="NVIDIA_BASE_URL") as exc:
        load_settings(tmp_path / "absent", environ={**env_values(), "NVIDIA_BASE_URL": url})
    assert "secret" not in str(exc.value)
