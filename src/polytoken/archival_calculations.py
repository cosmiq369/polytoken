"""Withdrawn metrics retained solely to authenticate pre-model-fit archives."""
from decimal import Decimal

def historical_metrics(metrics, counts, spec, prefix, row, scale, price, fx):
    english_system = next(int(r['tokens']) for r in counts if r['tokenizer_spec'] == spec
                          and r['lang_variant'] == 'en' and r['part'] == 'system_prompt')
    saved = row['billed_system_input'] - english_system * row['requests']
    metrics[prefix + 'english_system_input_saved'] = saved
    metrics[prefix + 'english_system_inr_per_rupee_input_mtok'] = float(Decimal(saved) * scale / 1_000_000)
    if price:
        metrics[prefix + 'english_system_monthly_saving_inr'] = float(
            Decimal(saved) / 1_000_000 * Decimal(str(price['input_per_mtok_usd'])) * scale * Decimal(str(fx['inr_per_usd'])))
