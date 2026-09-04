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
from globals import *

class Trakt:
    PREFIXES = {'user': '', 'popular': 'pop:', 'trending': 'trend:'}

    def __init__(self, cache=None):
        self.monitor = MONITOR()
        if cache is None: self.cache = SimpleCache()
        else:
            self.cache = cache
            self.cache.enable_mem_cache = False
        
        self.enabled = REAL_SETTINGS.getSetting('Enable_Trakt') == 'true'
        self.allow_community = REAL_SETTINGS.getSetting('Allow_CommunityLists') == 'true'
        self.cache_checksum = 'community_' + str(self.allow_community)
        self.name    = LANGUAGE(32100)
        self.logo    = os.path.join(ADDON_PATH,'resources','images','trakt.png')
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def convert_type(self, list_type):
        return {'movie':'movies','show':'tvshows','season':'seasons','episode':'episodes'}[list_type]


    def clean_string(self, string):
        if not string: return ''
        import re
        string = string.replace('copy','').replace('\r\n\t','').rstrip()
        string = re.sub(r'[^\x20-\x7E]', '', string)
        return string.strip()


    def _headers(self):
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': REAL_SETTINGS.getSetting('Trakt_ClientID')}
        access_token = REAL_SETTINGS.getSetting('Trakt_TokenID')
        if access_token: headers['Authorization'] = f'Bearer {access_token}'
        return headers


    def _list_id(self, prefix, raw_id):
        return '%s%s'%(self.PREFIXES[prefix], raw_id)


    def _resolve_id(self, list_id):
        for prefix, tag in self.PREFIXES.items():
            if tag and list_id.startswith(tag):
                return prefix, list_id[len(tag):]
        return 'user', list_id


    def _fetch_paginated(self, url, headers, params=None):
        items = []
        page = 1
        limit = 1000
        while not self.monitor.abortRequested():
            p = {'page': page, 'limit': limit}
            if params: p.update(params)
            response = requests.get(url, headers=headers, params=p, timeout=15)
            if response.status_code in (204, 404):
                self.log('_fetch_paginated, empty %s %s'%(response.status_code, url))
                break
            if response.status_code != 200:
                self.log('_fetch_paginated, failed! %s %s'%(response.status_code, url))
                break
            items.extend(response.json())
            total_pages = int(response.headers.get('X-Pagination-Page-Count', 1))
            if page >= total_pages: break
            page += 1
        return items


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_lists(self):
        if not self.enabled: return []
        tmp = []
        seen = set()
        headers = self._headers()
        self.log('get_lists')

        def _add(item):
            if item['id'] not in seen:
                seen.add(item['id'])
                tmp.append(item)

        # 1) User's own lists
        trakt_user = REAL_SETTINGS.getSetting('Trakt_Username')
        if trakt_user:
            url = f"https://api.trakt.tv/users/{trakt_user}/lists"
            for item in self._fetch_paginated(url, headers):
                desc = self.clean_string(item.get('description',''))
                count = item.get('item_count', 0)
                label2 = '%s items - %s'%(count, desc) if desc else '%s items'%count
                _add({
                    'name': self.clean_string(item.get('name')),
                    'description': label2,
                    'id': self._list_id('user', str(item.get('ids',{}).get('trakt'))),
                    'icon': self.logo
                })

        # 2) Popular personal lists
        if self.allow_community:
            url = "https://api.trakt.tv/lists/popular/personal"
            response = requests.get(url, headers=headers, params={'limit': 25}, timeout=15)
            if response.status_code == 200:
                for item in response.json():
                    lst = item.get('list', item)
                    user = lst.get('user',{})
                    count = lst.get('item_count', 0)
                    _add({
                        'name': '[Popular] %s'%self.clean_string(lst.get('name')),
                        'description': '%s items - by %s - %s likes'%(count, user.get('username',''), item.get('like_count',0)),
                        'id': self._list_id('popular', str(lst.get('ids',{}).get('trakt'))),
                        'icon': self.logo
                    })

            # 3) Trending personal lists
            url = "https://api.trakt.tv/lists/trending/personal"
            response = requests.get(url, headers=headers, params={'limit': 25}, timeout=15)
            if response.status_code == 200:
                for item in response.json():
                    lst = item.get('list', item)
                    user = lst.get('user',{})
                    count = lst.get('item_count', 0)
                    _add({
                        'name': '[Trending] %s'%self.clean_string(lst.get('name')),
                        'description': '%s items - by %s - %s watchers'%(count, user.get('username',''), item.get('watchers',0)),
                        'id': self._list_id('trending', str(lst.get('ids',{}).get('trakt'))),
                        'icon': self.logo
                    })

        return sorted(tmp, key=itemgetter('name'))
            
            
    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_list_items(self, list_id):
        self.log('get_list_items, list_id = %s'%list_id)
        tmp = {}
        prefix, raw_id = self._resolve_id(list_id)
        headers = self._headers()

        for list_type in ['movie','show','season','episode','person']:
            page = 1
            limit = 1000
            while not self.monitor.abortRequested():
                url = f"https://api.trakt.tv/lists/{raw_id}/items/{list_type}"
                params = {'page': page, 'limit': limit}
                response = requests.get(url, headers=headers, params=params, timeout=15)
                if response.status_code in (204, 404):
                    break
                if response.status_code != 200:
                    self.log("get_list_items, failed! %s [%s]"%(response.status_code,list_type))
                    break
                else:
                    results = response.json()
                    for item in results:
                        if list_type == 'person':
                            person = item.get('person', {})
                            person_id = person.get('ids', {}).get('trakt')
                            if person.get('name') and person_id:
                                tmp.setdefault('persons', []).append({'name': person.get('name'),'id': str(person_id)})
                        elif list_type == 'season' and 'show' in item: item[list_type].update(item.pop('show'))
                        else: tmp.setdefault(self.convert_type(list_type),[]).append({'type':item.get('type'),'title':item.get(list_type,{}).get('title'),'year':item.get(list_type,{}).get('year'),'season':item.get(list_type,{}).get('number'),'uniqueid':item.get(list_type,{}).get('ids'),'data':item})
                    self.log("get_list_items, %s = %s, page = %s"%(list_type,len(results),page))
                    total_pages = int(response.headers.get('X-Pagination-Page-Count', 1))
                    if page >= total_pages: break
                    page += 1
        return tmp


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_trakt_person(self, trakt_id):
        tmp   = {}
        limit = 1000
        urls  = {'movie':f"https://api.trakt.tv/people/{trakt_id}/movies",
                 'show' :f"https://api.trakt.tv/people/{trakt_id}/shows"}
        headers = self._headers()
        for list_type, url in list(urls.items()):
            page = 1
            while not self.monitor.abortRequested():
                params   = {'page': page, 'limit': limit}
                response = requests.get(url, headers=headers, params=params, timeout=15)
                if response.status_code in (204, 404):
                    break
                if response.status_code != 200:
                    self.log('get_trakt_person, failed! %s'%(response.status_code))
                    break
                else:
                    for item in response.json().get('cast',[]):
                        tmp.setdefault(self.convert_type(list_type),[]).append({'type':list_type,'title':item.get(list_type,{}).get('title'),'year':item.get(list_type,{}).get('year'),'season':item.get(list_type,{}).get('number'),'uniqueid':item.get(list_type,{}).get('ids'),'data':item})
                    total_pages = int(response.headers.get('X-Pagination-Page-Count', 1))
                    if page >= total_pages: break
                    page += 1
        return tmp
