"""Run in the fresh non-editable venv, from the clone; verify pin and five counts."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

import indictax
from indictax.tok import load_tokenizer
from polytoken.company_db import ROOT, jsonl
from polytoken.config import load_settings
from polytoken.logs import JsonlLogger

PIN = '0f61ec90ae49082d0fef7a21774e746fe17ed1cf'


def main():
    settings = load_settings()
    logger = JsonlLogger(ROOT/'logs/sample', secrets=settings.secrets)
    provenance = json.loads(importlib.metadata.distribution('indictax').read_text('direct_url.json'))
    assert provenance['vcs_info']['commit_id'] == PIN
    assert provenance['url'] == 'https://github.com/cosmiq369/indic-inference-tax'
    assert Path(indictax.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    assert not any((Path(p)/'indictax').is_dir() for p in sys.path if p and not Path(p).resolve().is_relative_to(Path(sys.prefix).resolve()))
    suite = subprocess.run([sys.executable,'-m','pytest','-q'],capture_output=True,text=True)
    logger.write('pin_check','offline_suite',ok=suite.returncode==0,command=f'{sys.executable} -m pytest -q',
                 output=suite.stdout+suite.stderr, pin=PIN, dependency=provenance)
    print(suite.stdout, flush=True)
    if suite.returncode:
        raise SystemExit(suite.returncode)
    snapshots = jsonl(ROOT/'logs/sample/v1_recomputed/measurement_snapshot.jsonl')
    checks = []
    selections = [('samudra','unsloth/Llama-3.2-3B-Instruct','system_prompt','te'),
                  ('samudra','Qwen/Qwen3-4B','user','en'),
                  ('samudra','unsloth/gemma-3-4b-it','assistant','te'),
                  ('swara','sarvamai/sarvam-1','assistant','hi'),
                  ('swara','microsoft/Phi-4-mini-instruct','user','hi')]
    for company,spec,part,language in selections:
        snapshot = next(r for r in snapshots if r['company']==company)
        count = next(r for r in snapshot['counts'] if r['tokenizer_spec']==spec and r['part']==part and r['lang_variant']==language)
        item = next(r for r in snapshot['inputs'] if (r['chat_id'],r['turn'],r['part'])==(count['chat_id'],int(count['turn']),part))
        text = item['en' if language=='en' else 'native']
        actual = len(load_tokenizer(spec).encode(text))
        check = dict(company=company,tokenizer_spec=spec,chat_id=item['chat_id'],turn=item['turn'],lang_variant=language,
                     text_sha256=hashlib.sha256(text.encode()).hexdigest(),stored_tokens=int(count['tokens']),
                     recomputed_tokens=actual,ok=actual==int(count['tokens']),source=count['source'],
                     query=count['source_query'],fetched_at=count['fetched_at'],
                     time_window={'start':count['time_window_start'],'end':count['time_window_end']})
        checks.append(check)
    ok = all(r['ok'] for r in checks)
    logger.write('pin_check','five_text_recount',ok=ok,pin=PIN,checks=checks,dependency=provenance,
                 python=sys.executable,indictax_file=indictax.__file__)
    print('Five stored-text counts match pinned harness:',ok)
    if not ok: raise SystemExit(1)


if __name__=='__main__':
    main()
