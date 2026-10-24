"""Deterministically check the federation against every underlying paired row."""
from collections import defaultdict
import math

from .company_db import ROOT, COMPANIES
from .logs import JsonlLogger
from .measure import read_inputs, utcnow


def checked_ratios(records, expected_inputs):
    pairs = defaultdict(dict)
    groups = defaultdict(lambda: dict(paired_items=0, native_tokens=0, english_tokens=0))
    expected = {(i['company'], i['chat_id'], i['turn'], i['part']):i['lang'] for i in expected_inputs}
    specs = defaultdict(set)
    for row in records:
        key = (row['company'], row['chat_id'], int(row['turn']), row['part'])
        spec = row['tokenizer_spec']
        if key not in expected or row['lang_variant'] not in (expected[key], 'en'):
            raise ValueError('Measurement does not match a source input')
        pair = pairs[(*key, spec, row['run_id'])]
        variant = row['lang_variant']
        count = int(row['tokens'])
        if variant in pair or count <= 0 or str(count) != str(row['tokens']):
            raise ValueError('Duplicate or invalid measurement')
        pair[variant] = count
        specs[key[0]].add(spec)
    for key, lang in expected.items():
        for spec in specs[key[0]]:
            matches = [p for p in pairs if p[:5] == (*key, spec)]
            if len(matches) != 1 or set(pairs[matches[0]]) != {lang, 'en'}:
                raise ValueError('Incomplete or repeated native/English pair')
            pair = pairs[matches[0]]
            group = groups[(key[0], spec, key[3])]
            group['paired_items'] += 1
            group['native_tokens'] += pair[lang]
            group['english_tokens'] += pair['en']
    return [dict(company=c, tokenizer_spec=s, part=p, **v,
                 native_to_english_ratio=v['native_tokens']/v['english_tokens'])
            for (c,s,p),v in sorted(groups.items())]


def check_federation(federated, computed):
    def key(row):
        return row['company'], row['tokenizer_spec'], row['part']
    actual = {key(r):r for r in federated}
    if len(actual) != len(federated) or set(actual) != {key(r) for r in computed}:
        raise ValueError('Federation groups do not match checked measurements')
    for row in computed:
        result = actual[key(row)]
        for field in ('paired_items', 'native_tokens', 'english_tokens'):
            if int(result[field]) != row[field]:
                raise ValueError(f'Federation {field} differs from recomputed value')
        if not math.isclose(float(result['native_to_english_ratio']), row['native_to_english_ratio'], rel_tol=1e-12):
            raise ValueError('Federation ratio differs from recomputed value')


def planted_shares(computed, inputs):
    chats = defaultdict(set)
    for item in inputs:
        if item['part'] != 'system_prompt':
            chats[item['company']].add(item['chat_id'])
    groups = defaultdict(dict)
    for row in computed:
        groups[(row['company'], row['tokenizer_spec'])][row['part']] = row['native_tokens']
    result = []
    for (company, spec), parts in sorted(groups.items()):
        if set(parts) != {'system_prompt', 'user', 'assistant'}:
            raise ValueError('Missing part for planted-property check')
        s = parts['system_prompt'] * len(chats[company])
        u, a = parts['user'], parts['assistant']
        result.append(dict(company=company, tokenizer_spec=spec, chat_count=len(chats[company]),
                           system_tokens=s, user_tokens=u, assistant_tokens=a,
                           system_share_of_input=s/(s+u), output_share_of_total=a/(s+u+a)))
    return result


def verify_and_save(client, logger, sample_dir=ROOT / 'logs/sample'):
    started = utcnow()
    inputs, records, queries = [], [], []
    for company in COMPANIES:
        items, provenance = read_inputs(client, company)
        inputs.extend(items)
        sql = f"SELECT * FROM company_systems.measurements__latest_token_counts WHERE company='{company}'"
        queries.extend([provenance['source_query'], sql])
        records.extend(client.query(sql, page_limit=10000))
    computed = checked_ratios(records, inputs)
    if {r['company'] for r in computed} != set(COMPANIES):
        raise ValueError('Need completed measurements for both companies to prove federation')
    sql = (ROOT / 'sql/token_ratio_by_part.sql').read_text()
    federated = client.query(sql, page_limit=1000)
    check_federation(federated, computed)
    # Check reference coverage and REST count independently, through Zetaris.
    ref_sql = 'SELECT lang_variant, COUNT(*) AS n FROM company_systems.reference__sentences GROUP BY lang_variant'
    price_sql = 'SELECT COUNT(*) AS n FROM polytoken_reference.prices'
    reference = {r['lang_variant']:int(r['n']) for r in client.query(ref_sql)}
    price_count = int(client.query(price_sql)[0]['n'])
    for row in federated:
        lang = next(i['lang'] for i in inputs if i['company']==row['company'])
        if (int(row['native_reference_sentences']) != reference[lang]
                or int(row['english_reference_sentences']) != reference['en']
                or int(row['price_rows']) != price_count):
            raise ValueError('Federation reference coverage failed independent verification')
    shares = billed_shares(inputs, records)
    intervals = bootstrap_ratios(inputs, records)
    provenance = dict(source='Zetaris SQL', query=sql, verification_queries=queries+[ref_sql, price_sql],
                      fetched_at=utcnow(), time_window={'start':started,'end':utcnow()},
                      measurement_run_ids=sorted({r['run_id'] for r in records}),
                      ok=True, translation_review='pending', money_available=False)
    sample = JsonlLogger(sample_dir, run_id=logger.run_id)
    sample.write('federation', 'verified_federation', rows=federated, checked_rows=computed, **provenance)
    sample.write('planted_properties', 'verified_token_shares', rows=shares,
                 accounting='Billed: stateless history replay for each completed reply. Corpus: system once per chat and every turn once. Content only; no template overhead or cache discounts.', **provenance)
    sample.write('bootstrap', 'verified_cluster_intervals', rows=intervals, **provenance)
    logger.write('measurements', 'federation_verified', groups=len(computed), **provenance)
    return computed, shares


def _count_index(chat_rows, counts):
    """Validate complete paired evidence before either accounting convention."""
    if not counts:
        raise ValueError('No measurement evidence')
    checked_ratios(counts, chat_rows)
    index, runs = {}, defaultdict(set)
    for row in counts:
        key = (row['company'], row['tokenizer_spec'], row['lang_variant'])
        runs[key[:2]].add(row['run_id'])
        index.setdefault(key, {})[(row['chat_id'], int(row['turn']), row['part'])] = int(row['tokens'])
    if any(len(values) != 1 for values in runs.values()):
        raise ValueError('Mixed measurement runs')
    if {r['company'] for r in chat_rows} != {k[0] for k in index}:
        raise ValueError('Missing company measurements')
    return index


def billed_tokens(chat_rows, counts):
    """Reconstruct completed stateless requests from read_inputs items and counts.

    All earlier user/assistant content is replayed for each recorded reply. A
    trailing unanswered user remains in corpus totals but incurs no completed
    request. These are content tokens, excluding chat templates/retries/cache.
    Returns both language variants so future cost comparisons stay paired.
    """
    index = _count_index(chat_rows, counts)
    chats = defaultdict(lambda: defaultdict(list))
    systems = defaultdict(list)
    for row in chat_rows:
        if row['part'] == 'system_prompt':
            systems[row['company']].append(row)
        else:
            chats[row['company']][row['chat_id']].append(row)
    for company, company_chats in chats.items():
        if len(systems[company]) != 1:
            raise ValueError('Need one system prompt per company')
        for rows in company_chats.values():
            rows.sort(key=lambda r: int(r['turn']))
            if [int(r['turn']) for r in rows] != list(range(1, len(rows)+1)):
                raise ValueError('Nonconsecutive chat turns')
            if any(r['part'] != ('user' if i % 2 == 0 else 'assistant') for i,r in enumerate(rows)):
                raise ValueError('Chat roles must alternate from user')
    result = []
    for (company, spec, variant), values in sorted(index.items()):
        system = systems[company][0]
        s = values[(system['chat_id'], int(system['turn']), 'system_prompt')]
        billed_input = billed_output = system_input = requests = users = assistants = 0
        for rows in chats[company].values():
            history = s
            for row in rows:
                n = values[(row['chat_id'], int(row['turn']), row['part'])]
                if row['part'] == 'assistant':
                    billed_input += history
                    billed_output += n
                    system_input += s
                    requests += 1
                    assistants += n
                else:
                    users += n
                history += n
        if not requests:
            raise ValueError('No completed replies for billed accounting')
        result.append(dict(company=company, tokenizer_spec=spec, lang_variant=variant,
                           chat_count=len(chats[company]), requests=requests,
                           billed_input=billed_input, billed_output=billed_output,
                           billed_system_input=system_input,
                           corpus_system_input=s*len(chats[company]),
                           corpus_input=s*len(chats[company])+users, corpus_output=assistants))
    return result


def billed_shares(chat_rows, counts):
    """Per company/tokenizer, show native and English under both conventions."""
    groups = {}
    languages = {r['company']:r['lang'] for r in chat_rows}
    for row in billed_tokens(chat_rows, counts):
        key = row['company'], row['tokenizer_spec']
        group = groups.setdefault(key, dict(company=key[0], tokenizer_spec=key[1],
                                           chat_count=row['chat_count'], requests=row['requests']))
        conventions = {}
        for convention, system_key in (('billed', 'billed_system_input'), ('corpus', 'corpus_system_input')):
            i, o = row[convention+'_input'], row[convention+'_output']
            conventions[convention] = dict(input_tokens=i, output_tokens=o, system_input_tokens=row[system_key],
                                           system_share_of_input=row[system_key]/i,
                                           output_share_of_total=o/(i+o))
        if row['lang_variant'] == languages[row['company']]:
            group.update(conventions)
        else:
            group['english'] = conventions
    return [groups[key] for key in sorted(groups)]


def cluster_bootstrap(chat_pairs, *, B=2000, seed=20261024):
    """Paired ratio of sums; resample whole chats, percentile (linear) CI."""
    import random
    if not chat_pairs or type(B) is not int or B < 2:
        raise ValueError('Need chats and at least two bootstrap replicates')
    pairs = [chat_pairs[key] for key in sorted(chat_pairs)]
    if any(len(p) != 2 or any(type(n) is not int or n < 0 for n in p) for p in pairs):
        raise ValueError('Expected nonnegative integer token pairs')
    if any(e <= 0 for _, e in pairs):
        raise ValueError('Each chat must have English evidence for this part')
    rng = random.Random(seed)
    ratios = []
    for _ in range(B):
        native = english = 0
        for _ in pairs:
            n, e = pairs[rng.randrange(len(pairs))]
            native += n
            english += e
        ratios.append(native/english)
    ratios.sort()
    def percentile(q):
        position = q*(B-1)
        lo = math.floor(position)
        hi = math.ceil(position)
        return ratios[lo] + (ratios[hi]-ratios[lo])*(position-lo)
    return dict(ci_low=percentile(.025), ci_high=percentile(.975),
                bootstrap_replicates=B, bootstrap_seed=seed, cluster_count=len(pairs),
                bootstrap_unit='chat', confidence=.95)


def bootstrap_ratios(chat_rows, counts, *, B=2000, seed=20261024):
    index = _count_index(chat_rows, counts)
    result = []
    for row in checked_ratios(counts, chat_rows):
        company, spec, part = row['company'], row['tokenizer_spec'], row['part']
        items = [r for r in chat_rows if r['company'] == company]
        language = items[0]['lang']
        pairs = {r['chat_id']:[0,0] for r in items if r['part'] != 'system_prompt'}
        for item in items:
            if item['part'] != part:
                continue
            key = item['chat_id'], int(item['turn']), part
            n, e = index[(company,spec,language)][key], index[(company,spec,'en')][key]
            targets = pairs if part == 'system_prompt' else [item['chat_id']]
            for chat_id in targets:
                pairs[chat_id][0] += n
                pairs[chat_id][1] += e
        result.append({**row, **cluster_bootstrap(pairs, B=B, seed=seed)})
    return result
