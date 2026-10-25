"""Audit every reachable Git blob without printing configured values."""
import json
import gzip
from pathlib import Path
import re
import subprocess
from dotenv import dotenv_values


def scan():
    configured = {k: v for k, v in dotenv_values('.env').items() if v}
    sensitive = {k: v for k, v in configured.items() if any(s in k for s in ('KEY', 'TOKEN', 'PASSWORD'))}
    names = list(dotenv_values('.env.example'))
    counts = {k: 0 for k in names}
    public_config_counts = {k: 0 for k in configured if k not in sensitive}
    hits, patterns, literal_references, oversized = [], [], [], []
    objects = subprocess.check_output(['git', 'rev-list', '--objects', '--all'], text=True).splitlines()
    for line in objects:
        oid, _, path = line.partition(' ')
        if not path or subprocess.check_output(['git', 'cat-file', '-t', oid], text=True).strip() != 'blob':
            continue
        data = subprocess.check_output(['git', 'cat-file', 'blob', oid])
        if path.endswith('.gz'):
            data = gzip.decompress(data)
        for key in names:
            counts[key] += int(key.encode() in data)
        for key, value in sensitive.items():
            if value.encode() in data:
                hits.append(dict(object=oid, path=path, variable=key))
        for key in public_config_counts:
            public_config_counts[key] += int(configured[key].encode() in data)
        if not path.startswith('docs/prompts/'):
            matches = list(re.finditer(rb'nvapi' + rb'-[A-Za-z0-9_-]*', data))
            if any(len(m.group()) > 6 for m in matches):
                patterns.append(dict(object=oid, path=path))
            elif matches:
                literal_references.append(dict(object=oid, path=path, classification='Bare search-pattern reference; no credential suffix'))
        if len(data) > 5_000_000 and not path.endswith('.gz'):
            oversized.append(dict(object=oid, path=path, bytes=len(data)))
    worktree_hits = []
    for name in subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], text=True).splitlines():
        path = Path(name)
        if not path.is_file():
            continue
        data = path.read_bytes()
        if path.suffix == '.gz':
            data = gzip.decompress(data)
        for key, value in sensitive.items():
            if value.encode() in data:
                worktree_hits.append(dict(path=name, variable=key))
        if not name.startswith('docs/prompts/') and re.search(rb'nvapi' + rb'-[A-Za-z0-9_-]+', data):
            worktree_hits.append(dict(path=name, pattern='provider credential prefix with suffix'))
    result = dict(event='history_secret_scan', scope='All reachable branches and all historical blobs',
                  configured_secret_value_hits=hits, worktree_secret_hits=worktree_hits, secret_variables=list(sensitive),
                  public_configuration_value_blob_counts=public_config_counts,
                  variable_name_blob_counts=counts, provider_prefix_hits=patterns, bare_pattern_references=literal_references,
                  pattern_exclusion='docs/prompts/ only; configured secret values have no path exclusions',
                  large_historical_blobs=oversized, scanned_objects=len(objects),
                  interpretation='Public URLs, model names, rate limits and usernames are configuration references, not credentials.')
    with Path('logs/sample/ship_secret_scan.jsonl').open('a') as handle:
        handle.write(json.dumps(result) + '\n')
    print(json.dumps(result, indent=2))
    return int(bool(hits or patterns or worktree_hits))

if __name__ == '__main__':
    raise SystemExit(scan())
