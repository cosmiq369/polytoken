import pytest

from polytoken.company_db import seed_company_db
from polytoken.config import load_settings
from polytoken.logs import JsonlLogger
from polytoken.measurement_report import verify_and_save
from polytoken.zetaris import ZetarisClient
from polytoken.company_db import ROOT

pytestmark = pytest.mark.live


def test_seed_company_db_idempotent_live():
    settings = load_settings()
    assert seed_company_db(settings) == seed_company_db(settings) == {
        'samudra.bot_config':1, 'samudra.chats':188, 'swara.bot_config':1,
        'swara.chats':180, 'raitu.bot_config':1, 'raitu.chats':160, 'paisa.bot_config':1, 'paisa.chats':160, 'reference.sentences':118, 'reference.prices':11}


def test_zetaris_sees_both_company_schemas():
    with ZetarisClient(load_settings()) as client:
        for company in ('samudra','swara','raitu','paisa'):
            rows = client.query(f'SELECT COUNT(*) AS turns, COUNT(DISTINCT chat_id) AS chats FROM company_systems.{company}__chats')
            assert int(rows[0]['turns']) == {'samudra':188,'swara':180,'raitu':160,'paisa':160}[company] and int(rows[0]['chats']) == 40
            rows = client.query(f'SELECT DISTINCT review_status FROM company_systems.{company}__chats')
            assert rows == [{'review_status':'pending'}]


def test_checked_federation_both_companies():
    settings = load_settings()
    logger = JsonlLogger(secrets=settings.secrets)
    with ZetarisClient(settings,logger=logger) as client:
        rows, shares = verify_and_save(client,logger, sample_dir=ROOT / 'logs/live_validation')
    assert {r['company'] for r in rows} == {'samudra','swara','raitu','paisa'}
    assert {r['part'] for r in rows} == {'system_prompt','user','assistant'}
    assert all(r['chat_count']==40 for r in shares)
