#   Copyright (C) 2026 Lunatixz
#
#   PKBridge - Kodi-to-Plex bridge service
#   HTTP server: every Plex client call resolves to Kodi data
#
# This file is part of PKBridge.
# -*- coding: utf-8 -*-

import gzip, json, os, re, socket, errno, mimetypes, time, traceback, ssl
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver   import ThreadingMixIn
from functools                import partial
from threading                import Thread

from constants import (ADDON_ID, ADDON_NAME, ADDON_VERSION, PLEX_DEFAULT_PORT,
                       PLEX_MACHINE_ID, PLEX_SERVER_NAME, CACHE_DIR,
                       generate_ratingKey, LOG, MONITOR)
from kodiproxy import KodiProxy
from plex      import PlexTranslator

COMPRESSION_THRESHOLD = 1024
CHUNK_SIZE            = 65536

# Fake plex.tv/link HTML page
LINK_PAGE_HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Sign In | Plex</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
               background: #1a1a2e; color: #fff; display: flex; justify-content: center;
               align-items: center; min-height: 100vh; }
        .container { background: #16213e; padding: 40px; border-radius: 12px;
                     box-shadow: 0 8px 32px rgba(0,0,0,0.3); max-width: 400px; width: 90%; }
        h1 { font-size: 24px; margin-bottom: 8px; text-align: center; }
        p { color: #a0a0a0; margin-bottom: 24px; text-align: center; font-size: 14px; }
        .code-input { width: 100%; padding: 16px; font-size: 24px; text-align: center;
                      letter-spacing: 8px; border: 2px solid #333; border-radius: 8px;
                      background: #0f3460; color: #fff; outline: none; }
        .code-input:focus { border-color: #e94560; }
        .btn { width: 100%; padding: 14px; margin-top: 16px; font-size: 16px; font-weight: 600;
               border: none; border-radius: 8px; cursor: pointer; background: #e94560; color: #fff; }
        .btn:hover { background: #c73e54; }
        .btn:disabled { background: #555; cursor: not-allowed; }
        .success { display: none; text-align: center; }
        .success h2 { color: #4caf50; margin-bottom: 12px; }
        .logo { text-align: center; margin-bottom: 24px; font-size: 32px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">&#9654;</div>
        <div id="form-section">
            <h1>Sign In to Plex</h1>
            <p>Enter the 4-character code shown on your device</p>
            <form id="link-form">
                <input type="text" class="code-input" id="code" maxlength="8"
                       placeholder="CODE" autocomplete="off" autofocus>
                <button type="submit" class="btn" id="submit-btn">Sign In</button>
            </form>
        </div>
        <div id="success-section" class="success">
            <h2>&#10003; Signed In!</h2>
            <p>Your device has been connected. You can close this page.</p>
        </div>
    </div>
    <script>
        document.getElementById('link-form').addEventListener('submit', function(e) {
            e.preventDefault();
            var code = document.getElementById('code').value.trim();
            if (!code) return;
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('submit-btn').textContent = 'Signing in...';
            fetch('/link', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'code=' + encodeURIComponent(code)
            }).then(function(r) { return r.json(); })
              .then(function(d) {
                if (d.success) {
                    document.getElementById('form-section').style.display = 'none';
                    document.getElementById('success-section').style.display = 'block';
                } else {
                    alert('Invalid code. Please try again.');
                    document.getElementById('submit-btn').disabled = false;
                    document.getElementById('submit-btn').textContent = 'Sign In';
                }
            }).catch(function() {
                alert('Connection error. Please try again.');
                document.getElementById('submit-btn').disabled = false;
                document.getElementById('submit-btn').textContent = 'Sign In';
            });
        });
    </script>
</body>
</html>'''


def _xml_error(status, code, msg):
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<MediaContainer size="0">'
            '<Error code="%d" message="%s"/>' % (code, msg) +
            '</MediaContainer>').encode('utf-8')


class PlexHandler(BaseHTTPRequestHandler):
    """Routes every path a Plex client can ask for."""

    kodiproxy  = None
    translator = None
    pkplayer   = None  # set by server factory

    # ------------------------------------------------------------------
    # Plumbing
    # ------------------------------------------------------------------

    def log_message(self, fmt, *args):
        LOG('HTTP %s' % (fmt % args))

    def _parse(self):
        path = self.path.split('?')[0].rstrip('/')
        parts = [p for p in path.split('/') if p]
        q = {}
        if '?' in self.path:
            for pair in self.path.split('?', 1)[1].split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    q[k] = v
        return parts, q

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def _json(self, data, status=200):
        body = json.dumps(data, separators=(',', ':')).encode('utf-8')
        enc = self.headers.get('Accept-Encoding', '')
        if 'gzip' in enc and len(body) > COMPRESSION_THRESHOLD:
            body = gzip.compress(body, compresslevel=5)
            self.send_header('Content-Encoding', 'gzip')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('X-Plex-Protocol', '1.0')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def _ok(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>OK</h1></body></html>')

    def _err(self, status, msg=''):
        self.send_response(status)
        self.send_header('Content-Type', 'application/xml; charset=utf-8')
        body = _xml_error(status, status, msg or 'Not Found')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------
    # HEAD
    # ------------------------------------------------------------------

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', '*/*')
        self.end_headers()

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def do_GET(self):
        parts, q = self._parse()
        try:
            self._route_get(parts, q)
        except Exception as e:
            LOG('GET %s FAILED: %s\n%s' % (self.path, e, traceback.format_exc()), 3)
            self._err(500, str(e))

    def _route_get(self, parts, q):
        p = parts

        # ==============================================================
        #  PLEX.TV/LINK  (fake auth page for QR code scanning)
        # ==============================================================
        if p == ['link'] or p == ['link', '']:
            return self._serve_link_page(q)

        # ==============================================================
        #  SERVER ROOT  /
        # ==============================================================
        if not p or p == ['']:
            return self._json(self.translator.server_info())

        # ==============================================================
        #  IDENTITY  /identity
        # ==============================================================
        if p == ['identity']:
            return self._json({
                'MediaContainer': {
                    'machineIdentifier': PLEX_MACHINE_ID,
                    'version': ADDON_VERSION,
                }
            })

        # ==============================================================
        #  CLAIMED STATUS  /api/claimed  (mock plex.tv endpoint)
        # ==============================================================
        if p == ['api', 'claimed']:
            return self._json({
                'MediaContainer': {
                    'size': 1,
                    'claimed': '0',
                    'machineIdentifier': PLEX_MACHINE_ID,
                    'version': ADDON_VERSION,
                }
            })

        # ==============================================================
        #  USER INFO  /api/v2/user  /api/user  (mock plex.tv endpoint)
        # ==============================================================
        if p == ['api', 'v2', 'user'] or p == ['api', 'user']:
            return self._json({
                'MediaContainer': {
                    'size': 1,
                    'User': [{
                        'id': 1,
                        'uuid': PLEX_MACHINE_ID,
                        'username': 'pkbridge',
                        'email': 'local@pkbridge.local',
                        'friendlyName': 'PKBridge User',
                        'thumb': '',
                    }]
                }
            })

        # ==============================================================
        #  PREFS  /:/prefs  /:/prefs/get
        # ==============================================================
        if p == [':', 'prefs'] or p == [':', 'prefs', 'get']:
            return self._json(self.translator.server_prefs())

        # ==============================================================
        #  LIBRARY SECTIONS  /library/sections
        # ==============================================================
        if p == ['library', 'sections']:
            return self._json(self.translator.library_sections())

        # ==============================================================
        #  SECTION CHILDREN  /library/sections/{id}/action
        #  action = all | recentlyAdded | onDeck | search
        # ==============================================================
        if len(p) >= 3 and p[0] == 'library' and p[1] == 'sections':
            section_id = int(p[2])
            action = p[3] if len(p) > 3 else 'all'
            return self._json(self.translator.section_children(
                section_id, action, q,
                start=int(q.get('X-Plex-Container-Start', 0)),
                size=int(q.get('X-Plex-Container-Size', 50)),
            ))

        # ==============================================================
        #  METADATA  /library/metadata/{key}
        #  CHILDREN  /library/metadata/{key}/children
        #  GRANDCHILDREN  /library/metadata/{key}/grandchildren
        # ==============================================================
        if len(p) >= 3 and p[0] == 'library' and p[1] == 'metadata':
            rk = p[2]
            child = p[3] if len(p) > 3 else None
            return self._json(self.translator.metadata(rk, child, q))

        # ==============================================================
        #  STREAM  /library/parts/{id}/stream
        #  This is the big one — Plex apps request media through here.
        #  Two modes:
        #    1. ?pkbridge=1  ->  trigger Kodi player (local playback)
        #    2. default      ->  serve file over HTTP (Plex app streams it)
        # ==============================================================
        if len(p) >= 4 and p[0] == 'library' and p[1] == 'parts' and p[3] == 'stream':
            return self._serve_stream(p[2], q)

        # ==============================================================
        #  TRANSCODE  /video/:/transcode/universal
        #  Plex apps may request transcoding — we serve the original file
        #  and let the client decide. If they can't play it, they'll ask
        #  for a transcode and we'll serve the original anyway.
        # ==============================================================
        if len(p) >= 3 and p[0] == 'video' and p[1] == ':':
            path_arg = q.get('path', '')
            if path_arg.startswith('/library/metadata/'):
                rk = path_arg.split('/')[-1]
                return self._serve_stream(rk, q)
            return self._err(404, 'Nothing to transcode')

        # ==============================================================
        #  SEARCH  /hubs/search  /search
        # ==============================================================
        if p in [['hubs', 'search'], ['search'], ['hubs', 'home']]:
            return self._json(self.translator.search(q.get('query', '')))

        # ==============================================================
        #  HUBS  /hubs
        # ==============================================================
        if p == ['hubs']:
            return self._json(self.translator.global_hubs())

        # ==============================================================
        #  SESSIONS  /status/sessions
        # ==============================================================
        if p == ['status', 'sessions']:
            return self._json(self.translator.sessions(self.pkplayer))

        # ==============================================================
        #  PLAYLISTS  /playlists
        # ==============================================================
        if p == ['playlists']:
            return self._json(self.translator.playlists())

        # ==============================================================
        #  MEDIA PROVIDERS  /media/providers
        # ==============================================================
        if p == ['media', 'providers']:
            return self._json(self.translator.media_providers())

        # ==============================================================
        #  SYSTEM  /system
        # ==============================================================
        if p == ['system']:
            return self._json(self.translator.system_info())

        # ==============================================================
        #  IMAGE PROXY  /image/{path}
        # ==============================================================
        if p and p[0] == 'image':
            return self._serve_image('/'.join(p[1:]))

        # ==============================================================
        #  THUMB  /library/metadata/{rk}/thumb/{id}
        # ==============================================================
        if len(p) >= 5 and p[0] == 'library' and p[1] == 'metadata' and p[3] == 'thumb':
            return self._serve_item_thumb(p[2], q)

        # ==============================================================
        #  FALLBACK
        # ==============================================================
        LOG('Unknown GET %s' % self.path, 2)
        return self._json({'MediaContainer': {'size': 0}})

    # ------------------------------------------------------------------
    # POST
    # ------------------------------------------------------------------

    def do_POST(self):
        parts, q = self._parse()
        try:
            # ==============================================================
            #  MOCK PLEX.TV AUTH ENDPOINTS
            # ==============================================================

            # /api/v2/users/signin — return fake auth token
            if parts == ['api', 'v2', 'users', 'signin']:
                return self._json({
                    'MediaContainer': {
                        'size': 1,
                        'User': [{
                            'id': 1,
                            'uuid': PLEX_MACHINE_ID,
                            'username': 'pkbridge',
                            'email': 'local@pkbridge.local',
                            'friendlyName': 'PKBridge User',
                            'thumb': '',
                            'authToken': 'pkbridge_' + PLEX_MACHINE_ID[:16],
                            'subscription': {
                                'active': '1',
                                'status': 'active',
                                'plan': 'Plex Pass',
                            }
                        }]
                    }
                })

            # /api/user — alias for signin
            if parts == ['api', 'user']:
                return self._json({
                    'MediaContainer': {
                        'size': 1,
                        'User': [{
                            'id': 1,
                            'uuid': PLEX_MACHINE_ID,
                            'username': 'pkbridge',
                            'email': 'local@pkbridge.local',
                            'friendlyName': 'PKBridge User',
                            'thumb': '',
                            'authToken': 'pkbridge_' + PLEX_MACHINE_ID[:16],
                        }]
                    }
                })

            # /link — accept any code, return success
            if parts == ['link']:
                code = q.get('code', '')
                if not code:
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode('utf-8')
                    for pair in body.split('&'):
                        if pair.startswith('code='):
                            code = pair[5:]
                LOG('Link code received: %s' % code)
                return self._json({'success': True, 'code': code})

            # Timeline — acknowledge every time
            if parts == [':', 'timeline'] or parts == [':', 'timeline', '']:
                # Client reports playback state here; optionally sync back to Kodi
                self._sync_timeline(q)
                return self._ok()

            if parts == [':', 'scrobble']:
                return self._ok()
            if parts == [':', 'rate']:
                return self._ok()
            if parts == [':', 'unsubscribe']:
                return self._ok()

            return self._ok()
        except Exception as e:
            LOG('POST %s FAILED: %s' % (self.path, e), 3)
            self._err(500, str(e))

    # ------------------------------------------------------------------
    # PUT
    # ------------------------------------------------------------------

    def do_PUT(self):
        parts, q = self._parse()
        try:
            if parts == [':', 'prefs']:
                return self._ok()
            if parts == [':', 'rate']:
                return self._ok()
            if parts == [':', 'scrobble']:
                return self._ok()
            if parts == [':', 'scrobble', 'duration']:
                return self._ok()
            return self._ok()
        except Exception as e:
            LOG('PUT %s FAILED: %s' % (self.path, e), 3)
            self._err(500, str(e))

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def do_DELETE(self):
        try:
            return self._ok()
        except Exception as e:
            self._err(500, str(e))

    # ===================================================================
    #  STREAMING  /library/parts/{id}/stream
    # ===================================================================

    def _serve_stream(self, part_id: str, q: dict):
        """Two modes:
        - ?pkbridge=1  -> trigger Kodi local player, return 200
        - default      -> serve the file over HTTP for the Plex app
        """
        file_path = self.translator.resolve_file(part_id)
        if not file_path or not os.path.exists(file_path):
            return self._err(404, 'File not found')

        # ---- Local Kodi playback mode ----
        if q.get('pkbridge') == '1':
            offset_ms = int(q.get('offset', 0))
            meta = self.translator.get_item_meta(part_id)
            self.pkplayer.play_plex_stream(file_path, offset_ms, meta)
            self._ok()
            return

        # ---- HTTP streaming mode (Plex app streams from us) ----
        self._send_file(file_path)

    def _send_file(self, file_path: str):
        """Stream a file with HTTP Range support for seeking."""
        try:
            file_size = os.path.getsize(file_path)
            ct = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

            range_header = self.headers.get('Range')
            if range_header:
                m = re.match(r'bytes=(\d+)-(\d*)', range_header)
                if m:
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else min(start + CHUNK_SIZE * 16 - 1, file_size - 1)
                    end = min(end, file_size - 1)
                    length = end - start + 1

                    self.send_response(206)
                    self.send_header('Content-Type', ct)
                    self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, file_size))
                    self.send_header('Content-Length', length)
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()

                    with open(file_path, 'rb') as f:
                        f.seek(start)
                        remaining = length
                        while remaining > 0:
                            chunk = f.read(min(CHUNK_SIZE, remaining))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                    return

            # Full file
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', file_size)
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()

            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    self.wfile.write(data)

        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            LOG('Stream error: %s' % e, 3)

    # ===================================================================
    #  TIMELINE SYNC  (Plex app reports playback state -> sync to Kodi)
    # ===================================================================

    def _sync_timeline(self, q: dict):
        """Plex client sends timeline updates; if they're playing through
        our HTTP stream, we can optionally seek Kodi's player to match."""
        state = q.get('state', '')
        rating_key = q.get('ratingKey', '')
        time_ms = int(q.get('time', 0))
        duration_ms = int(q.get('duration', 0))

        if state == 'stopped':
            return  # nothing to sync

        # If the Plex app is playing via our HTTP stream and we want Kodi
        # to mirror that playback, we'd trigger Kodi player here.
        # For now we just log it — the Plex app is the primary player.
        if rating_key and time_ms:
            LOG('Timeline: %s @ %dms / %dms (%s)' % (rating_key, time_ms, duration_ms, state))

    # ===================================================================
    #  IMAGE PROXY
    # ===================================================================

    def _serve_image(self, image_path: str):
        try:
            import xbmcvfs
            decoded = xbmcvfs.decodePath(image_path)
            if not os.path.exists(decoded):
                return self._err(404, 'Image not found')

            ext = os.path.splitext(decoded)[1].lower()
            ct = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                  '.gif': 'image/gif', '.bmp': 'image/bmp', '.webp': 'image/webp',
                  '.tbn': 'image/jpeg'}.get(ext, 'application/octet-stream')

            with open(decoded, 'rb') as f:
                data = f.read()

            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', len(data))
            self.send_header('Cache-Control', 'max-age=86400')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            LOG('Image error: %s' % e, 2)
            self._err(500, str(e))

    def _serve_item_thumb(self, rating_key, q):
        thumb_path = self.translator.resolve_thumb(rating_key)
        if thumb_path and os.path.exists(thumb_path):
            return self._serve_image(thumb_path)
        self._err(404, 'Thumb not found')

    def _serve_link_page(self, q):
        """Serve fake plex.tv/link page for QR code auth."""
        code = q.get('code', '')
        html = LINK_PAGE_HTML
        if code:
            html = html.replace('autofocus', 'value="%s"' % code)
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    timeout = 10
    allow_reuse_address = True


class ThreadedHTTPSServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    timeout = 10
    allow_reuse_address = True

    def __init__(self, server_address, handler_class, certfile, keyfile):
        HTTPServer.__init__(self, server_address, handler_class)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile, keyfile)
        self.socket = ctx.wrap_socket(self.socket, server_side=True)


def _generate_self_signed_cert(cert_dir):
    """Generate a self-signed cert for HTTPS. Returns (certfile, keyfile) paths."""
    certfile = os.path.join(cert_dir, 'pkbridge.pem')
    keyfile = os.path.join(cert_dir, 'pkbridge.key')

    if os.path.exists(certfile) and os.path.exists(keyfile):
        return certfile, keyfile

    try:
        from subprocess import run as _run, PIPE
        _run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-keyout', keyfile, '-out', certfile,
            '-days', '3650', '-nodes',
            '-subj', '/CN=plex.tv/O=PKBridge/C=US',
        ], check=True, capture_output=True)
        LOG('Self-signed cert generated: %s' % certfile)
        return certfile, keyfile
    except Exception as e:
        LOG('Cert generation failed (openssl not found?): %s' % e, 2)
        return None, None


class PKBridgeServer:
    def __init__(self, kodiproxy, translator, pkplayer):
        self.kodiproxy  = kodiproxy
        self.translator = translator
        self.pkplayer   = pkplayer
        self.httpd  = None
        self.httpsd = None
        self.thread = None
        self.https_thread = None
        self.port   = PLEX_DEFAULT_PORT
        self.host   = '0.0.0.0'
        self._running = False

    def _chk_port(self, host, port):
        for p in range(port, port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((host, p))
                    return p
            except socket.error:
                continue
        return port

    def start(self):
        if self._running:
            return

        import xbmc
        try:
            host = socket.gethostbyname(socket.gethostname())
        except Exception:
            host = '0.0.0.0'

        self.port = self._chk_port(host, PLEX_DEFAULT_PORT)
        self.host = '%s:%d' % (host, self.port)

        PlexHandler.kodiproxy  = self.kodiproxy
        PlexHandler.translator = self.translator
        PlexHandler.pkplayer   = self.pkplayer

        handler = partial(PlexHandler)
        self.httpd = ThreadedHTTPServer((host, self.port), handler)

        self.thread = Thread(target=self.httpd.serve_forever, name='PKBridge.HTTP', daemon=True)
        self.thread.start()
        self._running = True
        LOG('HTTP server started on %s' % self.host, xbmc.LOGINFO)

        # Start HTTPS server for plex.tv auth interception
        certfile, keyfile = _generate_self_signed_cert(CACHE_DIR)
        if certfile and keyfile:
            try:
                https_port = self._chk_port(host, 443)
                self.httpsd = ThreadedHTTPSServer((host, https_port), handler, certfile, keyfile)
                self.https_thread = Thread(target=self.httpsd.serve_forever, name='PKBridge.HTTPS', daemon=True)
                self.https_thread.start()
                LOG('HTTPS server started on %s:%d' % (host, https_port), xbmc.LOGINFO)
            except Exception as e:
                LOG('HTTPS server failed to start: %s' % e, 2)

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
            except Exception:
                pass
            try:
                self.httpd.server_close()
            except Exception:
                pass
        if self.httpsd:
            try:
                self.httpsd.shutdown()
            except Exception:
                pass
            try:
                self.httpsd.server_close()
            except Exception:
                pass
        self._running = False
        LOG('HTTP server stopped')

    def get_host(self):
        return self.host

    def is_running(self):
        return self._running
