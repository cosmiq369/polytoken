"""Pure calculations shared with the checker; never reads files or services."""
from collections import defaultdict
from decimal import Decimal
from statistics import median

from ..measurement_report import billed_tokens, bootstrap_ratios
from ..prices import cost_usd, PriceUnavailable


def items_from_rows(company, config, chats):
    items = [dict(company=company, chat_id='__system__', turn=0, part='system_prompt',
                  native=config['system_prompt_native'], en=config['system_prompt_en'], lang=config['language'])]
    items.extend(dict(company=company, chat_id=r['chat_id'], turn=int(r['turn']), part=r['role'],
                      native=r['text_native'], en=r['text_en'], lang=r['lang']) for r in chats)
    return items


def select_price(prices, spec):
    choices = [p for p in prices if p['tokenizer_spec'] == spec and p['verified'] is True
               and p['input_per_mtok_usd'] is not None and p['output_per_mtok_usd'] is not None]
    # A reproducible quoted provider scenario, not a claim about the user's invoice.
    return sorted(choices, key=lambda p: (p['input_per_mtok_usd'], p['output_per_mtok_usd'], p['provider']))[0] if choices else None


def baseline_metrics(snapshot, prices, fx):
    items, counts, config = snapshot['items'], snapshot['counts'], snapshot['config']
    billed = billed_tokens(items, counts)
    metrics = {}
    for row in billed:
        if row['lang_variant'] != config['language']:
            continue
        spec = row['tokenizer_spec']
        prefix = 'baseline/' + spec + '/'
        native = [r for r in counts if r['tokenizer_spec'] == spec and r['lang_variant'] == config['language']]
        values = {(r['chat_id'], int(r['turn']), r['part']): int(r['tokens']) for r in native}
        # Attribute history replay to its original role, including prior answers as input.
        parts = defaultdict(int)
        chats = defaultdict(list)
        for item in items:
            if item['part'] != 'system_prompt':
                chats[item['chat_id']].append(item)
        for turns in chats.values():
            history = defaultdict(int, system_prompt=values[('__system__', 0, 'system_prompt')])
            for item in sorted(turns, key=lambda x: x['turn']):
                n = values[(item['chat_id'], item['turn'], item['part'])]
                if item['part'] == 'assistant':
                    for part, count in history.items():
                        parts[part] += count
                    parts['output'] += n
                history[item['part']] += n
        if sum(parts.values()) != row['billed_input'] + row['billed_output']:
            raise ValueError('Billed attribution mismatch')
        for key in ('chat_count', 'requests', 'billed_input', 'billed_output', 'billed_system_input'):
            metrics[prefix + key] = row[key]
        metrics[prefix + 'monthly_chats'] = int(config['monthly_chats'])
        total = row['billed_input'] + row['billed_output']
        for part, n in parts.items():
            metrics[prefix + part + '_tokens'] = n
            metrics[prefix + part + '_share'] = n / total
        price = select_price(prices, spec)
        scale = Decimal(str(config['monthly_chats'])) / row['chat_count']
        if price:
            money = cost_usd(price, row['billed_input'], row['billed_output'])
            metrics[prefix + 'monthly_inr'] = float(money * scale * Decimal(str(fx['inr_per_usd'])))
            for part, n in parts.items():
                component = cost_usd(price, n if part != 'output' else 0, n if part == 'output' else 0)
                metrics[prefix + part + '_cost_share'] = float(component / money) if money else 0.
        english_system = next(int(r['tokens']) for r in counts if r['tokenizer_spec'] == spec
                              and r['lang_variant'] == 'en' and r['part'] == 'system_prompt')
        saved = row['billed_system_input'] - english_system * row['requests']
        metrics[prefix + 'english_system_input_saved'] = saved
        metrics[prefix + 'english_system_inr_per_rupee_input_mtok'] = float(Decimal(saved) * scale / 1_000_000)
        if price:
            metrics[prefix + 'english_system_monthly_saving_inr'] = float(
                Decimal(saved) / 1_000_000 * Decimal(str(price['input_per_mtok_usd'])) * scale * Decimal(str(fx['inr_per_usd'])))
            # Explicit hypothesis only: halve answer tokens, including their later replay.
            metrics[prefix + 'half_answers_monthly_saving_inr'] = float(
                (Decimal(parts['output']) * Decimal(str(price['output_per_mtok_usd']))
                 + Decimal(parts['assistant']) * Decimal(str(price['input_per_mtok_usd'])))
                / 2_000_000 * scale * Decimal(str(fx['inr_per_usd'])))
    for row in bootstrap_ratios(items, counts):
        prefix = 'ratios/' + row['tokenizer_spec'] + '/' + row['part'] + '/'
        for key in ('native_to_english_ratio', 'ci_low', 'ci_high', 'paired_items', 'cluster_count'):
            metrics[prefix + key] = row[key]
    return metrics


def experiment_metrics(experiment, snapshot, prices, fx):
    pairs = experiment['pairs']
    ok = [p for p in pairs if p['original']['ok'] and p['changed']['ok']]
    metrics = {'experiment/completed_pairs': len(ok)}
    if len(ok) != 20:
        return metrics
    spec = snapshot['config']['model_in_use']
    price = select_price(prices, spec)
    scale = Decimal(str(snapshot['config']['monthly_chats']))
    for variant in ('original', 'changed'):
        i = sum(p[variant]['input_tokens'] for p in ok)
        o = sum(p[variant]['output_tokens'] for p in ok)
        metrics['experiment/' + variant + '_input_tokens'] = i
        metrics['experiment/' + variant + '_output_tokens'] = o
        if price:
            # One sampled last-turn response per chat. Not the historical whole-chat bill.
            metrics['experiment/' + variant + '_monthly_inr'] = float(cost_usd(price, i, o) / len(ok) * scale * Decimal(str(fx['inr_per_usd'])))
    saving_i = sum(p['original']['input_tokens'] - p['changed']['input_tokens'] for p in ok)
    metrics['experiment/inr_per_rupee_input_mtok'] = float(Decimal(saving_i) / len(ok) * scale / 1_000_000)
    if price:
        metrics['experiment/monthly_saving_inr'] = (metrics['experiment/original_monthly_inr']
                                                   - metrics['experiment/changed_monthly_inr'])
    return metrics


def quality_metrics(verdict):
    rows = verdict['pairs']
    if len({r['chat_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate quality pair')
    return {'quality/passed': sum(r.get('same_facts') is True for r in rows),
            'quality/judged': sum(type(r.get('same_facts')) is bool for r in rows),
            'quality/queued_for_review': len(rows)}


def speed_metrics(probe):
    good = [r for r in probe['runs'] if r['ok']]
    metrics = {'speed/completed_runs': len(good)}
    if len(good) != 8:
        return metrics
    for field in ('ttft_s', 'output_tokens_per_s', 'latency_s'):
        vals = {v: [r[field] for r in good if r['variant'] == v] for v in ('original', 'changed')}
        if any(len(v) != 4 for v in vals.values()):
            raise ValueError('Four speed runs per variant required')
        for variant, values in vals.items():
            metrics[f'speed/{field}/{variant}_median'] = median(values)
            metrics[f'speed/{field}/{variant}_min'] = min(values)
            metrics[f'speed/{field}/{variant}_max'] = max(values)
        # ABBA ABBA: adjacent A/B measurements form four temporally paired blocks.
        differences = []
        for j in range(0, 8, 2):
            block = {r['variant']: r[field] for r in good[j:j+2]}
            differences.append(block['changed'] - block['original'])
        metrics[f'speed/{field}/paired_difference'] = median(differences)
        metrics[f'speed/{field}/difference_min'] = min(differences)
        metrics[f'speed/{field}/difference_max'] = max(differences)
    return metrics
