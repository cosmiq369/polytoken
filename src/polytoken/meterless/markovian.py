"""Bounded chunk execution and auditable token economics."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Callable

from polytoken.logs import JsonlLogger


class ConfigValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ChunkConfig:
    chunkSize: int = 8000
    maxChunks: int = 24
    carryoverTokens: int = 800
    overlapTokens: int = 0

    def __post_init__(self):
        for key, low, high in (("chunkSize", 1000, 128000), ("maxChunks", 1, 32),
                               ("carryoverTokens", 128, 32768), ("overlapTokens", 0, 4096)):
            value = getattr(self, key)
            if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
                raise ConfigValidationError(f"{key}={value} outside [{low}, {high}]")
        if self.overlapTokens:
            raise ConfigValidationError("overlapTokens must be zero")
        if self.chunkSize < 400 + self.carryoverTokens + 1200:
            raise ConfigValidationError("chunkSize must cover framingTokens + carryoverTokens + outputBudget")


def model_totals(n: int, *, F=400, G=200, S=300, O=1200, C=800) -> dict:
    if not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    naive = n * (F + G + S) + O * n * (n - 1) // 2
    markovian = n * (F + G + C + S)
    return {"naiveTotal": naive, "markovianTotal": markovian,
            "savings": naive - markovian, "efficiency": (naive - markovian) / naive}


def run_efficiency(chunks: list[dict], config: ChunkConfig | dict) -> dict:
    cfg = config if isinstance(config, ChunkConfig) else ChunkConfig(**config)
    total = sum(chunk["tokens"] for chunk in chunks)
    standard = prefix = 0
    for chunk in chunks:
        standard += prefix + chunk["tokens"]
        prefix += chunk["tokens"]
    cost = len(chunks) * cfg.carryoverTokens + total
    saved = max(0, standard - cost)
    return {"totalTokensUsed": total, "standardCost": standard,
            "markovianCost": cost, "tokensSaved": saved,
            "efficiencyPercent": saved / standard * 100 if standard else 0.0}


class Markovian:
    def __init__(self, chunk_config: ChunkConfig | dict | None = None, *,
                 logger: JsonlLogger | None = None, clock: Callable | None = None,
                 log_stream: str = "markovian"):
        self.config = chunk_config if isinstance(chunk_config, ChunkConfig) else ChunkConfig(**(chunk_config or {}))
        self.logger = logger or JsonlLogger()
        self.clock = clock
        self.log_stream = log_stream

    def run(self, goal: str, generator: Callable, *, reflect: bool = True) -> dict:
        chunks: list[dict] = []
        outputs: list[str] = []
        carryover = ""
        token_label = "measured"
        complete = False
        for index in range(1, self.config.maxChunks + 1):
            prompt = (f"GOAL: {goal}\nCHUNK {index}/{self.config.maxChunks}\n"
                      f"CARRYOVER: {carryover}\n"
                      "End a nonfinal chunk with [STATE_CHECKPOINT] and its concise state. "
                      "End the final chunk with [TASK_COMPLETE].")
            response = generator(prompt)
            if isinstance(response, str):
                response = {"text": response}
            raw = response["text"]
            complete = "[TASK_COMPLETE]" in raw
            state = raw.split("[STATE_CHECKPOINT]", 1)[1].strip() if "[STATE_CHECKPOINT]" in raw else ""
            cleaned = raw.split("[STATE_CHECKPOINT]", 1)[0].replace("[TASK_COMPLETE]", "").strip()
            carryover = state[:self.config.carryoverTokens * 4]
            usage = response.get("usage") or {}
            p = usage.get("prompt_tokens")
            c = usage.get("completion_tokens")
            if isinstance(p, int) and isinstance(c, int) and p >= 0 and c >= 0:
                tokens = p + c
            else:
                tokens = math.ceil((len(prompt) + len(raw)) / 4)
                token_label = "estimated"
            chunks.append({"id": index, "tokens": tokens, "carryover": carryover, "content": cleaned})
            outputs.append(cleaned)
            if complete:
                break
        status = "completed" if complete else "max_chunks"
        if reflect and complete:
            try:
                generator("Reflect briefly on the completed task without changing the result.")
            except Exception as exc:
                self.logger.write(self.log_stream, "reflection_failed", error_class=type(exc).__name__)
        cfg = asdict(self.config)
        projected = model_totals(len(chunks), C=self.config.carryoverTokens)
        actual = run_efficiency(chunks, self.config)
        run = {"status": status, "output": "\n\n".join(outputs), "chunks": chunks,
               "chunkConfig": cfg, "tokenLabel": token_label,
               "projected": projected, "actual": actual}
        self.logger.write(self.log_stream, "run", status=status, chunkConfig=cfg,
                          tokenLabel=token_label, projected=projected, actual=actual,
                          chunk_count=len(chunks))
        return run
