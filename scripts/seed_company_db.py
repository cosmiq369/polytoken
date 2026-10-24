"""Idempotently load fictional company systems and the declared reference corpus."""
import json
from polytoken.company_db import seed_company_db
from polytoken.config import load_settings
from polytoken.logs import JsonlLogger

if __name__ == '__main__':
    settings = load_settings()
    logger = JsonlLogger(secrets=settings.secrets)
    try:
        print(json.dumps(seed_company_db(settings, logger), indent=2))
        print('Money unavailable: no verified prices are loaded.')
    except Exception as exc:
        print('Seeding failed:', type(exc).__name__)
        raise SystemExit(1) from None
