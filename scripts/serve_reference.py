"""Expose only the empty/current price list and its schema to local Zetaris."""
import argparse
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from polytoken.logs import JsonlLogger

ROOT = Path(__file__).resolve().parents[1] / 'data/reference'
logger = JsonlLogger()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        name = self.path.lstrip('/')
        if name not in ('prices.json', 'prices.schema.json'):
            self.send_error(404)
            return
        content = (ROOT / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        logger.write('reference_http', 'request', message=format % args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=55433)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    logger.write('reference_http', 'listening', port=args.port, pid=os.getpid())
    print(f'Reference JSON listening on 127.0.0.1:{args.port}', flush=True)
    server.serve_forever()
