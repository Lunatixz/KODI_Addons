# -*- coding: utf-8 -*-
"""Addon Module"""

from __future__ import absolute_import, division, unicode_literals

import sys
import json
import logging
import os
import re
import socket
import time
import dateutil.parser
import datetime

from resources.lib import kodiutils
from resources.lib.modules.iptvsimple import IptvSimple
from simplecache import SimpleCache

_LOGGER = logging.getLogger(__name__)

CHANNELS_VERSION = 1
EPG_VERSION = 1


def update_qs(url, **params):
    """Add or update a URL query string"""
    try:  # Python 3
        from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
    except ImportError:  # Python 2
        from urllib import urlencode

        from urlparse import parse_qsl, urlparse, urlunparse
    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)


class Addon:
    """Helper class for Addon communication"""
    cache = SimpleCache() 
    cache.enable_mem_cache = False

    def __init__(self, addon_id, addon_obj, channels_uri, epg_uri):
        self.addon_id = addon_id
        self.addon_obj = addon_obj
        self.channels_uri = channels_uri
        self.epg_uri = epg_uri
        
        addon = kodiutils.get_addon(addon_id)
        self.addon_path = kodiutils.addon_path(addon)
    
    
    @staticmethod
    def getLocalTime():
        offset = (datetime.datetime.utcnow() - datetime.datetime.now())
        return datetime.datetime.fromtimestamp(float(time.time() + offset.total_seconds()))
            

    @classmethod
    def refresh(cls, show_progress=False, force=False):
        """Update channels and EPG data"""
        channels = []
        epg = []

        if show_progress:
            progress = kodiutils.progress(message=kodiutils.localize(30703))  # Detecting IPTV add-ons...
        else:
            progress = None

        addons = cls.detect_iptv_addons()
        for index, addon in enumerate(addons):
            """Check if addon requires update"""
            
            if not force and not cls.is_refresh_required(addon.addon_id):
                addon_epg = cls.cache.get('iptvmanager.epg.%s'%(addon.addon_id))
                addon_channel = cls.cache.get('iptvmanager.channel.%s'%(addon.addon_id))
                if addon_epg and addon_channel:
                    _LOGGER.info('Update not needed for %s...', addon.addon_id)
                    channels.append(addon_channel)
                    epg.append(addon_epg)
                    continue
            
            
            if progress:
                # Fetching channels and guide of {addon}...
                progress.update(int(100 * index / len(addons)),
                                kodiutils.localize(30704).format(addon=kodiutils.addon_name(addon.addon_obj)))
            _LOGGER.info('Updating IPTV data for %s...', addon.addon_id)

            # Fetch channels
            addon_channel = dict(
                addon_id=addon.addon_id,
                addon_name=kodiutils.addon_name(addon.addon_obj),
                channels=addon.get_channels(),
            )
            channels.append(addon_channel)
            
            if progress and progress.iscanceled():
                progress.close()
                return

            # Fetch EPG
            addon_epg = addon.get_epg()
            cls.set_cache_n_update(cls,addon.addon_id,addon_epg,addon_channel)
            epg.append(addon_epg)

            if progress and progress.iscanceled():
                progress.close()
                return

        # Write files
        if show_progress:
            progress.update(100, kodiutils.localize(30705))  # Updating channels and guide...

        IptvSimple.write_playlist(channels)
        IptvSimple.write_epg(epg, channels)

        if kodiutils.get_setting_bool('iptv_simple_restart'):
            if show_progress:
                # Restart now.
                IptvSimple.restart(True)
            else:
                # Try to restart now. We will schedule it if the user is watching TV.
                IptvSimple.restart(False)

        # Update last_refreshed
        kodiutils.set_property('last_refreshed', int(time.time()))

        if show_progress:
            progress.close()


    @staticmethod
    def is_refresh_required(addon_id):
        refresh_required = False
        now = Addon.getLocalTime()
        if now >= dateutil.parser.parse(kodiutils.get_setting('%s.next_update'%(addon_id), now.strftime('%Y%m%d%H%M%S %z').rstrip())):
            refresh_required = True
        _LOGGER.info('%s is refresh required? %s'%(addon_id,refresh_required))
        return refresh_required
        
        
    def set_cache_n_update(self, addon_id, addon_epg, addon_channel):
        """Find epgs min. Start and min. Stop time"""
        now = self.getLocalTime()
        max_start = min([min([dateutil.parser.parse(program['start']) for program in programmes], default=now) for channel, programmes in addon_epg.items()], default=now) #earliest first start
        max_stop =  min([max([dateutil.parser.parse(program['stop']) for program in programmes], default=now) for channel, programmes in addon_epg.items()], default=now)  #earliest last stop
        
        guide_hours, r = divmod(abs(max_start - max_stop).total_seconds(),3600) #amount of guidedata available.
        half_life_hours = round(guide_hours//2) #guidedata half life (update time).
        next_update = (max_stop - datetime.timedelta(hours=half_life_hours))#start update prematurely to assure no gaps in meta.
        cache_life = abs(now - next_update).total_seconds()
        
        self.cache.set('iptvmanager.epg.%s'%(addon_id), addon_epg, expiration=datetime.timedelta(seconds=cache_life))
        self.cache.set('iptvmanager.channel.%s'%(addon_id), addon_channel, expiration=datetime.timedelta(seconds=cache_life))
        kodiutils.set_setting('%s.next_update'%(addon_id),next_update.strftime('%Y%m%d%H%M%S %z').rstrip())
        _LOGGER.info('%s next update %s, life %s'%(addon_id,next_update.strftime('%Y%m%d%H%M%S %z').rstrip(),half_life_hours))
            

    @staticmethod
    def detect_iptv_addons():
        """Find add-ons that provide IPTV channel data"""
        result = kodiutils.jsonrpc(method="Addons.GetAddons",
                                   params={'installed': True, 'enabled': True, 'type': 'xbmc.python.pluginsource'})

        addons = []
        for row in result['result'].get('addons', []):
            addon = kodiutils.get_addon(row['addonid'])

            # Check if add-on supports IPTV Manager
            if addon.getSetting('iptv.enabled') != 'true':
                continue

            addons.append(Addon(
                addon_id=row['addonid'],
                addon_obj=addon,
                channels_uri=addon.getSetting('iptv.channels_uri'),
                epg_uri=addon.getSetting('iptv.epg_uri'),
            ))

        return addons

    def get_channels(self):
        """Get channel data from this add-on"""
        _LOGGER.info('Requesting channels from %s...', self.channels_uri)
        if not self.channels_uri:
            return []

        try:
            data = self._get_data_from_addon(self.channels_uri)
            _LOGGER.debug(data)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error('Something went wrong while calling %s: %s', self.addon_id, exc)
            return []

        # Return M3U8-format as-is without headers
        if not isinstance(data, dict):
            return data.replace('#EXTM3U\n', '')

        # JSON-STREAMS format
        if data.get('version', 1) > CHANNELS_VERSION:
            _LOGGER.warning('Skipping %s since it uses an unsupported version: %d', self.channels_uri,
                            data.get('version'))
            return []

        channels = []
        for channel in data.get('streams', []):
            # Check for required fields
            if not channel.get('name') or not channel.get('stream'):
                _LOGGER.warning('Skipping channel since it is incomplete: %s', channel)
                continue

            # Fix logo path to be absolute
            if not channel.get('logo'):
                channel['logo'] = kodiutils.addon_icon(self.addon_obj)
            elif not channel.get('logo').startswith(('http://', 'https://', 'special://', 'resource://', '/')):
                channel['logo'] = os.path.join(self.addon_path, channel.get('logo'))

            # Ensure group is a set
            if not channel.get('group'):
                channel['group'] = set()
            # Accept string values (backward compatible)
            elif isinstance(channel.get('group'), (bytes, str)):
                channel['group'] = set(channel.get('group').split(';'))
            # Accept string values (backward compatible, py2 version)
            elif sys.version_info.major == 2 and isinstance(channel.get('group'), unicode): # noqa: F821; pylint: disable=undefined-variable
                channel['group'] = set(channel.get('group').split(';'))
            elif isinstance(channel.get('group'), list):
                channel['group'] = set(list(channel.get('group')))
            else:
                _LOGGER.warning('Channel group is not a list: %s', channel)
                channel['group'] = set()
            # Add add-on name as group, if not already
            channel['group'].add(kodiutils.addon_name(self.addon_obj))

            channels.append(channel)

        return channels

    def get_epg(self):
        """Get epg data from this add-on"""
        if not self.epg_uri:
            return {}

        _LOGGER.info('Requesting epg from %s...', self.epg_uri)
        try:
            data = self._get_data_from_addon(self.epg_uri)
            _LOGGER.debug(data)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error('Something went wrong while calling %s: %s', self.addon_id, exc)
            return {}

        # Return XMLTV-format as-is without headers and footers
        if not isinstance(data, dict):
            return re.search(r'<tv[^>]*>(.*)</tv>', data, flags=re.DOTALL).group(1).strip()

        # JSON-EPG format
        if data.get('version', 1) > EPG_VERSION:
            _LOGGER.warning('Skipping EPG from %s since it uses an unsupported version: %d', self.epg_uri,
                            data.get('version'))
            return {}

        # Check for required fields
        if not data.get('epg'):
            _LOGGER.warning('Skipping EPG from %s since it is incomplete', self.epg_uri)
            return {}

        return data['epg']

    def _get_data_from_addon(self, uri):
        """Request data from the specified URI"""
        # Plugin path
        if uri.startswith('plugin://'):
            # Prepare data
            sock = self._prepare_for_data()
            uri = update_qs(uri, port=sock.getsockname()[1])

            _LOGGER.info('Executing RunPlugin(%s)...', uri)
            kodiutils.execute_builtin('RunPlugin', uri)

            # Wait for data
            result = self._wait_for_data(sock)

            # Load data
            data = json.loads(result)

            return data

        # Currently, only plugin:// uris are supported
        raise NotImplementedError

    @staticmethod
    def _prepare_for_data():
        """Prepare ourselves so we can receive data"""
        # Bind on localhost on a free port above 1024
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))

        _LOGGER.debug('Bound on port %s...', sock.getsockname()[1])

        # Listen for one connection
        sock.listen(1)
        return sock

    def _wait_for_data(self, sock, timeout=10):
        """Wait for data to arrive on the socket"""
        # Set a connection timeout
        # The remote and should connect back as soon as possible so we know that the request is being processed
        sock.settimeout(timeout)

        try:
            _LOGGER.debug('Waiting for a connection from %s on port %s...', self.addon_id, sock.getsockname()[1])

            # Accept one client
            conn, addr = sock.accept()
            _LOGGER.debug('Connected to %s:%s! Waiting for result...', addr[0], addr[1])

            # We have no timeout when the connection is established
            conn.settimeout(None)

            # Read until the remote end closes the connection
            buf = ''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk.decode()

            if not buf:
                # We got an empty reply, this means that something didn't go according to plan
                raise Exception('Something went wrong in %s' % self.addon_id)

            return buf

        except socket.timeout:
            raise Exception('Timout waiting for reply on port %s' % sock.getsockname()[1])

        finally:
            # Close our socket
            _LOGGER.debug('Closing socket on port %s', sock.getsockname()[1])
            sock.close()
