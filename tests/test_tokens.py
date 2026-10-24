import pytest
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
