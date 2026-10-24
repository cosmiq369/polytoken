"""Typed environment settings. Errors name variables, never their values."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from dotenv import dotenv_values, load_dotenv

REQUIRED_VARIABLES = (
    "NVIDIA_API_KEY", "NVIDIA_BASE_URL", "AGENT_MODEL",
    "ZETARIS_URL", "ZETARIS_USER", "ZETARIS_PASSWORD",
)


class ConfigError(ValueError):
    """Missing or invalid environment configuration."""


@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str = field(repr=False)
    nvidia_base_url: str
    agent_model: str
    zetaris_url: str
    zetaris_user: str = field(repr=False)
    zetaris_password: str = field(repr=False)
    nvidia_rpm: float = 40.0
    hf_token: str | None = field(default=None, repr=False)

    @property
    def secrets(self) -> tuple[str, ...]:
        return tuple(v for v in (
            self.nvidia_api_key, self.zetaris_password, self.hf_token,
        ) if v)


def load_settings(
    env_file: str | Path = ".env", *, environ: Mapping[str, str] | None = None,
) -> Settings:
    """Load .env without interpolation; existing process variables take precedence.

    An explicit environ mapping isolates configuration in offline tests.
    HF_TOKEN is also made available to indictax when loading the real environment.
    """
    if environ is None:
        load_dotenv(env_file, override=False, interpolate=False)
        values = dict(os.environ)
    else:
        values = {**dotenv_values(env_file, interpolate=False), **environ}
    missing = [name for name in REQUIRED_VARIABLES if not (values.get(name) or "").strip()]
    if missing:
        raise ConfigError("Missing required environment variables: " + ", ".join(missing))
    for name in ("NVIDIA_BASE_URL", "ZETARIS_URL"):
        try:
            url = urlsplit(values[name])
            valid = (url.scheme in ("http", "https") and bool(url.hostname)
                     and not url.username and not url.password and not url.query and not url.fragment)
            _ = url.port
        except ValueError:
            valid = False
        if not valid:
            raise ConfigError(f"Invalid {name}: expected an HTTP(S) URL without credentials, query or fragment")
    try:
        rpm = float(values.get("NVIDIA_RPM") or 40)
        if not math.isfinite(rpm) or rpm <= 0:
            raise ValueError
    except (ValueError, TypeError):
        raise ConfigError("Invalid NVIDIA_RPM: expected a positive finite number") from None
    return Settings(
        nvidia_api_key=values["NVIDIA_API_KEY"],
        nvidia_base_url=values["NVIDIA_BASE_URL"].rstrip("/"),
        agent_model=values["AGENT_MODEL"],
        zetaris_url=values["ZETARIS_URL"].rstrip("/"),
        zetaris_user=values["ZETARIS_USER"],
        zetaris_password=values["ZETARIS_PASSWORD"],
        nvidia_rpm=rpm,
        hf_token=values.get("HF_TOKEN") or None,
    )
