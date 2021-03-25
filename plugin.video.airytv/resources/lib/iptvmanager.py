#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of AiryTV.
#
# AiryTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# AiryTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AiryTV.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
"""IPTV Manager Integration module"""
import json
import socket

class IPTVManager:
    """Interface to IPTV Manager"""
    def __init__(self, port, airytv):
        """Initialize IPTV Manager object"""
        self.port    = port
        self.airytv = airytv
        
    def via_socket(func):
        """Send the output of the wrapped function to socket"""
        def send(self):
            try:
                """Decorator to send over a socket"""
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', self.port))
                sock.sendall(json.dumps(func(self)).encode())
                sock.close()
            except: pass
        return send

    @via_socket
    def send_channels(self):
        """Return JSON-STREAMS formatted information to IPTV Manager"""
        return dict(version=1, streams=self.airytv.buildChannels(opt='iptv_channel'))

    @via_socket
    def send_epg(self):
        """Return JSON-EPG formatted information to IPTV Manager"""
        return dict(version=1, epg=self.airytv.buildChannels(opt='iptv_broadcasts'))