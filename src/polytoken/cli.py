"""The foundation doctor. Service probes share the production clients and logs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .config import ConfigError, REQUIRED_VARIABLES, Settings, load_settings
from .llm import NvidiaGenerator
from .logs import JsonlLogger
from .zetaris import ZetarisClient

TOKENIZER_SPEC = "unsloth/gemma-3-4b-it"
TOKENIZER_SENTENCE = "తెలుగు భాష అందమైనది."


def check_zetaris(settings: Settings, logger: JsonlLogger) -> str:
    with ZetarisClient(settings, logger=logger) as client:
        client.login()
        rows = client.query("select 7 as seven")
    if len(rows) != 1 or rows[0].get("seven") not in (7, "7"):
        raise RuntimeError("select 7 as seven did not return 7")
    return "Zetaris: login and select 7 as seven returned 7"


def check_nvidia(settings: Settings, logger: JsonlLogger) -> str:
    with NvidiaGenerator(settings, logger=logger, max_tokens=8) as generator:
        generator.generate("Reply with OK.")
    return "NVIDIA: completion succeeded through generator (max_tokens=8)"


def check_tokenizer(settings: Settings | None, logger: JsonlLogger) -> str:
    import indictax
    from .tokens import count

    value = count(TOKENIZER_SPEC, TOKENIZER_SENTENCE)
    if value <= 0:
        raise RuntimeError("Tokenizer returned no tokens for the Telugu probe")
    logger.write("doctor", "tokenizer_observation", source=TOKENIZER_SPEC,
                 query={"operation": "count", "text": TOKENIZER_SENTENCE},
                 fetched_at=datetime.now(timezone.utc).isoformat(),
                 token_count=value, ok=True)
    return f"indictax: {TOKENIZER_SPEC} loaded; Telugu sentence = {value} tokens"


def doctor(env_file=".env") -> int:
    print("PolyToken -- doctor")
    logger = JsonlLogger(env_file=env_file)
    settings = None
    passed, failed = 0, 0
    try:
        settings = load_settings(env_file)
        logger.add_secrets(*settings.secrets)
        detail = "environment: " + ", ".join(REQUIRED_VARIABLES)
        print(f"  PASS  {detail}")
        logger.write("doctor", "check", check="environment", ok=True)
        passed += 1
    except ConfigError as exc:
        print(f"  FAIL  environment: {exc}")
        logger.write("doctor", "check", check="environment", ok=False, error_class=type(exc).__name__)
        failed += 1

    for name, probe in (("Zetaris", check_zetaris), ("NVIDIA", check_nvidia), ("indictax", check_tokenizer)):
        try:
            if settings is None and name != "indictax":
                raise RuntimeError("requires valid environment settings")
            detail = probe(settings, logger)
            print(f"  PASS  {detail}")
            logger.write("doctor", "check", check=name, ok=True)
            passed += 1
        except Exception as exc:
            # Other libraries can put URLs, credentials or response text in errors.
            # Only known-safe client errors and our validation messages are printed.
            from .llm import LLMError
            from .zetaris import ZetarisError

            detail = str(exc) if isinstance(exc, (LLMError, ZetarisError)) or type(exc) is RuntimeError else type(exc).__name__
            detail = logger.redact(detail)
            print(f"  FAIL  {name}: {detail}")
            logger.write("doctor", "check", check=name, ok=False, error_class=type(exc).__name__)
            failed += 1
    if failed:
        print(f"{failed} of {passed + failed} checks failed.")
    else:
        print(f"All {passed} checks passed.")
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="polytoken")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("doctor", help="check configuration and the three live dependencies")
    command.add_argument("--env-file", default=".env")
    command = subparsers.add_parser("measure", help="measure paired demo text through all configured tokenizers")
    command.add_argument("--company", choices=("samudra", "swara", "all"), required=True)
    command.add_argument("--env-file", default=".env")
    args = parser.parse_args(argv)
    if args.command == "measure":
        from .measure import measure
        from .measurement_report import verify_and_save
        logger = JsonlLogger(env_file=args.env_file)
        try:
            settings = load_settings(args.env_file)
            logger.add_secrets(*settings.secrets)
            batches = measure(settings, args.company, logger)
            if args.company == "all":
                with ZetarisClient(settings, logger=logger) as client:
                    rows, _ = verify_and_save(client, logger)
                print(f"Federation verified: {len(rows)} company/tokenizer/part groups; evidence in logs/sample/.")
            print("Money unavailable: no verified prices have been supplied; token shares do not establish cost or latency.")
            return int(any(b['status'] == 'failed' for b in batches) or not any(b['status'] == 'completed' for b in batches))
        except Exception as exc:
            logger.write("measurements", "run_failed", ok=False, error_class=type(exc).__name__)
            print(f"Measurement failed: {logger.redact(str(exc))[:600]}")
            return 1
    return doctor(args.env_file)
