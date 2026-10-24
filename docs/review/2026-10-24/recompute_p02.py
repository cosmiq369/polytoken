"""Independent recomputation of PROMPT-02 measurements (reviewer's own code, not polytoken's)."""
import json, glob, collections, sys
from tokenizers import Tokenizer
ROOT = sys.argv[1]
HUB = ROOT + '/.cache/huggingface/hub'
names = {'Llama 3.2':'unsloth--Llama-3.2-3B-Instruct','Gemma 3':'unsloth--gemma-3-4b-it','Qwen3':'Qwen--Qwen3-4B',
         'Phi-4 mini':'microsoft--Phi-4-mini-instruct','SmolLM3':'HuggingFaceTB--SmolLM3-3B','GPT-OSS':'openai--gpt-oss-20b',
         'Sarvam-1':'sarvamai--sarvam-1','Krutrim-2':'krutrim-ai-labs--Krutrim-2-instruct'}
toks = {k: Tokenizer.from_file(glob.glob(f'{HUB}/models--{v}/snapshots/*/tokenizer.json')[0]) for k, v in names.items()}
cfg = {c['company']: c for c in map(json.loads, open(ROOT + '/data/demo/bot_config.jsonl'))}
chats = {co: [json.loads(l) for l in open(f'{ROOT}/data/demo/{co}_chats.jsonl')] for co in ('samudra', 'swara')}
def n(t, s): return len(t.encode(s, add_special_tokens=False).ids)
out = {}
for name, t in toks.items():
    row = {}
    for co, rows in chats.items():
        sys_n, sys_e = n(t, cfg[co]['system_prompt_native']), n(t, cfg[co]['system_prompt_en'])
        part = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            p = part[r['role']]; p[0] += n(t, r['text_native']); p[1] += n(t, r['text_en'])
        nchat = len({r['chat_id'] for r in rows})
        # convention A (Codex): one system prompt per chat, each turn once
        inA = nchat * sys_n + part['user'][0]; totA = inA + part['assistant'][0]
        # convention B (billed): stateless API, every assistant turn re-sends system + full history
        inB = outB = 0
        by = collections.defaultdict(list)
        for r in rows: by[r['chat_id']].append(r)
        for v in by.values():
            hist = 0
            for r in sorted(v, key=lambda r: r['turn']):
                k = n(t, r['text_native'])
                if r['role'] == 'assistant':
                    inB += sys_n + hist; outB += k
                hist += k
        row[co] = dict(sys=round(sys_n / sys_e, 3), user=round(part['user'][0] / part['user'][1], 3),
                       asst=round(part['assistant'][0] / part['assistant'][1], 3),
                       sys_share_A=round(100 * nchat * sys_n / inA, 2), out_share_A=round(100 * part['assistant'][0] / totA, 2),
                       inB=inB, outB=outB, sys_tokens=sys_n)
        # system share of billed input: system is re-sent once per assistant turn
        n_asst = sum(1 for r in rows if r['role'] == 'assistant')
        row[co]['sys_share_B'] = round(100 * n_asst * sys_n / inB, 2)
        row[co]['out_share_B'] = round(100 * outB / (inB + outB), 2)
    out[name] = row
    s, w = row['samudra'], row['swara']
    print(f"{name:11s} sam sys/user/asst {s['sys']:6.3f} {s['user']:6.3f} {s['asst']:6.3f} | swa {w['sys']:6.3f} {w['user']:6.3f} {w['asst']:6.3f} | "
          f"A: sam sys%in {s['sys_share_A']:5.2f} swa out%tot {w['out_share_A']:5.2f} | B(billed): sam sys%in {s['sys_share_B']:5.2f} swa out%tot {w['out_share_B']:5.2f} | sam sys tokens {s['sys_tokens']}")
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
