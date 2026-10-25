"""The foundation doctor. Service probes share the production clients and logs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

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
    command = subparsers.add_parser("engines-demo", help="demonstrate Meterless accounting and evidence storage")
    command.add_argument("--live", action="store_true")
    command.add_argument("--env-file", default=None)
    command = subparsers.add_parser("investigate", help="run a bounded live investigation")
    command.add_argument("--company", choices=("samudra", "swara"), required=True)
    command.add_argument("--question", default="Explain the workload cost and latency and test a fix.")
    command.add_argument("--monthly-chats", type=int)
    command.add_argument("--latency-target-s", type=float)
    command.add_argument("--env-file", default=".env")
    command.add_argument("--sample-suffix", default="", help="suffix for archived events and report, e.g. v2")
    command = subparsers.add_parser("serve", help="start the API and registered price endpoint")
    command.add_argument("--port", type=int, default=8000)
    command = subparsers.add_parser("score", help="score archived complete runs against the contract, offline")
    command.add_argument("--sample-dir", default="logs/sample")
    command.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    if args.command == "score":
        from .score import score
        for row in score(args.sample_dir, args.output):
            print(row['company'] + ': ' + row.get('top_finding', {}).get('status', row.get('status', 'unavailable')))
        return 0
    if args.command == "serve":
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(), host="127.0.0.1", port=args.port)
        return 0
    if args.command == "investigate":
        import json
        from .agent.runtime import investigate
        from .reference_server import ensure_reference_server, ensure_reference_table
        logger = JsonlLogger(env_file=args.env_file)
        server = ensure_reference_server(logger)
        try:
            with ZetarisClient(load_settings(args.env_file), logger=logger) as client:
                ensure_reference_table(client, logger)
            report, events = investigate(args.company, question=args.question,
                monthly_chats=args.monthly_chats, latency_target_s=args.latency_target_s,
                env_file=args.env_file,
                event_sink=lambda row: print(f"{row['step']}: {row['event']} — {row['why']}", flush=True)
                    if row['event'] in ('step_started', 'done') else None)
            sample = Path('logs/sample')
            sample.mkdir(parents=True, exist_ok=True)
            stem = sample / ('agent_' + args.company + ('_' + args.sample_suffix if args.sample_suffix else ''))
            # Never overwrite a previous run: append all events and archive old reports.
            with stem.with_suffix('.jsonl').open('a') as handle:
                for row in events:
                    handle.write(json.dumps(row, ensure_ascii=False) + '\n')
            destination = stem.with_name(stem.name + '_report.json')
            if destination.exists():
                previous = json.loads(destination.read_text())
                (sample / (stem.name + '_' + previous['id'] + '_report.json')).write_text(destination.read_text())
            destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print(f"{report['status']}: {destination}")
            return 0
        finally:
            if server:
                server.shutdown()
                server.server_close()
    if args.command == "engines-demo":
        return engines_demo(live=args.live, env_file=args.env_file)
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
            print("Token measurements verified; use investigate for estimates from verified prices and live experiments.")
            return int(any(b['status'] == 'failed' for b in batches) or not any(b['status'] == 'completed' for b in batches))
        except Exception as exc:
            logger.write("measurements", "run_failed", ok=False, error_class=type(exc).__name__)
            print(f"Measurement failed: {logger.redact(str(exc))[:600]}")
            return 1
    return doctor(args.env_file)


def engines_demo(*, live=False, env_file=None) -> int:
    from .meterless.evidence import ingest_federation_sample
    from .meterless.markovian import Markovian
    from .meterless.world_model import WorldModel

    from .paths import ROOT
    root = ROOT
    if live:
        source_env = Path(env_file).resolve() if env_file else root / ".env"
        settings = load_settings(env_file=source_env)
        logger = JsonlLogger(directory=root / "logs" / "sample", env_file=source_env, secrets=settings.secrets)
        model_logger = JsonlLogger(directory=root / "logs", env_file=source_env, secrets=settings.secrets)
        with NvidiaGenerator(settings, logger=model_logger, max_tokens=256) as model:
            generator = model.generate
            run = Markovian({"maxChunks": 3, "carryoverTokens": 128}, logger=logger,
                            log_stream="meterless_markovian_live").run(
                "Explain in exactly three chunks why Telugu and Hindi token counts can differ from English. "
                "End chunks 1 and 2 with [STATE_CHECKPOINT] followed by concise state; end chunk 3 "
                "with [TASK_COMPLETE]. State that cost requires a verified price.", generator, reflect=False)
        if run["tokenLabel"] != "measured":
            raise RuntimeError("live provider did not return measured usage")
    else:
        calls = 0
        def fake(_prompt):
            nonlocal calls
            calls += 1
            marker = "[TASK_COMPLETE]" if calls == 4 else f"[STATE_CHECKPOINT]\nCompleted {calls}; remaining {4 - calls}"
            return {"text": f"Step {calls}: compare paired token evidence. " * 80 + marker}
        run = Markovian({"maxChunks": 4}).run("Demonstrate bounded token accounting", fake, reflect=False)
    print(f"Markovian: {len(run['chunks'])} chunks, {run['status']}, tokenLabel={run['tokenLabel']}")
    print(f"Projected savings: {run['projected']['savings']} tokens ({run['projected']['efficiency'] * 100:.2f}%)")
    print(f"Signed savings: {run['actual']['net_tokens']} tokens ({run['actual']['net_percent']:.2f}%)")
    with TemporaryDirectory() as directory:
        with WorldModel(Path(directory) / "world.sqlite") as world:
            sample = root / "logs" / "sample" / "federation.jsonl"
            event_ids = ingest_federation_sample(world, sample)
            counts = world.counts()
            print(f"World Model: {counts['entities']} entities, {counts['events']} events, {counts['audit']} audit entries; {len(event_ids)} federation rows")
    return 0
