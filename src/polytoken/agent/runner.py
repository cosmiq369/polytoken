"""Nine bounded steps, one Markovian run, and a claims-only report."""
import json
from uuid import uuid4

from .budget import BudgetExceeded
from .calculations import experiment_metrics, quality_metrics, speed_metrics, select_price
from .planner import Planner
from ..checker import Checker, make_claims
from ..meterless.markovian import Markovian, run_efficiency
from ..tools import now

STEPS = ('clarify', 'measure', 'locate', 'hypothesise', 'experiment', 'judge', 'speed', 'check', 'report')
DEFAULT_WHY = {
    'clarify': 'Read the company configuration and recall sourced constraints before measuring.',
    'measure': 'Read paired token measurements and verified prices through Zetaris to reconstruct billed history.',
    'locate': 'Compare billed cost contributions from the system, user turns, replayed answers and output.',
    'hypothesise': 'Rank estimated savings from changing the system language, shortening answers and switching tokenizer families.',
    'experiment': 'Test the highest-priority feasible hypothesis with paired hosted replies on the same sampled user turns.',
    'judge': 'Check whether changed replies preserve the original facts and queue every pair for native review.',
    'speed': 'Measure streamed timings in alternating order to expose run-to-run variation.',
    'check': 'Recompute every proposed report number using only stored evidence.',
    'report': 'Publish verified claims with model, accounting, uncertainty and review limitations.',
}


class Investigation:
    def __init__(self, tools, memory, *, question='', monthly_chats=None, latency_target_s=None,
                 event_sink=None, historical_runs=None, run_id=None):
        self.tools, self.memory = tools, memory
        self.guard, self.logger = tools.budget, tools.logger
        self.run_id = run_id or self.logger.run_id or uuid4().hex
        self.question = question
        self.overrides = {'monthly_chats': monthly_chats, 'latency_target_s': latency_target_s}
        self.event_sink = event_sink or (lambda event: None)
        self.events, self.claims, self.dropped = [], [], []
        self.history = historical_runs or []
        self.step, self.why = 'clarify', DEFAULT_WHY['clarify']
        self.context, self.metrics, self.candidates, self.remembered = {}, {}, [], []
        self.experiment = self.quality = self.speed = None
        self.partial_reason = None
        self.needs_input = []
        self.checker = Checker(tools.store, self.logger)
        self.tools.emit = self.emit
        self.model_usage = []
        original_generate = tools.generate
        def tracked_generate(prompt, **kwargs):
            try:
                result = original_generate(prompt, **kwargs)
            except Exception:
                if kwargs.get('model') is None:
                    self.model_usage.append({})
                raise
            if kwargs.get('model') is None:
                self.model_usage.append(result.get('usage') or {})
            return result
        self.tools.generate = tracked_generate
        self.planner = Planner(self.nemotron, self.logger)

    def emit(self, event, **fields):
        row = {'event': event, 'timestamp': now(), 'investigation_id': self.run_id,
               'step': self.step, 'why': self.why, **fields}
        row = self.logger.redact(row)
        self.events.append(row)
        self.logger.write('agent_events', event, **{k: v for k, v in row.items() if k != 'event'})
        self.event_sink(row)

    def nemotron(self, prompt):
        return self.tools.generate(prompt, before_attempt=lambda: self.guard.consume('nemotron'),
                                   remaining=self.guard.remaining, abort=self.guard.check, enable_thinking=False)

    def add_metrics(self, metrics, operation, inputs):
        self.claims.extend(make_claims(metrics, operation, inputs))

    def baseline_inputs(self):
        return {'snapshot': self.tools.snapshot_id, 'prices': self.tools.price_id, 'fx': self.tools.fx_id}

    def hypotheses(self):
        spec = self.config['model_in_use']
        prefix = 'baseline/' + spec + '/'
        english_key = prefix + 'english_system_monthly_saving_inr'
        cap_key = prefix + 'half_answers_monthly_saving_inr'
        candidates = [dict(lever='english_system', claim_id=english_key,
                           basis='Measured system-language substitution; reply-language instruction overhead and generated answers require experiment.'),
                      dict(lever='answer_cap', claim_id=cap_key,
                           basis='Hypothesis assumes half as many answer tokens, including replay; no measured cap benefit yet.')]
        own = self.metrics.get(prefix + 'monthly_inr')
        switched = {}
        if own is not None:
            for key, value in list(self.metrics.items()):
                if key.startswith('baseline/') and key.endswith('/monthly_inr'):
                    other = key[len('baseline/'):-len('/monthly_inr')]
                    if other != spec:
                        claim_id = 'hypotheses/' + other + '/switch_monthly_saving_inr'
                        switched[claim_id] = own - value
                        candidates.append(dict(lever='model_switch', tokenizer=other, claim_id=claim_id,
                                               basis='Quoted alternate tokenizer/provider scenario; hosting and output quality remain untested.'))
        self.add_metrics(switched, 'hypotheses', self.baseline_inputs())
        self.metrics.update(switched)
        for candidate in candidates:
            candidate['status'] = 'untested estimate'
        return sorted(candidates, key=lambda c: self.metrics.get(c['claim_id'], float('-inf')), reverse=True)

    def experiment_choices(self):
        choices = []
        original, _ = self.tools.choose_host(self.config['model_in_use'])
        for candidate in self.candidates:
            lever = candidate['lever']
            target = original
            if lever == 'model_switch':
                hosts = self.tools.hosted_choices(candidate['tokenizer'])
                if not hosts or hosts[0] == original:
                    continue
                original_family = next(f for f, ms in self.tools.catalogue['families'].items() if original in ms)
                if candidate['tokenizer'] in original_family:
                    continue
                target = hosts[0]
            args = {'lever': lever, 'hosted_model': target}
            if args not in choices:
                choices.append(args)
        return choices

    def do_step(self, step, args, company):
        t = self.tools
        if step == 'clarify':
            recalled = [r['memory'] for r in self.memory.query(company, threshold=0., top_n=20)['memories']
                        if company in r['memory'].entities and r['memory'].type == 'company_profile']
            self.remembered = [{'id': m.id, 'source': m.source} for m in recalled]
            remembered = json.loads(recalled[-1].content) if recalled else {}
            config, ids = t.load_company(company, self.overrides)
            for key in ('monthly_chats', 'latency_target_s', 'model_in_use', 'language'):
                if config.get(key) is None and remembered.get(key) is not None:
                    config[key] = remembered[key]
            self.needs_input = [key for key in ('monthly_chats', 'latency_target_s', 'model_in_use', 'language') if config.get(key) is None]
            if self.needs_input:
                self.partial_reason = 'Clarification required: ' + ', '.join(self.needs_input)
                return
            config['constraints'] = remembered.get('constraints') or [f"Replies stay in {config['language']}"]
            profile = {k: config[k] for k in ('monthly_chats', 'latency_target_s', 'model_in_use', 'language', 'constraints')}
            eid = t.observe('query_result', {'config': config, 'user_overrides': self.overrides,
                                            'remembered': self.remembered, 'supports': ids},
                            {'operation': 'clarify', 'question': self.question}, 'Zetaris bot_config + sourced H-MEM + explicit user input')
            self.config, self.config_ids = config, [eid]
            self.memory.add(content=json.dumps(profile), source=eid, layer='long_term',
                            entities=[company], domain='company', type='company_profile', confidence=1.)
            self.emit('finding', text='Recalled the saved company profile and constraints.' if recalled else 'Saved the company configuration and reply-language constraint.',
                      remembered=self.remembered, evidence_ids=[eid])
            self.context.update(company=company, language=config['language'], model=config['model_in_use'], constraints=config['constraints'])
        elif step == 'measure':
            result = t.measure(company, self.config, self.config_ids)
            self.metrics = result['metrics']
            self.add_metrics(self.metrics, 'baseline', self.baseline_inputs())
            t.billed_cost(company, self.config['model_in_use'])
            prefix = 'baseline/' + self.config['model_in_use'] + '/'
            self.context['billed_evidence'] = {k[len(prefix):]: v for k, v in self.metrics.items() if k.startswith(prefix)}
        elif step == 'locate':
            prefix = 'baseline/' + self.config['model_in_use'] + '/'
            parts = {part: self.metrics.get(prefix + part + '_cost_share') for part in ('system_prompt', 'user', 'assistant', 'output')}
            if all(value is None for value in parts.values()):
                parts = {part: self.metrics.get(prefix + part + '_share', 0) for part in parts}
                self.finding = 'The largest billed token component is ' + max(parts, key=parts.get) + '; money unavailable.'
            else:
                self.finding = 'The largest billed cost component at the quoted provider price is ' + max(parts, key=lambda p: parts[p] or 0) + '.'
            self.context['finding'] = self.finding
            self.emit('finding', text=self.finding, evidence_ids=list(self.baseline_inputs().values()))
        elif step == 'hypothesise':
            self.candidates = self.hypotheses()
            self.context['ranked_hypotheses'] = [{**c, 'expected_monthly_saving_inr': self.metrics.get(c['claim_id'])} for c in self.candidates]
        elif step == 'experiment':
            self.experiment = t.fix_experiment(company, **args)
            metrics = experiment_metrics(self.experiment, t.snapshot, t.prices, t.fx)
            self.add_metrics(metrics, 'experiment', {**self.baseline_inputs(), 'experiment': self.experiment['evidence_ids'][0]})
            self.context['experiment'] = {'lever': args['lever'], 'model_label': self.experiment['model_label'], **metrics}
        elif step == 'judge':
            self.quality = t.quality_judge(self.experiment['pairs'])
            self.add_metrics(quality_metrics(self.quality), 'quality', {'quality': self.quality['evidence_ids'][0]})
            self.context['quality'] = quality_metrics(self.quality)
        elif step == 'speed':
            pair = self.experiment['pairs'][0]
            variants = {v: {'system': self.experiment['systems'][v], 'user': pair['user'], 'model': self.experiment['models'][v]}
                        for v in ('original', 'changed')}
            self.speed = t.speed_probe(self.experiment['models']['original'], variants)
            self.add_metrics(speed_metrics(self.speed), 'speed', {'speed': self.speed['evidence_ids'][0]})
        elif step == 'check':
            self.claims, dropped = self.checker.check(self.claims)
            self.dropped.extend(dropped)
            for row in dropped:
                self.emit('claim_dropped', **row)
        elif step == 'report':
            return

    def run(self, company):
        index = 0

        def chunk(_markovian_prompt):
            nonlocal index
            step = STEPS[index]
            self.step, self.why = step, DEFAULT_WHY[step]
            old_usage = len(self.model_usage)
            try:
                self.guard.check()
                choices = self.experiment_choices() if step == 'experiment' else [{}]
                if not choices:
                    raise ValueError('No feasible hosted experiment')
                fallback = {'why': DEFAULT_WHY[step], 'tool': step, 'args': choices[0], 'done': step == 'report'}
                # Markovian carryover is the actual input to the next planner, not decorative.
                compact = {'question': self.question, **self.context}
                compact['carryover'] = _markovian_prompt.split('CARRYOVER: ', 1)[1].split('\nEnd a nonfinal', 1)[0]
                if step == 'experiment':
                    compact['ranked_hypotheses'] = compact.get('ranked_hypotheses', [])[:4]
                plan = self.planner.plan(step, compact, fallback, {step: choices})
                self.why = plan['why']
                self.emit('step_started')
                if plan['done'] and step != 'report':
                    self.partial_reason = 'Planner completed before all investigation stages'
                else:
                    self.emit('tool_called', tool=plan['tool'], args=plan['args'])
                    self.do_step(step, plan['args'], company)
                self.guard.check()
            except BudgetExceeded as exc:
                self.partial_reason = str(exc)
            except Exception as exc:
                self.partial_reason = f'{step} unavailable: {type(exc).__name__}'
                self.logger.write('agent', 'step_failed', step=step, ok=False, error_class=type(exc).__name__)
            self.emit('budget', **self.guard.snapshot())
            index += 1
            done = bool(self.partial_reason) or index == len(STEPS)
            # Only this wrapper writes markers. Raw model text is never passed to Markovian.
            # Keep a compact list of evidence IDs and a finding; no raw rows/history.
            state = json.dumps({'evidence_ids': self.tools.ids[-4:], 'finding': self.context.get('finding', ''),
                                'next_step': STEPS[index] if not done else 'complete'}, ensure_ascii=True)
            response = {'text': self.why + (' [TASK_COMPLETE]' if done else ' [STATE_CHECKPOINT]' + state)}
            usages = self.model_usage[old_usage:]
            if usages and all(type(u.get(k)) is int for u in usages for k in ('prompt_tokens', 'completion_tokens')):
                response['usage'] = {k: sum(u[k] for u in usages) for k in ('prompt_tokens', 'completion_tokens')}
            return response

        run = Markovian({'maxChunks': len(STEPS), 'carryoverTokens': 512}, logger=self.logger, log_stream='agent_markovian').run(
            'Investigate ' + company, chunk, reflect=False)
        self.current_run = run
        eid = self.tools.observe('measurement', {'runs': [*self.history, run]}, 'Markovian run accounting including every run in the log', 'Markovian telemetry')
        metrics = {}
        for i, historical in enumerate([*self.history, run]):
            actual = run_efficiency(historical['chunks'], historical['chunkConfig']) if 'chunks' in historical else historical['actual']
            net = actual['standardCost'] - actual['markovianCost']
            metrics[f'markovian/{i}/net_tokens'] = net
            metrics[f'markovian/{i}/net_percent'] = net / actual['standardCost'] * 100 if actual['standardCost'] else 0.
        self.add_metrics(metrics, 'markovian', {'runs': eid})
        budget = self.guard.snapshot()
        eid = self.tools.observe('measurement', budget, 'BudgetGuard physical attempts and monotonic elapsed time', 'Runtime telemetry')
        self.add_metrics({f'budget/{k}': v for k, v in budget.items() if type(v) in (int, float)}, 'budget', {'budget': eid})
        self.claims, dropped = self.checker.check(self.claims)
        self.dropped.extend(dropped)
        for row in dropped:
            self.emit('claim_dropped', **row)
        verified = {c['id']: c['value'] for c in self.claims}
        report = self.build_report(company, verified)
        if report['top_finding']:
            self.memory.add(content=report['top_finding'], source=self.run_id, layer='working',
                            type='finding', entities=[company], derived_from=self.tools.ids[-4:])
        self.emit('done', status=report['status'], report_url=f'/investigations/{self.run_id}/report')
        return report

    def build_report(self, company, verified):
        quality_pass = verified.get('quality/passed', 0) >= 18 and verified.get('quality/judged') == 20
        tested = self.experiment['lever'] if self.experiment else None
        fixes = []
        for candidate in self.candidates:
            if candidate['claim_id'] not in verified:
                continue
            c = dict(candidate)
            if c['lever'] == tested and (c['lever'] != 'model_switch' or self.experiment['models']['changed'] in self.tools.hosted_choices(c['tokenizer'])):
                c['status'] = 'provisional; native review pending' if quality_pass else 'rejected'
                c['reason'] = 'Automated same-facts check passed; native review is pending.' if quality_pass else 'Automated quality bar failed or could not be completed.'
                c['model_label'] = self.experiment['model_label']
                c['experiment_evidence_ids'] = self.experiment['evidence_ids']
            fixes.append(c)
        speed_status = 'not measured'
        if verified.get('speed/completed_runs') == 8:
            low = verified.get('speed/latency_s/difference_min')
            high = verified.get('speed/latency_s/difference_max')
            spread = max(verified['speed/latency_s/' + v + '_max'] - verified['speed/latency_s/' + v + '_min']
                         for v in ('original', 'changed'))
            difference = verified['speed/latency_s/paired_difference']
            speed_status = 'inconclusive' if low is None or low <= 0 <= high or abs(difference) <= spread else ('changed slower' if low > 0 else 'changed faster')
        money = any(k.startswith('baseline/' + getattr(self, 'config', {}).get('model_in_use', '?') + '/') and k.endswith('/monthly_inr') for k in verified)
        baseline_valid = any(k.endswith('_cost_share') or k.endswith('_share') for k in verified)
        return {'schema_version': '1', 'id': self.run_id, 'company': company,
                'status': 'partial' if self.partial_reason else 'complete', 'partial_reason': self.partial_reason,
                'needs_input': self.needs_input, 'top_finding': getattr(self, 'finding', None) if baseline_valid else None,
                'top_fix': next((f['lever'] for f in fixes if f['status'].startswith('provisional')), None),
                'money_status': 'quoted provider scenario; content only' if money else 'money unavailable',
                'quoted_price': {k: v for k, v in (select_price(self.tools.prices, self.config['model_in_use']) or {}).items()
                                 if k in ('model', 'provider', 'source_url', 'fetched_at')} if hasattr(self, 'config') else None,
                'claims': self.claims, 'dropped_claims': self.dropped, 'fixes': fixes,
                'quality_status': 'automated pass; native review pending' if quality_pass else 'failed or not fully judged',
                'review_status': 'pending', 'speed_status': speed_status,
                'remembered': self.remembered, 'remembered_fields': ['volume', 'target', 'model', 'reply-language constraints'] if self.remembered else [],
                'experiment': {k: self.experiment[k] for k in ('lever', 'models', 'model_label', 'accounting', 'evidence_ids')} if self.experiment else None,
                'markovian_runs': [{'log_index': i, 'token_label': r['tokenLabel'], 'claim_prefix': f'markovian/{i}/'} for i, r in enumerate([*self.history])]
                    + [{'log_index': len(self.history), 'token_label': self.current_run['tokenLabel'], 'claim_prefix': f'markovian/{len(self.history)}/'}],
                'limitations': ['Synthetic paired translations and all native reviews remain pending.',
                               'Baseline reconstructs completed whole-chat content billing; excludes templates, retries and unpublished cache discounts.',
                               'A/B money scales one sampled last-turn response per chat, using the company tokenizer and quoted price. Do not compare it directly with the whole-chat baseline.',
                               'Hosted family membership is not proof of deployed-model quality or speed. Stand-in results require validation on the actual model.',
                               'Untested hypotheses are estimates, not validated recommendations.',
                               'Signed Markovian accounting is the reference history-replay counterfactual; it is not a measured second execution.'],
                'evidence_ids': list(self.tools.ids)}
