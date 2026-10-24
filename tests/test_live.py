"""Opt-in checks use the same production probe functions as polytoken doctor."""

import pytest

from polytoken.cli import check_nvidia, check_tokenizer, check_zetaris
from polytoken.config import load_settings
from polytoken.logs import JsonlLogger

pytestmark = pytest.mark.live


@pytest.fixture
def live_settings():
    return load_settings()


@pytest.fixture
def live_logger(live_settings):
    return JsonlLogger(secrets=live_settings.secrets)


def test_zetaris(live_settings, live_logger):
    assert check_zetaris(live_settings, live_logger)


def test_nvidia(live_settings, live_logger):
    assert check_nvidia(live_settings, live_logger)


def test_tokenizer(live_settings, live_logger):
    assert check_tokenizer(live_settings, live_logger)
