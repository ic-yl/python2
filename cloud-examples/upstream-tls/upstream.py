"""Owned fixture that selects a certificate using the requested TLS name."""

import json
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


SERVER = Path('/server')


def context_for(label):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(SERVER/(label+'.pem'), SERVER/(label+'.key'))
    return context


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({'fixture': 'upstream-tls', 'path': self.path, 'sni': self.connection.course_sni,
                           'served_name': self.connection.course_name}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    contexts = {name: context_for(name) for name in ('identity.lab.test', 'api.lab.test', 'reports.lab.test')}
    default = contexts['identity.lab.test']

    def select(connection, requested, _current):
        name = requested if requested in contexts else 'identity.lab.test'
        connection.context = contexts[name]
        connection.course_name = name
        connection.course_sni = requested

    default.sni_callback = select
    with HTTPServer(('0.0.0.0', 9443), Handler) as server:
        server.socket = default.wrap_socket(server.socket, server_side=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
