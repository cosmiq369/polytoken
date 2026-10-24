"""Archive current measurement evidence through Zetaris before replacing a demo."""
import argparse
from pathlib import Path
from polytoken.company_db import COMPANIES
from polytoken.config import load_settings
from polytoken.logs import JsonlLogger
from polytoken.measure import read_inputs, utcnow
from polytoken.measurement_report import checked_ratios
from polytoken.zetaris import ZetarisClient


def snapshot(destination):
    settings = load_settings()
    logger = JsonlLogger(secrets=settings.secrets)
    sample = JsonlLogger(destination, run_id=logger.run_id, secrets=settings.secrets)
    with ZetarisClient(settings, logger=logger) as client:
        for company in COMPANIES:
            start = utcnow()
            inputs, provenance = read_inputs(client, company)
            query = f"SELECT * FROM company_systems.measurements__latest_token_counts WHERE company='{company}'"
            counts = client.query(query, page_limit=10000)
            checked_ratios(counts, inputs)
            sample.write('measurement_snapshot', 'verified_snapshot', company=company,
                         inputs=inputs, counts=counts, source='Zetaris SQL',
                         query=provenance['source_query']+';\n'+query,
                         fetched_at=utcnow(), time_window={'start':start,'end':utcnow()}, ok=True)
            print(company, len(inputs), len(counts), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    snapshot(parser.parse_args().destination)
