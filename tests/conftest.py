from __future__ import annotations

import socket

import pytest

from polytoken.config import load_settings
from polytoken.logs import JsonlLogger


def pytest_collection_modifyitems(config, items):
    # Merely running pytest never reaches the network. Explicit -m live opts in.
    expression = config.option.markexpr
    if expression and "live" in expression and "not live" not in expression:
        return
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(pytest.mark.skip(reason="live checks require explicit -m live"))


@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return

    def blocked(*args, **kwargs):
        raise AssertionError("Network access is disabled in offline tests")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture
def settings(tmp_path):
    return load_settings(tmp_path / "missing.env", environ={
        "NVIDIA_API_KEY": "fixture-nvidia-secret",
        "NVIDIA_BASE_URL": "https://nvidia.example/v1",
        "AGENT_MODEL": "fixture/nemotron",
        "ZETARIS_URL": "http://zetaris.example",
        "ZETARIS_USER": "fixture-user",
        "ZETARIS_PASSWORD": "fixture-zetaris-secret",
    })


@pytest.fixture
def logger(tmp_path, settings):
    return JsonlLogger(tmp_path / "logs", run_id="fixture-run", secrets=settings.secrets)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()
