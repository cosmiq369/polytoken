import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def test_probe_records_success_failure_and_no_system(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('probe', Path(__file__).resolve().parents[1] / 'scripts/probe_hosted.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(tmp_path)
    path = tmp_path / 'data/reference/nvidia_hosted.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'families': {'ok': ['ok/model'], 'bad': ['bad/model']}}))
    monkeypatch.setattr(module, 'load_settings', lambda: SimpleNamespace(secrets=[], nvidia_base_url='https://example.test'))
    class SQL:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def query(self, query):
            return [{'system_prompt_native': 'Telugu policy'}] if 'config' in query else [{'role': 'user', 'chat_id': 'c1', 'text_native': 'question'}]
    class Generate(SQL):
        def generate(self, prompt, **kwargs):
            if kwargs['model'] == 'bad/model':
                raise RuntimeError('HTTP 404')
            kwargs['on_stream']('OK')
            return dict(model=kwargs['model'], text='OK', usage={'completion_tokens': 1}, ttft_s=.01, latency_s=.02)
    monkeypatch.setattr(module, 'ZetarisClient', SQL)
    monkeypatch.setattr(module, 'NvidiaGenerator', Generate)
    module.main()
    result = json.loads(path.read_text())['serving_verification']
    assert result['ok/model']['served'] is True
    assert result['ok/model']['probe']['long']['ok'] == 3
    assert result['bad/model']['served'] is False
    rows = [json.loads(line) for line in Path('logs/sample/hosted_probe.jsonl').read_text().splitlines()]
    assert len(rows) == 18
    assert sum(r['no_system'] for r in rows) == 6
