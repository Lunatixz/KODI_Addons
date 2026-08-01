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
    def __init__(self, cache=None):
        self.monitor = MONITOR()
        if cache is None: self.cache = SimpleCache()
        else:
            self.cache = cache
            self.cache.enable_mem_cache = False
        
        self.enabled = REAL_SETTINGS.getSetting('Enable_Trakt') == 'true'
        self.name    = LANGUAGE(32100)
        self.logo    = os.path.join(ADDON_PATH,'resources','images','trakt.png')
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def convert_type(self, list_type):
        return {'movie':'movies','show':'tvshows','season':'seasons','episode':'episodes'}[list_type]


    def clean_string(self, string):
        return string.replace('copy','').replace('\r\n\t','').rstrip()
        
        
    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_lists(self):
        if not self.enabled: return []
        tmp = []
        trakt_user   = REAL_SETTINGS.getSetting('Trakt_Username')
        access_token = REAL_SETTINGS.getSetting('Trakt_TokenID')
        url = f"https://api.trakt.tv/users/{trakt_user}/lists"
        self.log('get_lists, trakt_user = %s, url = %s'%(trakt_user,url))
        headers = { 'Content-Type': 'application/json',
                    'trakt-api-version': '2',
                    'trakt-api-key': REAL_SETTINGS.getSetting('Trakt_ClientID')}
        if access_token: headers['Authorization'] = f'Bearer {access_token}'
        current_page   = 1
        limit = 1000 # Maximize to reduce calls
        while not self.monitor.abortRequested():
            params   = {'page': current_page, 'limit': limit}
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200: 
                self.log("get_lists, failed! to fetch data from Trakt: %s"%(response.status_code))
                break
            else:
                for item in response.json(): 
                    tmp.append({'name':self.clean_string(item.get('name')),'description':self.clean_string(item.get('description')),'id':str(item.get('ids',{}).get('trakt')),'icon':self.logo})
                # X-Pagination-Page-Count: Total pages available
                # X-Pagination-Item-Count: Total items across all pages
                total_pages = int(response.headers.get('X-Pagination-Page-Count', 1))
                total_items = int(response.headers.get('X-Pagination-Item-Count', 0))
                self.log(f"get_lists, Fetched page {current_page}/{total_pages} (Total Items: {total_items})")
                if current_page >= total_pages: break
                elif self.monitor.waitForAbort(0.5): break
                current_page += 1
        return sorted(tmp,key=itemgetter('name'))
                
            
    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_list_items(self, list_id):
        tmp = {}
        limit = 1000 # Maximize to reduce calls
        for list_type in ['movie','show','season','episode','person']:
            page = 1
            while not self.monitor.abortRequested():
                url = f"https://api.trakt.tv/lists/{list_id}/items/{list_type}"
                params  = {'page': page, 'limit': limit}
                headers = {
                    'Content-Type': 'application/json',
                    'trakt-api-version': '2',
                    'trakt-api-key': REAL_SETTINGS.getSetting('Trakt_ClientID')}
                response = requests.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    self.log("get_list_items, failed! to fetch data from Trakt: %s [%s]"%(response.status_code,list_type))
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
                    # Check if more pages exist via Trakt headers
                    total_pages = int(response.headers.get('X-Pagination-Page-Count', 1))
                    if page >= total_pages: break
                    page += 1
        return tmp


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def get_trakt_person(self, trakt_id):
        tmp   = {}
        limit = 1000 # Maximize to reduce calls
        urls  = {'movie':f"https://api.trakt.tv/people/{trakt_id}/movies",
                 'show' :f"https://api.trakt.tv/people/{trakt_id}/shows"}
        headers = { 'Content-Type': 'application/json',
                    'trakt-api-version': '2',
                    'trakt-api-key': REAL_SETTINGS.getSetting('Trakt_ClientID')}
        for list_type, url in list(urls.items()):
            page = 1
            while not self.monitor.abortRequested():
                params   = {'page': page, 'limit': limit}
                response = requests.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    self.log("get_trakt_person, failed! to fetch data from Trakt: %s"%(response.status_code))
                    break
                else:
                    for item in response.json().get('cast',[]):
                        tmp.setdefault(self.convert_type(list_type),[]).append({'type':list_type,'title':item.get(list_type,{}).get('title'),'year':item.get(list_type,{}).get('year'),'season':item.get(list_type,{}).get('number'),'uniqueid':item.get(list_type,{}).get('ids'),'data':item})
                    total_pages = int(response.headers.get('X-Pagination-Page-Count', 1))
                    if page >= total_pages: break
                    page += 1
        return tmp
