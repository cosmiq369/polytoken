import pytest

from polytoken.company_db import seed_company_db
from polytoken.config import load_settings
from polytoken.logs import JsonlLogger
from polytoken.measurement_report import verify_and_save
from polytoken.zetaris import ZetarisClient

pytestmark = pytest.mark.live


def test_seed_company_db_idempotent_live():
    settings = load_settings()
    assert seed_company_db(settings) == seed_company_db(settings) == {
        'samudra.bot_config':1, 'samudra.chats':223, 'swara.bot_config':1,
        'swara.chats':223, 'reference.sentences':118, 'reference.prices':7}


def test_zetaris_sees_both_company_schemas():
    with ZetarisClient(load_settings()) as client:
        for company in ('samudra','swara'):
            rows = client.query(f'SELECT COUNT(*) AS turns, COUNT(DISTINCT chat_id) AS chats FROM company_systems.{company}__chats')
            assert int(rows[0]['turns']) == 223 and int(rows[0]['chats']) == 50
            rows = client.query(f'SELECT DISTINCT review_status FROM company_systems.{company}__chats')
            assert rows == [{'review_status':'pending'}]


def test_checked_federation_both_companies():
    settings = load_settings()
    logger = JsonlLogger(secrets=settings.secrets)
    with ZetarisClient(settings,logger=logger) as client:
        rows, shares = verify_and_save(client,logger)
    assert {r['company'] for r in rows} == {'samudra','swara'}
    assert {r['part'] for r in rows} == {'system_prompt','user','assistant'}
    assert all(r['chat_count']==50 for r in shares)
