"""Thin cached access to the declared, separately installed indictax harness."""

from functools import lru_cache

from indictax.tok import load_tokenizer


@lru_cache(maxsize=None)
def _tokenizer(spec: str):
    return load_tokenizer(spec)


def count(spec: str, text: str) -> int:
    return len(_tokenizer(spec).encode(text))


def fragment_rate(spec: str, text: str) -> float:
    tokenizer = _tokenizer(spec)
    ids = tokenizer.encode(text)
    return sum(tokenizer.is_fragment(tid) for tid in ids) / len(ids) if ids else 0.0
