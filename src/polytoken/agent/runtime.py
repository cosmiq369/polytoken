"""Production dependency injection; the investigation never opens hidden fixtures."""
from contextlib import ExitStack
import json
from pathlib import Path

import httpx

from .budget import BudgetGuard
from .runner import Investigation
from ..config import load_settings
from ..llm import NvidiaGenerator, shared_limiter
from ..logs import JsonlLogger
from ..meterless.evidence import EvidenceStore
from ..meterless.hmem import HMem
from ..meterless.world_model import WorldModel
from ..reference import load_hosted
from ..tools import InvestigationTools, now
from ..zetaris import ZetarisClient


def discover_hosted(settings, logger):
    declared = load_hosted()
    shared_limiter(settings.nvidia_rpm).acquire()
    started = now()
    with httpx.Client(timeout=20.) as client:
        response = client.get(settings.nvidia_base_url + '/models', headers={'Authorization': 'Bearer ' + settings.nvidia_api_key})
        response.raise_for_status()
        rows = response.json()['data']
    live = {row['id'] for row in rows if isinstance(row, dict) and isinstance(row.get('id'), str)}
    result = {**declared, 'families': {f: [m for m in models if m in live] for f, models in declared['families'].items()},
              'live_fetched_at': now(), 'live_query': settings.nvidia_base_url + '/models'}
    logger.write('catalogue', 'live_intersection', ok=True, source=result['live_query'],
                 query='GET /models', time_window={'start': started, 'end': now()}, fetched_at=now(), families=result['families'])
    return result


def historical_runs(log_dir, agent_model=None):
    path = Path(log_dir) / 'agent_markovian.jsonl'
    if not path.exists():
        return []
    runs = [row for line in path.read_text().splitlines() if (row := json.loads(line)).get('event') == 'run']
    calls = Path(log_dir) / 'llm_calls.jsonl'
    if calls.exists() and agent_model:
        unknown = {row['run_id'] for line in calls.read_text().splitlines() if (row := json.loads(line)).get('model') == agent_model
                   and row.get('ok') is False and row.get('prompt_tokens') is None}
        for run in runs:
            if run['run_id'] in unknown:
                run['tokenLabel'] = 'estimated'
                run['usage_note'] = 'Failed Nemotron attempts have unknown usage; the counterfactual excludes that unknown usage.'
    return runs


def investigate(company, *, question='', monthly_chats=None, latency_target_s=None,
                env_file='.env', run_id=None, event_sink=None, log_dir='logs', state_dir='.cache/state', catalogue=None):
    settings = load_settings(env_file)
    logger = JsonlLogger(log_dir, run_id=run_id, secrets=settings.secrets)
    # These are composition-root startup reads, before the investigation begins.
    history = historical_runs(log_dir, settings.agent_model)
    catalogue = catalogue if catalogue is not None else discover_hosted(settings, logger)
    with ExitStack() as stack:
        world = stack.enter_context(WorldModel(Path(state_dir) / 'world.sqlite', logger=logger))
        memory = stack.enter_context(HMem(path=Path(state_dir) / 'memory.sqlite', logger=logger))
        client = stack.enter_context(ZetarisClient(settings, logger=logger, timeout_s=20.))
        generator = stack.enter_context(NvidiaGenerator(settings, logger=logger, max_tokens=640, timeout_s=35.))
        guard = BudgetGuard()
        toolset = InvestigationTools(client, generator.generate, EvidenceStore(world), guard, logger, catalogue=catalogue)
        toolset.observe('query_result', catalogue, 'GET ' + catalogue.get('live_query', '/models'), 'NVIDIA catalogue intersected with verified allowlist')
        agent = Investigation(toolset, memory, question=question, monthly_chats=monthly_chats,
                              latency_target_s=latency_target_s, event_sink=event_sink, historical_runs=history)
        report = agent.run(company)
        directory = Path(log_dir) / 'investigations'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (report['id'] + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        logger.write('agent', 'report', report=report)
        return report, agent.events
