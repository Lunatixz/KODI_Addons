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
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

WEB_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web')

_INTRO_CACHE = None   # full JSONRPC.Introspect, fetched once per process
_EP_CACHE = {'ts': 0, 'items': None}   # all-episodes memo (episodeid-only methods)

def _introspect():
    global _INTRO_CACHE
    if _INTRO_CACHE is None:
        _INTRO_CACHE = sendJSON({"method": "JSONRPC.Introspect", "params": {}}).get('result') or {}
    return _INTRO_CACHE

def _type_str(el, intro):
    # unwrap one union/schema element to a plain type string (Kodi unions optional
    # params as [{type:integer},{type:null}] - raw arrays stringify to [object Object])
    if isinstance(el, str): return None if el == 'null' else el
    if isinstance(el, list):
        for e2 in el:
            r = _type_str(e2, intro)
            if r: return r
        return None
    if isinstance(el, dict):
        et = el.get('type')
        if isinstance(et, str): return None if et == 'null' else et
        if isinstance(et, list):
            for e2 in et:
                r = _type_str(e2, intro)
                if r: return r
        ref = el.get('$ref')
        if ref:
            td = intro.get('types', {}).get(ref) or {}
            if isinstance(td.get('type'), str): return td['type']
            if isinstance(td.get('type'), (list, dict)):
                r = _type_str(td.get('type'), intro)
                if r: return r
    return None

def _param_type(param, intro):
    t = param.get('type')
    if isinstance(t, str): return t
    if isinstance(t, (list, dict)):
        for el in (t if isinstance(t, list) else [t]):
            r = _type_str(el, intro)
            if r: return r
    ref = param.get('$ref')
    if ref:
        td = intro.get('types', {}).get(ref) or {}
        if isinstance(td.get('type'), str): return td['type']
        if isinstance(td.get('type'), (list, dict)):
            r = _type_str(td.get('type'), intro)
            if r: return r
        if 'enum' in td: return 'string'
        if td: return 'object'
    return 'string'

def _resolve_enum(param, intro):
    # enums live at any depth: inline, array items, union elements, a $ref'd type
    # def, or that def's own items (List.Attributes style) - walk the worklist
    work, seen = [param], set()
    while work:
        src = work.pop(0)
        if not isinstance(src, dict) or id(src) in seen: continue
        seen.add(id(src))
        if 'enum' in src: return src['enum']
        for key in ('items', 'type'):
            v = src.get(key)
            if isinstance(v, dict): work.append(v)
            elif isinstance(v, list): work.extend(x for x in v if isinstance(x, dict))
        ref = src.get('$ref')
        if ref and ref not in seen:
            seen.add(ref)
            td = intro.get('types', {}).get(ref)
            if isinstance(td, dict): work.append(td)
    return None

def _first_ref(el):
    # first $ref anywhere in a schema node (inline, unions, items)
    if isinstance(el, dict):
        if el.get('$ref'): return el['$ref']
        for k in ('type', 'items'):
            r = _first_ref(el.get(k))
            if r: return r
    elif isinstance(el, list):
        for x in el:
            r = _first_ref(x)
            if r: return r
    return None

def _schema_for(method):
    intro = _introspect()
    m = intro.get('methods', {}).get(method)
    if not m: return None
    params = []
    for p in (m.get('params') or []):
        if not isinstance(p, dict) or not p.get('name'): continue
        d = {'name': p['name'], 'required': bool(p.get('required')), 'type': _param_type(p, intro)}
        if p.get('description'): d['description'] = p['description']
        enum = _resolve_enum(p, intro)
        prim = [v for v in enum if isinstance(v, (str, int, float, bool))] if enum else []
        if prim and d['type'] == 'object' and p.get('name') == 'properties':
            # schema quirk seen in the wild: 'properties' typed object although it is
            # semantically a string list - canonicalize so the UI shows checkboxes
            d['type'] = 'array'
            d['itemsEnum'] = prim
        elif prim and d['type'] == 'array':
            d['itemsEnum'] = prim
        elif prim:
            # primitives only - dropdown labels must never stringify to objects
            d['enum'] = prim
        if d['type'] == 'object':
            # structured object (sort/limits/...): expose the member fields so the
            # UI can render typed sub-controls instead of a raw {} box
            own = p.get('properties')
            src = own if isinstance(own, dict) else (intro.get('types', {}).get(_first_ref(p)) or {})
            props = src.get('properties')
            req_list = src.get('required') if isinstance(src.get('required'), list) else []
            if isinstance(props, dict):
                fields = []
                for fname, fspec in props.items():
                    if not isinstance(fspec, dict): continue
                    fd = {'name': fname, 'required': bool(fspec.get('required')) or fname in req_list,
                          'type': _param_type(fspec, intro)}
                    if fspec.get('description'): fd['description'] = fspec['description']
                    fe = _resolve_enum(fspec, intro)
                    if fe:
                        fp = [v for v in fe if isinstance(v, (str, int, float, bool))]
                        if fp: fd['enum'] = fp
                    fields.append(fd)
                if fields: d['fields'] = fields
        params.append(d)
    return {'method': method, 'description': m.get('description') or '', 'params': params}

def _options(kind, arg):
    # live value lists for dropdowns (IDs and names fetched from this Kodi instance)
    try:
        if kind == 'movies':
            items = sendJSON({"method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "year"]}}).get('result', {}).get('movies', [])
            return [{'value': i.get('movieid'), 'label': '%s (%s)' % (i.get('title') or '?', i.get('year') or '?')} for i in items]
        if kind == 'tvshows':
            items = sendJSON({"method": "VideoLibrary.GetTVShows", "params": {"properties": ["title"]}}).get('result', {}).get('tvshows', [])
            return [{'value': i.get('tvshowid'), 'label': i.get('title') or i.get('label') or '?'} for i in items]
        if kind == 'episodes':
            if arg:
                items = sendJSON({"method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": int(arg), "properties": ["title", "season", "episode"]}}).get('result', {}).get('episodes', [])
                return [{'value': e.get('episodeid'), 'label': 'S%02dE%02d %s' % (e.get('season') or 0, e.get('episode') or 0, e.get('title') or '')} for e in items]
            now = time.time()   # all-episodes list: N+1 query, memoized 5 min
            if _EP_CACHE['items'] is not None and now - _EP_CACHE['ts'] < 300: return _EP_CACHE['items']
            out = []
            for s in sendJSON({"method": "VideoLibrary.GetTVShows", "params": {"properties": ["title"]}}).get('result', {}).get('tvshows', []):
                eps = sendJSON({"method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": s.get('tvshowid'), "properties": ["title", "season", "episode"]}}).get('result', {}).get('episodes', [])
                for e in eps:
                    out.append({'value': e.get('episodeid'), 'label': '%s S%02dE%02d %s' % (s.get('title') or '', e.get('season') or 0, e.get('episode') or 0, e.get('title') or '')})
            _EP_CACHE['ts'] = now
            _EP_CACHE['items'] = out
            return out
        if kind == 'seasons':
            if not arg: return []
            items = sendJSON({"method": "VideoLibrary.GetSeasons", "params": {"tvshowid": int(arg)}}).get('result', {}).get('seasons', [])
            return [{'value': s.get('seasonid'), 'label': s.get('label') or ('Season %s' % s.get('season'))} for s in items]
        if kind == 'artists':
            items = sendJSON({"method": "AudioLibrary.GetArtists", "params": {}}).get('result', {}).get('artists', [])
            return [{'value': i.get('artistid'), 'label': str(i.get('artist') or i.get('label') or i.get('artistid'))} for i in items]
        if kind == 'albums':
            items = sendJSON({"method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "artist"]}}).get('result', {}).get('albums', [])
            out = []
            for i in items:
                a = i.get('artist')
                if isinstance(a, list): a = ', '.join(str(x) for x in a)
                out.append({'value': i.get('albumid'), 'label': '%s%s' % (i.get('title') or '?', ' - ' + a if a else '')})
            return out
        if kind == 'profiles':
            items = sendJSON({"method": "Profiles.GetProfiles", "params": {}}).get('result', {}).get('profiles', [])
            return [{'value': p.get('profileid'), 'name': str(p.get('name') or p.get('label') or ''),
                     'label': str(p.get('name') or p.get('label') or p.get('profileid'))} for p in items]
        if kind == 'addons':
            items = sendJSON({"method": "Addons.GetAddons", "params": {}}).get('result', {}).get('addons', [])
            return [{'value': i.get('addonid'), 'label': str(i.get('name') or i.get('label') or i.get('addonid'))} for i in items]
        if kind == 'sources':
            items = sendJSON({"method": "Files.GetSources", "params": {"media": "video"}}).get('result', {}).get('sources', [])
            return [{'value': i.get('file'), 'label': '%s (%s)' % (i.get('label') or '?', i.get('file'))} for i in items]
        if kind == 'playlists':
            items = sendJSON({"method": "Playlist.GetPlaylists", "params": {}}).get('result', {}).get('playlists', [])
            return [{'value': i.get('playlistid'), 'label': '%s #%s' % (i.get('type') or 'list', i.get('playlistid'))} for i in items]
        if kind == 'players':
            items = sendJSON({"method": "Player.GetActivePlayers", "params": {}}).get('result') or []
            if items:
                return [{'value': i.get('playerid'), 'label': str(i.get('type') or 'player') + ' player'} for i in items]
            return [{'value': 0, 'label': 'No active player (0)'}, {'value': 1, 'label': 'No active player (1)'}]
    except Exception as e:
        log('options(%s) failed: %s' % (kind, e), xbmc.LOGWARNING)
    return None

class PowerToysHandler(BaseHTTPRequestHandler):
    server_version = 'PowerToys/1.3.4'

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
        if path == '/qrcode.min.js':
            return self._send_file(os.path.join(WEB_ROOT, 'qrcode.min.js'), 'application/javascript')
        if path.startswith('/run/'):
            return self._serve_index()

        if path == '/api/v1/instances':
            return self._send_json({'instances': self._get_instances()})

        if path == '/api/v1/schema':
            from urllib.parse import parse_qs
            method = parse_qs(query).get('method', [''])[0]
            if not method: return self._send_json({'error': 'missing method parameter'}, 400)
            try:
                schema = _schema_for(method)
            except Exception as e:
                return self._send_json({'error': 'introspect failed: %s' % e}, 500)
            if not schema: return self._send_json({'error': 'method not found: %s' % method}, 404)
            return self._send_json(schema)

        if path == '/api/v1/options':
            from urllib.parse import parse_qs
            params = parse_qs(query)
            kind = params.get('kind', [''])[0]
            if not kind: return self._send_json({'error': 'missing kind parameter'}, 400)
            opts = _options(kind, params.get('tvshowid', [''])[0])
            if opts is None: return self._send_json({'error': 'unknown kind: %s' % kind}, 400)
            return self._send_json({'options': opts})

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


class PowerToysHTTPServer(ThreadingHTTPServer):
    # ThreadingHTTPServer: each request runs on its own daemon thread, so a slow
    # handler (/report walking a big library, a long /exec) can never block
    # shutdown() and hang Kodi's exit sequence
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
    port = REAL_SETTINGS.getSettingInt('WebServer_Port') or 9095
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
        try:
            _server.shutdown()   # stops the accept loop only; handler threads are daemons
            _server.server_close()
        except Exception as e:
            log('webserver stop error: %s' % e, xbmc.LOGWARNING)
        _server = None
        _thread = None
        log('webserver stopped')
