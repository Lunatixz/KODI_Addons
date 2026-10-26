#   Copyright (C) 2026 Lunatixz
#
#
# This file is part of Kodi PowerToys
#
# Kodi PowerToys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Kodi PowerToys is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kodi PowerToys.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-
from globals import *
import base64, json, os, threading, urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

WEB_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web')

class PowerToysHandler(BaseHTTPRequestHandler):
    server_version = 'PowerToys/1.2.0'

    def log_message(self, fmt, *args):
        log('webserver: %s - %s' % (self.address_string(), fmt % args))

    @property
    def svc(self):
        return self.server.service

    def _check_auth(self):
        if not REAL_SETTINGS.getSettingBool('WebServer_Auth'): return True
        header = self.headers.get('Authorization', '')
        if not header.startswith('Basic '): return False
        try:
            expected = '%s:%s' % (REAL_SETTINGS.getSetting('WebServer_User'), REAL_SETTINGS.getSetting('WebServer_Pass'))
            return base64.b64decode(header[6:]).decode('utf-8') == expected
        except Exception:
            return False

    def _send_auth_challenge(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Kodi PowerToys"')
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'401 Unauthorized')

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status=200):
        body = html.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f: body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _serve_index(self):
        self._send_file(os.path.join(WEB_ROOT, 'index.html'), 'text/html; charset=utf-8')

    def _local_ip(self):
        return self.svc.sync._local_ip if self.svc and self.svc.sync else '127.0.0.1'

    def _get_instances(self):
        instances = [{'label': 'This device (%s)' % self._local_ip(), 'ip': self._local_ip(), 'port': 'local', 'self': True}]
        if self.svc and self.svc.sync:
            with self.svc.sync._lock:
                for name, peer in self.svc.sync.peers.items():
                    instances.append({'label': '%s (%s:%d)' % (peer.get('host', name), peer['ip'], peer['port']),
                                      'ip': peer['ip'], 'port': peer['port'], 'self': False})
        return instances

    def _encode_commands(self, commands):
        raw = json.dumps(commands, separators=(',', ':')).encode('utf-8')
        return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')

    def _decode_commands(self, encoded):
        try:
            padding = 4 - len(encoded) % 4
            if padding != 4: encoded += '=' * padding
            return json.loads(base64.urlsafe_b64decode(encoded))
        except Exception:
            return None

    def _execute_local(self, commands):
        responses = []
        for cmd in commands:
            method = cmd.get('method', '')
            if method == 'PowerToys.Wake':
                woken = self.svc.sync.wake_peers() if (self.svc and getattr(self.svc, 'sync', None)) else 0
                responses.append({'jsonrpc': '2.0', 'id': ADDON_ID, 'result': 'OK' if woken else 'No MACs configured'})
                continue
            cmd = dict(cmd)
            cmd['jsonrpc'] = '2.0'
            cmd['id'] = ADDON_ID
            resp = loadJSON(xbmc.executeJSONRPC(dumpJSON(cmd)))
            responses.append(resp)
            if method == 'VideoLibrary.Scan' and self.svc and getattr(self.svc, 'sync', None):
                path = (cmd.get('params') or {}).get('directory') or None
                self.svc.sync.queue_msg('ScanLibrary', {'path': path})
        return responses

    def _execute_remote(self, ip, port, commands):
        responses = []
        for cmd in commands:
            cmd = dict(cmd)
            cmd['jsonrpc'] = '2.0'
            cmd['id'] = ADDON_ID
            url = 'http://%s:%s/jsonrpc' % (ip, port)
            req = urllib.request.Request(url, data=json.dumps(cmd).encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            resp = urllib.request.urlopen(req, timeout=10)
            responses.append(loadJSON(resp.read()))
        return responses

    def do_GET(self):
        if not self._check_auth(): return self._send_auth_challenge()
        path = self.path.split('?')[0]
        query = self.path.split('?')[1] if '?' in self.path else ''

        if path == '/' or path == '/index.html':
            return self._serve_index()
        if path == '/style.css':
            return self._send_file(os.path.join(WEB_ROOT, 'style.css'), 'text/css')
        if path == '/app.js':
            return self._send_file(os.path.join(WEB_ROOT, 'app.js'), 'application/javascript')
        if path.startswith('/run/'):
            return self._serve_index()

        if path == '/api/v1/instances':
            return self._send_json({'instances': self._get_instances()})

        if path == '/report':
            try:
                report = self.svc._cachedReport() if self.svc else 'Service not ready'
            except Exception as e:
                report = 'Report failed: %s' % e
            html = ('<!DOCTYPE html><html><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
                    '<title>Kodi PowerToys - Health Report</title><style>'
                    'body{font-family:monospace;background:#1a1a2e;color:#a0d0a0;padding:16px}'
                    'pre{white-space:pre-wrap;word-break:break-all}</style></head><body><pre>%s</pre></body></html>'
                    % report.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
            return self._send_html(html)

        if path == '/log':
            from urllib.parse import parse_qs
            params = parse_qs(query)
            fname = 'kodi.old.log' if params.get('file', [''])[0] == 'old' else 'kodi.log'
            try:
                logdir = xbmcvfs.translatePath('special://logpath/')
                fpath = os.path.join(logdir, fname)
                size = os.path.getsize(fpath)
                with open(fpath, 'rb') as f:
                    if size > 2 * 1024 * 1024:  # ponytail: tail-only, cap read at 2MB
                        f.seek(size - 2 * 1024 * 1024)
                    raw = f.read()
                text = raw.decode('utf-8', 'replace')
                nlines = int(params.get('lines', ['0'])[0] or 0)
                if nlines > 0:
                    text = '\n'.join(text.splitlines()[-nlines:])
                body = text.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
            except Exception as e:
                self._send_json({'error': str(e)}, 500)
            return

        if path == '/api/v1/qr':
            from urllib.parse import parse_qs
            params = parse_qs(query)
            commands_raw = params.get('commands', [''])[0]
            commands = loadJSON(commands_raw)
            if not commands: return self._send_json({'error': 'invalid or missing commands parameter'}, 400)
            if isinstance(commands, dict): commands = [commands]
            encoded = self._encode_commands(commands)
            url = 'http://%s:%d/run/%s' % (self._local_ip(), self.server.server_address[1], encoded)
            return self._send_json({'url': url, 'encoded': encoded, 'commands': commands})

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if not self._check_auth(): return self._send_auth_challenge()
        path = self.path.split('?')[0]

        if path == '/wake':
            woken = self.svc.sync.wake_peers() if (self.svc and getattr(self.svc, 'sync', None)) else 0
            return self._send_json({'woken': woken})

        if path == '/exec':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length))
            except Exception:
                return self._send_json({'error': 'invalid JSON body'}, 400)

            commands = body.get('commands', [])
            targets = body.get('instances', ['local'])
            if not commands: return self._send_json({'error': 'no commands provided'}, 400)

            results = []
            for target in targets:
                try:
                    if target == 'local' or (isinstance(target, dict) and target.get('self')):
                        responses = self._execute_local(commands)
                        results.append({'instance': 'local', 'status': 'ok', 'responses': responses})
                    elif isinstance(target, dict):
                        responses = self._execute_remote(target['ip'], target['port'], commands)
                        results.append({'instance': '%s:%s' % (target['ip'], target['port']), 'status': 'ok', 'responses': responses})
                    elif isinstance(target, str) and ':' in target:
                        ip, port = target.rsplit(':', 1)
                        responses = self._execute_remote(ip, port, commands)
                        results.append({'instance': target, 'status': 'ok', 'responses': responses})
                    else:
                        results.append({'instance': str(target), 'status': 'error', 'error': 'unknown target format'})
                except Exception as e:
                    label = target if isinstance(target, str) else '%s:%s' % (target.get('ip'), target.get('port'))
                    results.append({'instance': label, 'status': 'error', 'error': str(e)})
            return self._send_json({'results': results})

        self.send_response(404)
        self.end_headers()


class PowerToysHTTPServer(HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr, service):
        self.service = service
        super().__init__(addr, PowerToysHandler)


_server = None
_thread = None

def start_server(service):
    global _server, _thread
    if _server: return
    port = REAL_SETTINGS.getSettingInt('WebServer_Port') or 9090
    try:
        _server = PowerToysHTTPServer(('0.0.0.0', port), service)
        _thread = threading.Thread(target=_server.serve_forever, daemon=True)
        _thread.start()
        log('webserver started on port %d' % port)
    except Exception as e:
        log('webserver failed to start: %s' % e, xbmc.LOGERROR)
        _server = None

def stop_server():
    global _server, _thread
    if _server:
        _server.shutdown()
        _server.server_close()
        _server = None
        _thread = None
        log('webserver stopped')
