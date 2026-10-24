import pytest

from polytoken.agent.budget import BudgetGuard
from polytoken.agent.runtime import discover_hosted
from polytoken.config import load_settings
from polytoken.logs import JsonlLogger
from polytoken.meterless.evidence import EvidenceStore
from polytoken.meterless.world_model import WorldModel
from polytoken.reference_server import ensure_reference_server, ensure_reference_table
from polytoken.tools import InvestigationTools
from polytoken.zetaris import ZetarisClient

pytestmark = pytest.mark.live


def test_live_catalogue_intersection():
    result = discover_hosted(load_settings(), JsonlLogger())
    assert result['live_fetched_at']
    assert any(result['families'].values())
    assert all(not models for family, models in result['families'].items() if 'Qwen 3' in family)


def test_live_tools_measure_and_verified_prices(tmp_path):
    settings = load_settings()
    logger = JsonlLogger()
    server = ensure_reference_server(logger)
    try:
        with ZetarisClient(settings, logger=logger) as client, WorldModel(tmp_path / 'world.sqlite', logger=logger) as world:
            ensure_reference_table(client, logger)
            tool = InvestigationTools(client, None, EvidenceStore(world), BudgetGuard(), logger, catalogue={'families': {}})
            config, ids = tool.load_company('samudra')
            result = tool.measure('samudra', config, ids)
            assert config['model_in_use'] == 'unsloth/Llama-3.2-3B-Instruct'
            assert len(tool.prices) == 7
            assert result['metrics']['baseline/unsloth/Llama-3.2-3B-Instruct/monthly_inr'] > 0
            assert tool.budget.counts['sql'] == 4
    finally:
        if server:
            server.shutdown()
            server.server_close()
