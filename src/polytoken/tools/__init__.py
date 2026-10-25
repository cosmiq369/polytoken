"""Investigation capabilities: all observations have World Model evidence IDs."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..agent.jobs import cache_key, cached_calls
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
import random
import re
import time
from uuid import uuid4

from .. import tokens
from ..agent.budget import BudgetExceeded
from ..agent.calculations import items_from_rows, baseline_metrics, select_price
from ..prices import load_prices
from ..reference import ROOT, load_fx, load_hosted


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_sql(query):
    # Deliberately small grammar; no comments, expressions, UDFs, joins, CTEs or
    # nested queries can smuggle another datasource or write into a SELECT.
    name = r'[a-zA-Z_][a-zA-Z_0-9]*'
    columns = rf'(?:\*|{name}(?:\s*,\s*{name})*|COUNT\(\*\)\s+AS\s+{name})'
    where = rf"(?:\s+WHERE\s+{name}\s*=\s*'(?:[a-zA-Z_0-9/-]+)')?"
    order = rf'(?:\s+ORDER\s+BY\s+{name}(?:\s*,\s*{name})*)?'
    pattern = rf'\s*SELECT\s+{columns}\s+FROM\s+(?:company_systems|polytoken_reference)\.{name}{where}{order}\s*'
    if not isinstance(query, str) or not re.fullmatch(pattern, query, re.I):
        raise ValueError('Only a simple SELECT from company_systems or polytoken_reference is permitted')
    return query


class InvestigationTools:
    def __init__(self, client, generate, store, budget, logger, *, catalogue,
                 fx=None, prices=None, count=tokens.count, emit=lambda *a, **k: None):
        self.client, self.generate, self.store, self.budget, self.logger = client, generate, store, budget, logger
        self.catalogue = catalogue
        self.fx = fx if fx is not None else load_fx()
        self.reference_prices = prices if prices is not None else load_prices(ROOT / 'prices.json')
        self.count, self.emit = count, emit
        self.ids = []
        self.snapshot = self.snapshot_id = self.price_id = self.fx_id = None
        self.prices = []

    def observe(self, kind, payload, query, source='PolyToken calculation', started=None):
        fetched = now()
        provenance = dict(kind=source, source=source, at=fetched, query=query,
                          time_window={'start': started or fetched, 'end': fetched}, fetched_at=fetched)
        eid = self.store.add(kind, payload, source=provenance, evidence_id=uuid4().hex,
                             supports=payload.get('supports', []))
        self.ids.append(eid)
        self.logger.write('evidence', 'observation', evidence_id=eid, kind=kind, payload=payload, source=provenance)
        self.emit('evidence_added', evidence_id=eid, kind=kind)
        return eid

    def sql(self, query):
        validate_sql(query)
        self.budget.check()
        started = now()
        try:
            rows = self.client.query(query, page_limit=20000,
                                     before_attempt=lambda: self.budget.consume('sql'), remaining=self.budget.remaining)
            self.budget.check()
        except Exception as exc:
            self.observe('query_result', {'ok': False, 'error_class': type(exc).__name__}, query, 'Zetaris SQL', started)
            if self.budget.reason:
                raise BudgetExceeded(self.budget.reason) from None
            raise
        eid = self.observe('query_result', {'ok': True, 'rows': rows}, query, 'Zetaris SQL', started)
        return {'rows': rows, 'evidence_ids': [eid]}

    def load_company(self, company, overrides=None):
        if company not in ('samudra', 'swara'):
            raise ValueError('Unknown company')
        config_result = self.sql(f'SELECT * FROM company_systems.{company}__bot_config')
        if len(config_result['rows']) != 1:
            raise ValueError('Need exactly one bot_config')
        config = dict(config_result['rows'][0])
        for key, value in (overrides or {}).items():
            if key in ('monthly_chats', 'latency_target_s') and value is not None:
                if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                    raise ValueError('Positive finite user constraint required')
                config[key] = value
        if config.get('monthly_chats') is not None and type(config.get('monthly_chats')) is not int:
            config['monthly_chats'] = int(config['monthly_chats'])
        if config.get('latency_target_s') is not None:
            config['latency_target_s'] = float(config['latency_target_s'])
        return config, config_result['evidence_ids']

    def token_meter(self, company, part='all', variant='native', *, texts=None, tokenizer=None):
        if variant not in ('native', 'en', 'changed') or part not in ('all', 'system_prompt', 'user', 'assistant'):
            raise ValueError('Unknown token measurement selection')
        if texts is not None:
            if not tokenizer or not all(isinstance(t, str) and t for t in texts):
                raise ValueError('Nonempty texts and tokenizer required')
            rows = [{'text': t, 'tokens': self.count(tokenizer, t)} for t in texts]
            eid = self.observe('measurement', {'ok': True, 'company': company, 'part': part,
                               'variant': variant, 'tokenizer_spec': tokenizer, 'rows': rows},
                               {'operation': 'indictax.count', 'tokenizer': tokenizer}, 'indictax tokenizer')
            return {'rows': rows, 'evidence_ids': [eid]}
        if company not in ('samudra', 'swara'):
            raise ValueError('Unknown company')
        result = self.sql("SELECT * FROM company_systems.measurements__latest_token_counts WHERE company='" + company + "'")
        rows = [r for r in result['rows'] if (part == 'all' or r['part'] == part)
                and ((r['lang_variant'] == 'en') == (variant == 'en'))]
        return {'rows': rows, 'all_rows': result['rows'], 'evidence_ids': result['evidence_ids']}

    def measure(self, company, config, config_ids):
        chats = self.sql(f'SELECT * FROM company_systems.{company}__chats ORDER BY chat_id, turn')
        measured = self.token_meter(company)
        specs = {r['tokenizer_spec'] for r in measured['all_rows']}
        matches = [s for s in specs if s == config['model_in_use'] or s.rsplit('/', 1)[-1] == config['model_in_use']]
        if len(matches) != 1:
            raise ValueError('Deployed model must resolve to exactly one measured tokenizer')
        config['deployed_model'] = config['model_in_use']
        config['model_in_use'] = matches[0]
        self.snapshot = {'config': config, 'items': items_from_rows(company, config, chats['rows']),
                         'counts': measured['all_rows'], 'supports': config_ids + chats['evidence_ids'] + measured['evidence_ids']}
        self.snapshot_id = self.observe('measurement', self.snapshot, 'Join bot_config, chats and latest token counts', 'Zetaris SQL snapshot')
        quoted = self.sql('SELECT * FROM polytoken_reference.prices')
        for reference in self.reference_prices:
            for row in quoted['rows']:
                if row.get('model') == reference['model'] and row.get('provider') == reference['provider']:
                    # The live federation must agree with the unchanged verified reference.
                    def equal(key):
                        if key.endswith('_usd'):
                            return row.get(key) is not None and Decimal(str(row[key])) == Decimal(str(reference[key]))
                        if key == 'verified':
                            return row.get(key) in (True, 'true') and reference[key] is True
                        return row.get(key) == reference[key]
                    if all(equal(k) for k in reference):
                        self.prices.append(reference)
        self.price_id = self.observe('price', {'rows': self.prices, 'supports': quoted['evidence_ids']},
                                     'Verified reference prices matched to SELECT * FROM polytoken_reference.prices', 'Zetaris SQL + verified price loader')
        self.fx_id = self.observe('price', self.fx, 'load_fx(data/reference/fx.json)', self.fx['source_url'])
        return {'metrics': baseline_metrics(self.snapshot, self.prices, self.fx),
                'evidence_ids': [self.snapshot_id, self.price_id, self.fx_id]}

    def billed_cost(self, company, tokenizer, variant='native', price_entry=None):
        if not self.snapshot or self.snapshot['items'][0]['company'] != company or variant not in ('native', 'english_system'):
            raise ValueError('Measure the company first; use native or english_system')
        price = select_price(self.prices, tokenizer)
        if price_entry is not None and price_entry != price:
            raise ValueError('Price entry must match the verified quoted scenario')
        metrics = baseline_metrics(self.snapshot, self.prices, self.fx)
        prefix = 'baseline/' + tokenizer + '/'
        before = metrics.get(prefix + 'monthly_inr')
        saving = metrics.get(prefix + 'english_system_monthly_saving_inr')
        payload = {'money_status': 'quoted scenario' if before is not None else 'money unavailable',
                   'before_monthly_inr': before,
                   'after_monthly_inr': before - saving if before is not None and variant == 'english_system' else before,
                   'saving_per_rupee_input_mtok': metrics[prefix + 'english_system_inr_per_rupee_input_mtok'],
                   'price_entry': price, 'variant': variant,
                   'supports': [self.snapshot_id, self.price_id, self.fx_id]}
        eid = self.observe('measurement', payload, {'operation': 'billed_tokens + cost_usd + FX'})
        return {**payload, 'evidence_ids': [eid]}

    def hosted_choices(self, spec):
        return [m for family, models in self.catalogue['families'].items() if spec in family for m in models]

    def choose_host(self, spec):
        matching = self.hosted_choices(spec)
        if matching:
            return matching[0], False
        all_models = [m for models in self.catalogue['families'].values() for m in models]
        if not all_models:
            raise ValueError('No permitted models in live NVIDIA catalogue')
        return all_models[0], True

    def changed_prompt(self, config, lever):
        language = config['language']
        if lever == 'english_system':
            return config['system_prompt_en'] + f'\nKeep every reply in language {language}.'
        if lever == 'answer_cap':
            return config['system_prompt_native'] + f'\nReply only in {language}. Use at most two short sentences. Preserve all relevant facts; ask a concise clarifying question when needed.'
        if lever == 'model_switch':
            return config['system_prompt_native']
        raise ValueError('Unknown lever')

    def generation_options(self, model):
        options = dict(self.catalogue.get('serving_verification', {}).get(model, {}).get('generation_options', {}))
        if 'gpt-oss' in model:
            options['reasoning_effort'] = 'low'
        return options

    def _hosted_call(self, prompt, system, model, spec, conversation=None):
        history = conversation or [{'role': 'user', 'content': prompt}]
        attempts = []
        for regeneration in range(2):
            started = now()
            try:
                result = self.generate(prompt, system_prompt=system, conversation=history, model=model, temperature=0,
                                       on_stream=lambda _: None, before_attempt=lambda: self.budget.consume('hosted'),
                                       remaining=self.budget.remaining, abort=self.budget.check,
                                       timeout_s=120., max_retries=2, retry_timeouts=True,
                                       reasoning_effort=self.generation_options(model).get('reasoning_effort'), max_tokens=1024)
                self.budget.check()
                finish = result.get('finish_reason')
                complete = finish == 'stop' and bool(result['text'].strip())
                row = {'ok': complete, 'text': result['text'], 'usage': result.get('usage') or {}, 'model': model,
                       'finish_reason': finish, 'regeneration': regeneration,
                       'input_tokens': self.count(spec, system) + sum(self.count(spec, m['content']) for m in history),
                       'output_tokens': self.count(spec, result['text']),
                       'latency_s': result.get('request_latency_s', result['latency_s']), 'ttft_s': result.get('ttft_s'),
                       'started': started, 'fetched_at': now()}
                if not complete:
                    row['error_class'] = 'TruncatedReply' if finish == 'length' else 'IncompleteReply'
            except Exception as exc:
                row = {'ok': False, 'error_class': type(exc).__name__, 'reason': self.logger.redact(str(exc))[:500],
                       'model': model, 'finish_reason': None, 'started': started, 'fetched_at': now()}
            attempts.append(dict(row))
            if row.get('finish_reason') != 'length' or self.budget.reason:
                break
        return {**row, 'generation_attempts': attempts}

    def fix_experiment(self, company, lever, hosted_model=None):
        config = self.snapshot['config']
        spec = config['model_in_use']
        original_model, standin = self.choose_host(spec)
        permitted = [m for models in self.catalogue['families'].values() for m in models]
        target = hosted_model or original_model
        if target not in permitted:
            raise ValueError('Hosted model absent from live allowlist')
        if lever != 'model_switch' and target != original_model:
            raise ValueError('Prompt A/B must use the same hosted model')
        if lever == 'model_switch':
            own_family = next((family for family, models in self.catalogue['families'].items() if original_model in models), None)
            target_family = next((family for family, models in self.catalogue['families'].items() if target in models), None)
            if own_family == target_family:
                raise ValueError('Model switch requires another hosted family')
        from ..agent.quality import contextual_experiment
        return contextual_experiment(self, company, lever, original_model, target, standin)

    def quality_judge(self, pairs, comparison='ab'):
        from ..agent.quality import contextual_judge
        return contextual_judge(self, pairs, comparison)

    def speed_probe(self, hosted_model, variants):
        allowed = {m for rows in self.catalogue['families'].values() for m in rows}
        if hosted_model not in allowed or set(variants) != {'original', 'changed'}:
            raise ValueError('Invalid speed probe')
        runs, call_ids = [], []
        cache = cached_calls(self.store)
        for index, variant in enumerate(('original', 'changed', 'changed', 'original') * 2):
            args = variants[variant]
            model = args.get('model', hosted_model)
            if model not in allowed:
                raise ValueError('Probe model not allowed')
            config = self.snapshot['config']
            key = cache_key(model, args['system'], config['company'] + '/speed/' + args.get('chat_id', 'probe') + '/' + str(index),
                            args.get('conversation') or args['user'], 1024,
                            {**self.generation_options(model), 'protocol_version': 3})
            if key in cache:
                cached, parent = cache[key]
                row = {**cached, 'supports': [parent], 'cache_hit': True}
                self.logger.write('experiment_jobs', 'cache_hit', cache_key=key, evidence_id=parent)
            else:
                row = self._hosted_call(args['user'], args['system'], model, config['model_in_use'], args.get('conversation'))
            row.update(variant=variant, cache_key=key)
            # Reasoning-model completion usage may include hidden tokens emitted
            # before visible TTFT. Without a breakdown it is not visible throughput.
            options = self.catalogue.get('serving_verification', {}).get(model, {}).get('generation_options', {})
            row['throughput_supported'] = not bool(options.get('reasoning_effort'))
            if row['ok']:
                output = row['usage'].get('completion_tokens')
                ttft, elapsed = row.get('ttft_s'), row['latency_s']
                if type(output) is not int or output <= 0 or ttft is None or elapsed <= ttft:
                    row.update(ok=False, error_class='MissingOrInvalidStreamUsage')
                elif row['throughput_supported']:
                    row['output_tokens_per_s'] = output / (elapsed - ttft)
                else:
                    row.pop('output_tokens_per_s', None)
                    row['throughput_note'] = 'Unavailable: provider completion usage does not separate reasoning tokens from visible reply tokens.'
            runs.append(row)
            call_ids.append(self.observe('timed_call', row, {'operation': 'speed_probe', 'variant': variant, 'temperature': 0}, 'NVIDIA streamed usage'))
        result = {'runs': runs, 'order': 'ABBAABBA', 'supports': call_ids}
        eid = self.observe('timed_call', result, 'Four streamed runs per variant, ABBA twice', 'NVIDIA streamed usage')
        return {**result, 'evidence_ids': [eid]}
