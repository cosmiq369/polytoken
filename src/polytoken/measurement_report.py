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
    shares = planted_shares(computed, inputs)
    provenance = dict(source='Zetaris SQL', query=sql, verification_queries=queries+[ref_sql, price_sql],
                      fetched_at=utcnow(), time_window={'start':started,'end':utcnow()},
                      measurement_run_ids=sorted({r['run_id'] for r in records}),
                      ok=True, translation_review='pending', money_available=False)
    sample = JsonlLogger(sample_dir, run_id=logger.run_id)
    sample.write('federation', 'verified_federation', rows=federated, checked_rows=computed, **provenance)
    sample.write('planted_properties', 'verified_token_shares', rows=shares,
                 accounting='One system prompt per chat; each user/assistant turn once; no history replay or template overhead', **provenance)
    logger.write('measurements', 'federation_verified', groups=len(computed), **provenance)
    return computed, shares
