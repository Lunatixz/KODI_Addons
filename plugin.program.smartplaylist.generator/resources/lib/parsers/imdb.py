#   Copyright (C) 2024 Lunatixz
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
import csv
import requests

from globals  import *
from bs4      import BeautifulSoup
from operator import itemgetter

class IMDB:
    TITLE_TYPES = {'movie':'movies','tvseries':'tvshows','tvminiseries':'tvshows','tvepisode':'episodes'}

    def __init__(self, cache=None):
        if cache is None: self.cache = SimpleCache()
        else:
            self.cache = cache
            self.cache.enable_mem_cache = False

        self.enabled = REAL_SETTINGS.getSetting('Enable_IMDB') == 'true'
        self.name    = LANGUAGE(32112)
        self.logo    = os.path.join(ADDON_PATH,'resources','images','imdb.png')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    @staticmethod
    def classify(ttype):
        return IMDB.TITLE_TYPES.get((ttype or '').lower().replace(' ',''))


    def _parse_csv(self, text):
        tmp = {}
        for row in csv.DictReader(text.lstrip('\ufeff').splitlines()):
            key   = self.classify(row.get('Title Type',''))
            const = (row.get('Const') or '').strip()
            if not key or not const.startswith('tt'): continue
            tmp.setdefault(key, []).append({'title': row.get('Title'),'year': row.get('Year'),'uniqueid': {'imdb': const},'data': row})
        return tmp


    def _parse_page(self, list_id, headers):
        tmp = {}
        response = requests.get(f"https://www.imdb.com/list/{list_id}/", headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if script_tag:
            data = json.loads(script_tag.string)
            items = data.get('props', {}).get('pageProps', {}).get('contentData', {}).get('list', {}).get('items', [])
            for entry in items:
                item  = entry.get('item') or {}
                const = item.get('id','')
                key   = self.classify((item.get('titleType') or {}).get('id'))
                if not key or not const.startswith('tt'): continue
                tmp.setdefault(key, []).append({'title':(item.get('titleText') or {}).get('text'),'year':None,'uniqueid': {'imdb': const},'data': item})
        if not tmp: self.log('get_list_items, page scrape found nothing for %s'%(list_id))
        return tmp


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_lists(self):
        if not self.enabled: return []
        imdb_user = REAL_SETTINGS.getSetting('IMDB_ClientID')
        tmp = []
        self.log('get_lists, imdb_user = %s'%(imdb_user))
        url = f"https://www.imdb.com/user/{imdb_user}/lists"
        headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if script_tag:
            data = json.loads(script_tag.string)
            lists_data = data.get('props', {}).get('pageProps', {}).get('lists', [])
            for l in lists_data:
                try:
                    list_id   = l.get('id')
                    list_name = l.get('title') or l.get('name')
                    if list_id and list_name:
                        tmp.append({"name": list_name, "description": l.get('description') or '', "id": list_id, "icon": self.logo})
                except Exception as e: self.log(f"get_lists, failed! Error fetching user profile: {e}")
        if not tmp:
            for link in soup.find_all("a", href=True):
                try:
                    href = link['href']
                    if "/list/ls" in href:
                        list_id = href.split('/')[2]
                        name = link.get_text(strip=True)
                        if list_id.startswith('ls') and name and not any(x['id'] == list_id for x in tmp):
                            tmp.append({"name": name, "id": list_id, "icon": self.logo})
                except Exception as e: self.log(f"get_lists, failed! Error fetching user profile: {e}")
        return sorted(tmp, key=itemgetter('name'))


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_list_items(self, list_id):
        self.log('get_list_items, list_id = %s'%(list_id))
        headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/csv,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        tmp = {}
        try:
            response = requests.get(f"https://www.imdb.com/list/{list_id}/export", headers=headers, timeout=15)
            response.raise_for_status()
            tmp = self._parse_csv(response.text)
            if tmp: return tmp
            self.log('get_list_items, csv empty for %s, falling back to page scrape'%(list_id))
        except Exception as e:
            self.log('get_list_items, csv failed for %s! %s, falling back to page scrape'%(list_id, e))
        return self._parse_page(list_id, headers)
