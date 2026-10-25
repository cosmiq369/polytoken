"""Thin cached access to the declared, separately installed indictax harness."""

from functools import lru_cache

from indictax.tok import load_tokenizer


@lru_cache(maxsize=None)
def _tokenizer(spec: str):
    return load_tokenizer(spec)


def count(spec: str, text: str) -> int:
    return len(_tokenizer(spec).encode(text))


def fragment_rate(spec: str, text: str) -> float:
    tokenizer = _tokenizer(spec)
    ids = tokenizer.encode(text)
    return sum(tokenizer.is_fragment(tid) for tid in ids) / len(ids) if ids else 0.0


def local_tokenizer_files():
    """Resolve only the measured allowlist in the local HF cache, without download."""
    from pathlib import Path
    import yaml
    from huggingface_hub import try_to_load_from_cache
    from .paths import ROOT
    config = ROOT / 'configs/tokenizers.yaml'
    result = {}
    for row in yaml.safe_load(config.read_text())['tokenizers']:
        spec = row['spec']
        cached = try_to_load_from_cache(spec.removeprefix('hf:'), 'tokenizer.json')
        result[spec] = cached if isinstance(cached, str) and Path(cached).is_file() else None
    return result


@lru_cache(maxsize=16)
def _local_metadata(path, mtime_ns):
    from pathlib import Path
    import hashlib
    from tokenizers import Tokenizer
    return Tokenizer.from_file(path), hashlib.sha256(Path(path).read_bytes()).hexdigest()


def token_pieces(spec, text):
    """Return lossless display spans plus real IDs, raw labels and fragment flags.

    Byte tokens can share a Unicode offset. The first consumes the display span;
    subsequent pieces have empty text but retain their actual raw token labels.
    Gaps discarded by a tokenizer's normalizer are explicitly non-token spans.
    """
    from pathlib import Path
    from indictax.textstats import word_count
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        raise ValueError('Supply nonempty text of at most 2000 characters')
    files = local_tokenizer_files()
    if spec not in files:
        raise ValueError('Unknown tokenizer; choose a measured tokenizer')
    if not files[spec]:
        return dict(ok=False, tokenizer=spec, reason='Tokenizer is not available in the local cache; no download attempted.')
    path = Path(files[spec])
    metadata, digest = _local_metadata(str(path), path.stat().st_mtime_ns)
    adapter = _tokenizer('file:' + str(path))
    ids = adapter.encode(text)
    encoded = metadata.encode(text, add_special_tokens=False)
    if ids != encoded.ids or ids != adapter.encode(text):
        raise ValueError('Tokenizer IDs differ on independent encoding')
    import json
    import re
    decoder = json.loads(metadata.to_str()).get('decoder')
    byte_level = 'ByteLevel' in json.dumps(decoder)
    # Invert the reversible byte-to-Unicode alphabet used by ByteLevel BPE.
    direct = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    alphabet = {chr(b): b for b in direct}
    alphabet.update({chr(256 + i): b for i, b in enumerate(b for b in range(256) if b not in direct)})
    def hex_bytes(raw):
        fallback = re.fullmatch(r'<0x([0-9A-Fa-f]{2})>', raw)
        if fallback:
            return fallback[1].upper()
        if byte_level and all(c in alphabet for c in raw):
            return ' '.join(f'{alphabet[c]:02X}' for c in raw)
        return None
    pieces, cursor = [], 0
    for tid, raw, (start, end) in zip(encoded.ids, encoded.tokens, encoded.offsets):
        end = min(len(text), max(cursor, end))
        pieces.append(dict(id=tid, raw=raw, text=text[cursor:end], start=cursor, end=end,
                           tokenizer_start=start, tokenizer_end=encoded.offsets[len(pieces)][1],
                           fragment=adapter.is_fragment(tid), byte_hex=hex_bytes(raw), kind='token'))
        cursor = end
    if cursor < len(text):
        pieces.append(dict(id=None, raw='', text=text[cursor:], start=cursor, end=len(text),
                           fragment=False, kind='gap'))
    if ''.join(p['text'] for p in pieces) != text:
        raise ValueError('Token display pieces do not reproduce input')
    fragments = sum(adapter.is_fragment(tid) for tid in ids)
    if fragments != sum(p['fragment'] for p in pieces):
        raise ValueError('Fragment counts differ on recomputation')
    words = word_count(text)
    return dict(ok=True, tokenizer=spec, text=text, pieces=pieces, count=len(ids), words=words,
                fragments=fragments, tokens_per_word=len(ids)/words if words else None,
                lone_byte_share=fragments/len(ids) if ids else None,
                tokenizer_sha256=digest, source='Local tokenizer.json through indictax',
                formula={'tokens_per_word':'token count / whitespace word count',
                         'lone_byte_share':'lone-byte or partial-character token count / all token IDs'},
                boundary_note='Byte pieces may share a Unicode character span. Hex bytes identify byte tokens, grouped by their source character span; gap spans are not tokens.')
