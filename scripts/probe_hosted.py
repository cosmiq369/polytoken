#!/usr/bin/env python3
"""Probe actual streaming service, independently of model-list advertising."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median
import argparse
import hashlib
import json
import time

from polytoken.config import load_settings
from polytoken.llm import NvidiaGenerator
from polytoken.logs import JsonlLogger
from polytoken.tools import now
from polytoken.zetaris import ZetarisClient


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--model')
    parser.add_argument('--reasoning-effort', choices=['low', 'medium', 'high'])
    args = parser.parse_args(argv)
    settings = load_settings()
    logger = JsonlLogger(secrets=settings.secrets)
    sample = JsonlLogger('logs/sample', run_id=logger.run_id, secrets=settings.secrets)
    path = Path('data/reference/nvidia_hosted.json')
    catalogue = json.loads(path.read_text())
    with ZetarisClient(settings, logger=logger) as sql:
        config = sql.query('SELECT * FROM company_systems.samudra__bot_config')[0]
        chats = sql.query('SELECT * FROM company_systems.samudra__chats ORDER BY chat_id, turn')
    chat = next(r for r in chats if r['role'] == 'user')
    jobs = [(m, variant, attempt) for models in catalogue['families'].values() for m in models
            for variant in ('short', 'long') for attempt in range(1, 4) if not args.model or m == args.model]
    rows = []
    with NvidiaGenerator(settings, logger=logger, max_tokens=200, timeout_s=120.) as generator:
        def probe(model, variant, attempt, no_system=False):
            system = 'Answer briefly.' if variant == 'short' else config['system_prompt_native']
            user = 'Reply with OK.' if variant == 'short' else chat['text_native']
            if no_system:
                user = system + '\n' + user
                system = None
            start = time.monotonic()
            at = now()
            first = []
            try:
                result = generator.generate(user, model=model, system_prompt=system, temperature=0,
                    on_stream=lambda text: first.append(time.monotonic()) if text and not first else None,
                    max_retries=0, reasoning_effort=args.reasoning_effort)
                result = {**result, 'ok': bool(result['text'].strip()), 'status': 200}
            except Exception as exc:
                message = str(exc)
                result = {'ok': False, 'status': 404 if 'HTTP 404' in message else 'error',
                          'error_class': type(exc).__name__, 'reason': logger.redact(message), 'usage': {}}
            result.pop('model', None)
            row = dict(model=model, variant=variant, attempt=attempt, no_system=no_system,
                source=settings.nvidia_base_url + '/chat/completions',
                query={'system_sha256': hashlib.sha256((system or '').encode()).hexdigest(), 'chat_id': chat['chat_id'] if variant == 'long' else None,
                       'system_prompt': system, 'user': user, 'max_tokens': 200, 'stream': True, 'reasoning_effort': args.reasoning_effort},
                time_window={'start': at, 'end': now()}, fetched_at=now(),
                total_s=time.monotonic() - start, **{**result, 'ttft_s': (first[0] - start) if first else None})
            sample.write('hosted_probe', 'serving_probe', **row)
            print(model, variant, attempt, 'no_system='+str(no_system), result['status'], 'ok='+str(result['ok']), flush=True)
            return row
        with ThreadPoolExecutor(max_workers=4) as pool:
            pending = [pool.submit(probe, *job) for job in jobs]
            for future in as_completed(pending):
                row = future.result()
                rows.append(row)
                if row['status'] == 404:
                    rows.append(pool.submit(probe, row['model'], row['variant'], row['attempt'], True).result())
    verified = catalogue.get('serving_verification', {})
    for model in sorted({r['model'] for r in rows}):
        group = [r for r in rows if r['model'] == model]
        # Production currently supplies system roles; no-system-only successes are
        # diagnostic, not permission to send a known-unsupported request shape.
        verified[model] = {'serving_verified_at': now(), 'served': any(r['ok'] and not r['no_system'] for r in group),
            'probe': {v: {'ok': sum(r['ok'] for r in group if r['variant'] == v and not r['no_system']),
                         'tries': 3, 'ttft_median_s': median(vals) if (vals := [r['ttft_s'] for r in group if r['variant'] == v and r['ok'] and not r['no_system'] and r['ttft_s'] is not None]) else None}
                      for v in ('short', 'long')},
            'probe_run_id': logger.run_id,
            'generation_options': {'reasoning_effort': args.reasoning_effort} if args.reasoning_effort else {},
            'no_system_successes': sum(r['ok'] for r in group if r['no_system']), 'evidence': 'logs/sample/hosted_probe.jsonl'}
    catalogue['serving_verification'] = verified
    catalogue['note'] = 'Production intersects catalogue listing with successful streamed serving probes. Failed models are excluded.'
    path.write_text(json.dumps(catalogue, indent=2) + '\n')


if __name__ == '__main__':
    main()
