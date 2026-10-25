from indictax.tok import TokenizerAdapter

from polytoken import tokens


def test_count_fragments_and_cache(monkeypatch):
    loaded = []

    def load(spec):
        loaded.append(spec)
        return TokenizerAdapter(spec, 256, lambda text: list(text.encode()), lambda tid: tid >= 128)

    monkeypatch.setattr(tokens, "load_tokenizer", load)
    tokens._tokenizer.cache_clear()
    try:
        assert tokens.count("fixture", "తెలుగు") == len("తెలుగు".encode())
        assert tokens.fragment_rate("fixture", "తెలుగు") == 1.0
        assert tokens.fragment_rate("fixture", "hello") == 0.0
        assert tokens.fragment_rate("fixture", "") == 0.0
        assert loaded == ["fixture"]
    finally:
        tokens._tokenizer.cache_clear()


def test_local_tokenizer_uses_real_indictax(tmp_path):
    from tokenizers import Tokenizer, models, pre_tokenizers

    path = tmp_path / "tokenizer.json"
    tk = Tokenizer(models.WordLevel({"[UNK]": 0, "తెలుగు": 1, "hello": 2}, unk_token="[UNK]"))
    tk.pre_tokenizer = pre_tokenizers.Whitespace()
    tk.save(str(path))
    assert tokens.count(f"file:{path}", "తెలుగు hello") == 2
    assert tokens.fragment_rate(f"file:{path}", "తెలుగు hello") == 0.0


def test_paired_saved_token_samples_are_checked_and_review_label_is_honest(tmp_path):
    import copy
    from pathlib import Path
    from types import SimpleNamespace
    from polytoken.token_samples import samples
    from polytoken.logs import JsonlLogger
    from polytoken.billing_view import EventWorld
    from polytoken.checker import Checker
    root=Path(__file__).resolve().parents[1]
    data=samples(root/'logs',JsonlLogger(tmp_path))
    assert {s['variant'] for s in data}=={'native','tenglish'}
    for s in data:
        assert s['review_status']=='unreviewed' and s['models']
        for model in s['models']:
            world=EventWorld(model['evidence'])
            assert Checker(SimpleNamespace(world=world)).check(model['claims'])[1]==[]
            values={c['id']:c['value'] for c in model['claims']}
            assert values['token_pair/ratio']==values['token_pair/native_tokens']/values['token_pair/english_tokens']
            corrupt=copy.deepcopy(model['evidence']);corrupt[0]['payload']['count']+=1
            assert Checker(SimpleNamespace(world=EventWorld(corrupt))).check(model['claims'])[0]==[]
