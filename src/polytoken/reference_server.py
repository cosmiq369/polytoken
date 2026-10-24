"""The price URL already registered with Zetaris, owned by polytoken serve."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import httpx

from .prices import load_prices
from .reference import ROOT


def ensure_reference_table(client, logger):
    """Refresh only this application's REST metadata when its old schema is empty."""
    rows = client.query('SELECT * FROM polytoken_reference.prices')
    if rows:
        return
    client.execute('DROP LIGHTNING DATABASE TABLE polytoken_reference.prices')
    client.execute('''CREATE LIGHTNING REST TABLE prices FROM polytoken_reference
REQUEST(endpoint "http://host.docker.internal:55433/prices.json", method "GET",
http_encoding "URLENCODED", response_type "JSON") HEADER() BODY()''')
    rows = client.query('SELECT * FROM polytoken_reference.prices')
    if not rows:
        raise RuntimeError('REST prices still empty after metadata refresh')
    logger.write('data_setup', 'price_schema_refreshed', rows=len(rows), ok=True)


def ensure_reference_server(logger, port=55433):
    prices = load_prices(ROOT / 'prices.json')
    content = json.dumps(prices).encode()
    schema = (ROOT / 'prices.schema.json').read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = {'/prices.json': content, '/prices.schema.json': schema}.get(self.path)
            if body is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            logger.write('reference_http', 'request', message=fmt % args)
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    except OSError:
        response = httpx.get(f'http://127.0.0.1:{port}/prices.json', timeout=5.)
        response.raise_for_status()
        if response.json() != prices:
            raise RuntimeError('Registered reference port is occupied by different data') from None
        return None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.write('reference_http', 'listening', port=port)
    return server
