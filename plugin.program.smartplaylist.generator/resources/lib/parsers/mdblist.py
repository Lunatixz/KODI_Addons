#   Copyright (C) 2025 Lunatixz
#
#
# This file is part of Smartplaylist Generator.
#
# Smartplaylist Generator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smartplaylist Generator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-
import requests

from globals  import *
from operator import itemgetter

class MDBList:
    TYPE_MAP  = {'movie': 'movies', 'show': 'tvshows', 'season': 'seasons', 'episode': 'episodes'}
    PREFIXES  = {'user': '', 'top': 'top:', 'official': 'official:', 'external': 'ext:'}

    def __init__(self, cache=None):
        if cache is None: self.cache = SimpleCache()
        else:
            self.cache = cache
            self.cache.enable_mem_cache = False

        self.enabled = REAL_SETTINGS.getSetting('Enable_MDBList') == 'true'
        self.allow_community = REAL_SETTINGS.getSetting('Allow_CommunityLists_MDB') == 'true'
        self.cache_checksum = 'community_' + str(self.allow_community)
        self.name    = LANGUAGE(32300)
        self.logo    = os.path.join(ADDON_PATH,'resources','images','mdblist.png')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _api_key(self):
        return REAL_SETTINGS.getSetting('MDBList_APIKEY')


    def _get(self, path, **extra):
        api_key = self._api_key()
        if not api_key:
            self.log('_get, no API key set')
            return None
        url = 'https://api.mdblist.com%s'%path
        params = {'apikey': api_key}
        params.update(extra.pop('params', {}))
        response = requests.get(url, params=params, timeout=15, **extra)
        if response.status_code == 401:
            self.log('_get, invalid API key', xbmc.LOGERROR)
            return None
        response.raise_for_status()
        return response


    def _parse_item(self, item):
        imdb_id = item.get('imdb_id') or (item.get('ids') or {}).get('imdb') or ''
        if not imdb_id.startswith('tt'): return None
        parsed = {
            'title': item.get('title'),
            'year': item.get('release_year'),
            'uniqueid': {'imdb': imdb_id},
            'data': item
        }
        if item.get('season_number') is not None:
            parsed['season'] = item['season_number']
        if item.get('episode_number') is not None:
            parsed['episode'] = item['episode_number']
        if item.get('show_title'):
            parsed['showtitle'] = item['show_title']
        return parsed


    def _classify(self, item):
        mtype = (item.get('mediatype') or '').lower()
        return self.TYPE_MAP.get(mtype, 'tvshows')


    def _list_id(self, prefix, raw_id):
        return '%s%s'%(self.PREFIXES[prefix], raw_id)


    def _resolve_id(self, list_id):
        for prefix, tag in self.PREFIXES.items():
            if tag and list_id.startswith(tag):
                return prefix, list_id[len(tag):]
        return 'user', list_id


    def _fetch_items(self, path, **params):
        items = []
        offset = 0
        limit = 1000
        while True:
            response = self._get(path, params={'limit': limit, 'offset': offset, **params})
            if response is None: break
            data = response.json()
            for key in ('movies', 'shows'):
                for item in data.get(key, []):
                    parsed = self._parse_item(item)
                    if parsed: items.append((self._classify(item), parsed))
            if response.headers.get('X-Has-More', 'false').lower() != 'true': break
            offset += limit
        return items


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_lists(self):
        if not self.enabled: return []
        tmp = []
        seen = set()
        self.log('get_lists')

        def _add(item):
            if item['id'] not in seen:
                seen.add(item['id'])
                tmp.append(item)

        # 1) User's own lists
        response = self._get('/lists/user')
        if response is None:
            self.log('get_lists, API key missing or invalid', xbmc.LOGERROR)
            xbmc.executebuiltin('Notification(%s,%s,5000)'%(self.name, LANGUAGE(32304)))
            return []
        for lst in response.json():
            desc = lst.get('description','')
            count = lst.get('items', 0)
            label2 = '%s items - %s'%(count, desc) if desc else '%s items'%count
            _add({
                'name': '[User] %s'%lst.get('name'),
                'description': label2,
                'id': self._list_id('user', str(lst.get('id'))),
                'icon': self.logo
            })

        # 2) Top public lists
        if self.allow_community:
            response = self._get('/lists/top')
            if response:
                for lst in response.json():
                    desc = lst.get('description','')
                    count = lst.get('items', 0)
                    label2 = '%s items - %s'%(count, desc) if desc else '%s items'%count
                    _add({
                        'name': '[Top] %s'%lst.get('name'),
                        'description': label2,
                        'id': self._list_id('top', str(lst.get('id'))),
                        'icon': self.logo
                    })

            # 3) Official MDBList lists
            response = self._get('/lists/official')
            if response:
                for lst in response.json():
                    desc = lst.get('description','')
                    count = lst.get('items', 0)
                    label2 = '%s items - %s'%(count, desc) if desc else '%s items'%count
                    _add({
                        'name': '[Official] %s'%lst.get('name'),
                        'description': label2,
                        'id': self._list_id('official', lst.get('slug','')),
                        'icon': self.logo
                    })

            # 4) External/linked lists (imported from IMDb, Trakt, etc.)
            response = self._get('/external/lists/user')
            if response:
                for lst in response.json():
                    source = (lst.get('source') or '').upper()
                    desc = lst.get('description','')
                    count = lst.get('items', 0)
                    label2 = '%s items from %s'%(count, source)
                    if desc: label2 += ' - %s'%desc
                    _add({
                        'name': '[%s] %s'%(source or 'External', lst.get('name')),
                        'description': label2,
                        'id': self._list_id('external', str(lst.get('id'))),
                        'icon': self.logo
                    })

        return sorted(tmp, key=itemgetter('name'))


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_list_items(self, list_id):
        self.log('get_list_items, list_id = %s'%list_id)
        tmp = {}
        prefix, raw_id = self._resolve_id(list_id)

        if prefix == 'official':
            items = self._fetch_items('/lists/official/%s/items'%raw_id)
        elif prefix == 'external':
            items = self._fetch_items('/external/lists/%s/items'%raw_id)
        else:
            items = self._fetch_items('/lists/%s/items'%raw_id)

        for mtype, parsed in items:
            tmp.setdefault(mtype, []).append(parsed)
        return tmp
