"""Price loading and a fail-closed money calculation; no prices are invented."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit


class PriceUnavailable(ValueError):
    pass


FIELDS = {"model", "provider", "tokenizer_spec", "input_per_mtok_usd",
          "output_per_mtok_usd", "source_url", "fetched_at", "verified"}


def validate_price(row: dict) -> dict:
    if not isinstance(row, dict) or set(row) != FIELDS:
        raise ValueError("Price entry must contain exactly the declared schema fields")
    for name in ("model", "provider", "tokenizer_spec", "source_url", "fetched_at"):
        if not isinstance(row[name], str) or not row[name].strip():
            raise ValueError(f"Price {name} must be a nonempty string")
    if type(row["verified"]) is not bool:
        raise ValueError("Price verified must be a boolean")
    for name in ("input_per_mtok_usd", "output_per_mtok_usd"):
        value = row[name]
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (float, int, Decimal)):
                raise ValueError(f"Price {name} must be a nonnegative finite number or null")
            number = Decimal(str(value))
            if not number.is_finite() or number < 0:
                raise ValueError(f"Price {name} must be a nonnegative finite number or null")
    if urlsplit(row["source_url"]).scheme not in ("http", "https"):
        raise ValueError("Price source_url must be HTTP(S)")
    if datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("Price fetched_at must include a timezone")
    return row


def load_prices(path: str | Path) -> list[dict]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Prices must be a JSON list")
    validated = [validate_price(row) for row in rows]
    keys = [(row["provider"], row["model"]) for row in validated]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate provider/model price entries")
    return validated


def cost_usd(entry: dict | None, input_tokens: int, output_tokens: int) -> Decimal:
    if entry is None or entry.get("verified") is not True:
        raise PriceUnavailable("Money unavailable: a verified price entry is required")
    if any(entry.get(name) is None for name in ("input_per_mtok_usd", "output_per_mtok_usd")):
        raise PriceUnavailable("Money unavailable: input and output prices are both required")
    validate_price(entry)
    if any(type(value) is not int or value < 0 for value in (input_tokens, output_tokens)):
        raise ValueError("Token counts must be nonnegative integers")
    return (Decimal(str(entry["input_per_mtok_usd"])) * input_tokens
            + Decimal(str(entry["output_per_mtok_usd"])) * output_tokens) / Decimal(1_000_000)
