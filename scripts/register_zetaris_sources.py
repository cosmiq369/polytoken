#!/usr/bin/env python3
"""Idempotent local registration using the running UI's management SQL API."""
from polytoken.config import load_settings
from polytoken.logs import JsonlLogger
from polytoken.zetaris import ZetarisClient, ZetarisError

TABLES = ('samudra__bot_config', 'samudra__chats', 'swara__bot_config', 'swara__chats',
          'raitu__bot_config', 'raitu__chats', 'paisa__bot_config', 'paisa__chats',
          'reference__sentences', 'reference__prices', 'measurements__batches',
          'measurements__token_counts', 'measurements__latest_token_counts')
REST_SQL = '''CREATE LIGHTNING REST TABLE prices FROM polytoken_reference
REQUEST(endpoint "http://host.docker.internal:55433/prices.json", method "GET",
http_encoding "URLENCODED", response_type "JSON") HEADER() BODY()'''


def quoted(value):
    # Spark/Lightning string literals support backslash escaping.
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def register(settings, client):
    settings.require_company_db()
    sources = {row[0].lower() for row in client.execute('SHOW DATASOURCES')['data']}
    if 'company_systems' not in sources:
        options = {'jdbcdriver': 'org.postgresql.Driver',
                   'jdbcurl': 'jdbc:postgresql://host.docker.internal:55432/company_systems',
                   'username': settings.company_db_user, 'password': settings.company_db_password,
                   'schema': 'public', 'fetchsize': '1000'}
        client.execute('CREATE DATASOURCE company_systems OPTIONS (' +
                       ', '.join(key + ' ' + quoted(value) for key, value in options.items()) + ')')
    # REGISTER refreshes/upserts metadata; selected names exclude PostgreSQL indexes.
    client.execute('REGISTER DATASOURCE TABLES (' + ', '.join(quoted(t) for t in TABLES) + ') FROM company_systems')
    databases = {row[0].lower() for row in client.execute('SHOW LIGHTNING DATABASES')['data']}
    if 'polytoken_reference' not in databases:
        client.execute('CREATE LIGHTNING DATABASE polytoken_reference OPTIONS ()')
    try:
        client.query('SELECT count(*) AS n FROM polytoken_reference.prices')
    except ZetarisError as exc:
        if 'TABLE_OR_VIEW_NOT_FOUND' not in str(exc):
            raise
        client.execute(REST_SQL)
    counts = {}
    for name in TABLES:
        counts[name] = int(client.query(f'SELECT count(*) AS n FROM company_systems.{name}')[0]['n'])
    counts['rest_prices'] = int(client.query('SELECT count(*) AS n FROM polytoken_reference.prices')[0]['n'])
    return counts


def main():
    settings = load_settings()
    logger = JsonlLogger(secrets=settings.secrets)
    try:
        with ZetarisClient(settings, logger=logger) as client:
            counts = register(settings, client)
        logger.write('data_setup', 'register_sources', ok=True, counts=counts,
                     sources=['company_systems', 'polytoken_reference.prices'])
        for name, count in counts.items():
            print(f'{name}: {count} rows')
        return 0
    except Exception as exc:
        logger.write('data_setup', 'register_sources', ok=False, error_class=type(exc).__name__)
        print(f'Registration failed: {type(exc).__name__}; inspect redacted logs/zetaris_admin.jsonl')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
