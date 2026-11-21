"""Synthetic HTTP boundary recorder. It connects only to the owned lab DB."""

import json
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit


class LabHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urlsplit(self.path)
        if route.path not in ('/identity', '/api/status', '/api/export'):
            self.send_error(404)
            return
        with socket.create_connection(('db', 5432), timeout=2):
            body = json.dumps({'source': 'api-fixture', 'path': route.path, 'query': route.query,
                               'host': self.headers.get('Host'), 'proto': self.headers.get('X-Forwarded-Proto'),
                               'peer': self.headers.get('X-Forwarded-For'), 'db_tcp_connected': True}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    with HTTPServer(('0.0.0.0', 8081), LabHandler) as server:
        server.serve_forever()
