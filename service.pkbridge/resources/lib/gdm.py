#   Copyright (C) 2026 Lunatixz
#
#   PKBridge - Kodi-to-Plex bridge service
#   GDM (Good Day Mate) — Plex's UDP multicast server discovery
#
# Plex clients send M-SEARCH to 239.0.0.250:32414.
# We respond with our server identity so they find us automatically.
#
# This file is part of PKBridge.
# -*- coding: utf-8 -*-

import socket, struct, threading, time
from constants import (PLEX_DEFAULT_PORT, PLEX_MACHINE_ID, PLEX_SERVER_NAME,
                       ADDON_VERSION, LOG, MONITOR)

GDM_MULTICAST = '239.0.0.250'
GDM_PORTS     = [32414, 32410, 32412, 32413]
GDM_SEARCH    = b'M-SEARCH * HTTP/1.0\r\n\r\n'


class GDMListener(threading.Thread):
    """Listens for Plex GDM discovery queries and responds with our identity."""

    def __init__(self, port: int = PLEX_DEFAULT_PORT):
        super().__init__(name='PKBridge.GDM', daemon=True)
        self.port = port
        self._running = False
        self._sockets = []

    def run(self):
        self._running = True
        LOG('GDM listener starting')

        for gdm_port in GDM_PORTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except AttributeError:
                    pass  # Windows doesn't have SO_REUSEPORT
                sock.settimeout(2.0)
                sock.bind(('', gdm_port))

                # Join multicast group
                mreq = struct.pack('4s4s',
                                   socket.inet_aton(GDM_MULTICAST),
                                   socket.inet_aton('0.0.0.0'))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)

                self._sockets.append(sock)
                LOG('GDM listening on port %d' % gdm_port)
            except Exception as e:
                LOG('GDM bind port %d failed: %s' % (gdm_port, e), 2)

        if not self._sockets:
            LOG('GDM: no sockets available, listener disabled', 2)
            return

        while not MONITOR().abortRequested() and self._running:
            try:
                readable = socket.select(self._sockets, [], [], 2.0)[0]
                for sock in readable:
                    try:
                        data, addr = sock.recvfrom(4096)
                        self._handle_search(data, addr, sock)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        LOG('GDM recv error: %s' % e, 2)
            except Exception:
                if MONITOR().abortRequested():
                    break
                time.sleep(0.5)

        self._cleanup()
        LOG('GDM listener stopped')

    def _handle_search(self, data: bytes, addr: tuple, sock: socket.socket):
        """Got an M-SEARCH — respond with our server identity."""
        if data.strip() != GDM_SEARCH:
            return

        client_ip, client_port = addr
        LOG('GDM M-SEARCH from %s:%d' % (client_ip, client_port))

        # Build GDM response — a minimal HTTP-like response
        response = (
            'HTTP/1.0 200 OK\r\n'
            'Cache-Control: max-age=3600\r\n'
            'Date: %s\r\n'
            'Location: http://%s:%d\r\n'
            'Name: %s\r\n'
            'Port: %d\r\n'
            'Protocol: plex\r\n'
            'Product: PKBridge\r\n'
            'Version: %s\r\n'
            'MachineIdentifier: %s\r\n'
            'Updated-At: %d\r\n'
            '\r\n'
        ) % (
            time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
            client_ip,
            self.port,
            PLEX_SERVER_NAME,
            self.port,
            ADDON_VERSION,
            PLEX_MACHINE_ID,
            int(time.time()),
        )

        try:
            sock.sendto(response.encode('utf-8'), addr)
            LOG('GDM response sent to %s:%d' % addr)
        except Exception as e:
            LOG('GDM send failed: %s' % e, 2)

    def stop(self):
        self._running = False

    def _cleanup(self):
        for sock in self._sockets:
            try:
                mreq = struct.pack('4s4s',
                                   socket.inet_aton(GDM_MULTICAST),
                                   socket.inet_aton('0.0.0.0'))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
        self._sockets.clear()
