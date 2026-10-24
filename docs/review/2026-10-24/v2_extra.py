import json, glob, collections, random, re, sys, os
from tokenizers import Tokenizer
HUB=os.path.expanduser('~/mnt/PolyToken/.cache/huggingface/hub'); DATA=sys.argv[1]
def tk(v): return Tokenizer.from_file(glob.glob(f'{HUB}/models--{v}/snapshots/*/tokenizer.json')[0])
L=tk('unsloth--Llama-3.2-3B-Instruct'); G=tk('unsloth--gemma-3-4b-it'); Q=tk('Qwen--Qwen3-4B')
n=lambda t,s: len(t.encode(s,add_special_tokens=False).ids)
cfg={c['company']:c for c in map(json.loads,open(DATA+'/data/demo/bot_config.jsonl'))}
rows={co:[json.loads(l) for l in open(f'{DATA}/data/demo/{co}_chats.jsonl')] for co in ('samudra','swara')}
def billed(t, co, sys_text):
    S=n(t,sys_text); by=collections.defaultdict(list)
    for r in rows[co]: by[r['chat_id']].append(r)
    inp=out=replies=0
    for v in by.values():
        hist=0
        for r in sorted(v,key=lambda r:r['turn']):
            k=n(t,r['text_native'])
            if r['role']=='assistant': inp+=S+hist; out+=k; replies+=1
            hist+=k
    return inp,out,replies,len(by)
for name,t in (('Llama',L),('Gemma',G)):
    i,o,rp,c=billed(t,'samudra',cfg['samudra']['system_prompt_native']); ie,oe,_,_=billed(t,'samudra',cfg['samudra']['system_prompt_en'])
    print(f'samudra {name}: billed input/chat {i/c:,.1f} (te prompt) vs {ie/c:,.1f} (en prompt) -> {100*(1-ie/i):.1f}% less; output/chat {o/c:.1f}; replies {rp}; sys te {n(t,cfg["samudra"]["system_prompt_native"])} en {n(t,cfg["samudra"]["system_prompt_en"])}')
i,o,rp,c=billed(Q,'swara',cfg['swara']['system_prompt_native']); print(f'swara Qwen3: billed input/chat {i/c:.1f} output/chat {o/c:.1f} out share {100*o/(i+o):.2f}%')
# cluster bootstrap, samudra Llama assistant ratio
by=collections.defaultdict(lambda:[0,0])
for r in rows['samudra']:
    if r['role']=='assistant': p=by[r['chat_id']]; p[0]+=n(L,r['text_native']); p[1]+=n(L,r['text_en'])
ids=sorted(by); rng=random.Random(20261024); stats=[]
for _ in range(2000):
    s=[by[rng.choice(ids)] for _ in ids]; stats.append(sum(a for a,b in s)/sum(b for a,b in s))
stats.sort()
def pct(p): k=(len(stats)-1)*p; f=int(k); return stats[f]+(stats[min(f+1,len(stats)-1)]-stats[f])*(k-f)
print(f'bootstrap samudra Llama assistant: point {sum(a for a,b in by.values())/sum(b for a,b in by.values()):.4f} 95% [{pct(.025):.4f}, {pct(.975):.4f}] (chats with answers: {len(ids)})')
# data checks
sp=cfg['samudra']['system_prompt_native']; sents=[s.strip() for s in re.split(r'[.!?।]\s*', sp) if s.strip()]
print('samudra prompt words',len(sp.split()),'sentences',len(sents),'distinct',len(set(sents)))
en=cfg['samudra']['system_prompt_en']; print('EN excerpt:', en[:600].replace('\n',' '))
for co in rows:
    by=collections.defaultdict(list)
    for r in rows[co]: by[r['chat_id']].append(r)
    dup=sum(1 for v in by.values() if len({r['text_native'] for r in v if r['role']=='assistant'})<sum(r['role']=='assistant' for r in v))
    first=collections.Counter(' '.join(r['text_en'].split()[:4]) for r in rows[co] if r['role']=='assistant')
    print(co,'chats w/ repeated answer',dup,'| most common answer openings',first.most_common(3))
