"""The public import diagnostic must agree with launch and never print source text."""
import csv
import io
import json
from pathlib import Path

import pytest

from polytoken.cli import main
from polytoken.launcher import MAX_BYTES, parse_sample, validate_sample_file

ROOT = Path(__file__).resolve().parents[1]


def test_template_cli_and_audit(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(['validate-sample', str(ROOT/'web/sample-template.jsonl'), '--language', 'te']) == 0
    output = capsys.readouterr().out
    rows = parse_sample('sample.jsonl', (ROOT/'web/sample-template.jsonl').read_text(), 'te')
    assert f"{len(rows)} rows / {len({r['chat_id'] for r in rows})} chats" in output
    assert 'pending' in output
    audit = (tmp_path/'logs/sample_validation.jsonl').read_text()
    for row in rows:
        assert row['text_native'] not in output + audit
        assert row['text_en'] not in output + audit
    assert json.loads(audit)['ok'] is True


@pytest.mark.parametrize('case', ['syntax', 'missing', 'turn', 'role', 'language', 'encoding', 'oversize', 'unreadable'])
def test_errors_do_not_echo_conversations(case, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = [dict(chat_id='x', turn=i, role=role, lang='te', text_native='PRIVATE_NATIVE_SENTINEL', text_en='PRIVATE_ENGLISH_SENTINEL')
            for i, role in [(1, 'user'), (2, 'assistant')]]
    if case == 'missing': del rows[0]['text_en']
    if case == 'turn': rows[1]['turn'] = 4
    if case == 'role': rows[1]['role'] = 'user'
    if case == 'language': rows[0]['lang'] = 'hi'
    data = '\n'.join(json.dumps(r) for r in rows).encode()
    if case == 'syntax': data += b'\nPRIVATE_BROKEN_JSON'
    if case == 'encoding': data = b'\xff'
    if case == 'oversize': data = b'x' * (MAX_BYTES+1)
    path=tmp_path/'sample.jsonl'
    if case != 'unreadable': path.write_bytes(data)
    assert main(['validate-sample', str(path), '--language', 'te']) == 1
    output=capsys.readouterr().out
    assert output.startswith('INVALID: ')
    assert 'PRIVATE' not in output + (tmp_path/'logs/sample_validation.jsonl').read_text()


def test_csv_matches_launcher_and_review_cannot_be_self_certified(tmp_path):
    rows = [dict(chat_id='x', turn=i, role=role, lang='hi', text_native='नमस्ते', text_en='Hello', review_status='reviewed')
            for i,role in [(1,'user'),(2,'assistant')]]
    output=io.StringIO(); writer=csv.DictWriter(output,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    path=tmp_path/'sample.csv';path.write_text(output.getvalue())
    assert validate_sample_file(path,'hi') == {'rows':2,'chats':1,'review_status':'pending'}
    assert all(r['review_status']=='pending' for r in parse_sample(path.name,path.read_text(),'hi'))


def test_add_data_skill_copies_match():
    assert (ROOT/'skills/polytoken-add-data/SKILL.md').read_bytes() == (ROOT/'.claude/skills/polytoken-add-data/SKILL.md').read_bytes()
