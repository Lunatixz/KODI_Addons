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
from globals import *

class Trakt:
    def __init__(self, cache=None):
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
    def get_lists(self, trakt_user=REAL_SETTINGS.getSetting('Trakt_Username'), client_id=REAL_SETTINGS.getSetting('Trakt_ClientID')):
        tmp = []
        url = f"https://api.trakt.tv/users/{trakt_user}/lists"
        self.log('get_lists, trakt_user = %s, url = %s'%(trakt_user,url))
        headers = { 'Content-Type': 'application/json',
                    'trakt-api-version': '2',
                    'trakt-api-key': client_id}
        response = requests.get(url, headers=headers)
        if response.status_code == 200: 
            for item in response.json(): 
                tmp.append({'name':self.clean_string(item.get('name')),'description':self.clean_string(item.get('description')),'id':str(item.get('ids',{}).get('trakt')),'icon':self.logo})
        else: self.log("get_lists, failed! to fetch data from Trakt:", response.status_code)
        if len(tmp) > 0: return sorted(tmp,key=itemgetter('name'))
        else:            return None
        

    @cacheit()
    def get_list_items(self, list_id, client_id=REAL_SETTINGS.getSetting('Trakt_ClientID')):
        tmp = {}
        for list_type in ['movie','show','season','episode','person']:
            url = f"https://api.trakt.tv/lists/{list_id}/items/{list_type}"
            self.log('get_list_items, list_id = %s, url = %s'%(list_id,url))
            headers = { 'Content-Type': 'application/json',
                        'trakt-api-version': '2',
                        'trakt-api-key': client_id}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                for item in response.json():
                    if list_type == 'person':
                        for type, items in list(self.get_trakt_person(item.get(list_type,{}).get('ids',{}).get('trakt')).items()):
                            tmp.setdefault(type,[]).extend(items)
                    else:
                        if list_type == 'season' and 'show' in item: item[list_type].update(item.pop('show'))
                        tmp.setdefault(self.convert_type(list_type),[]).append({'type':item.get('type'),'title':item.get(list_type,{}).get('title'),'year':item.get(list_type,{}).get('year'),'season':item.get(list_type,{}).get('number'),'uniqueid':item.get(list_type,{}).get('ids'),'data':item})
            else: self.log("get_list_items, failed! to fetch data from Trakt:", response.status_code)
        if len(tmp) > 0: return tmp
        else:            return None
        
        
    @cacheit()
    def get_trakt_person(self, trakt_id, client_id=REAL_SETTINGS.getSetting('Trakt_ClientID')):
        tmp  = {}
        urls = {'movie':f"https://api.trakt.tv/people/{trakt_id}/movies",
                'show' :f"https://api.trakt.tv/people/{trakt_id}/shows"}
        headers = { 'Content-Type': 'application/json',
                    'trakt-api-version': '2',
                    'trakt-api-key': client_id}
        for list_type, url in list(urls.items()):
            self.log('get_trakt_person, trakt_id = %s, url = %s'%(trakt_id,url))
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                for item in response.json().get('cast',[]):
                    tmp.setdefault(self.convert_type(list_type),[]).append({'type':list_type,'title':item.get(list_type,{}).get('title'),'year':item.get(list_type,{}).get('year'),'season':item.get(list_type,{}).get('number'),'uniqueid':item.get(list_type,{}).get('ids'),'data':item})
            else: self.log("get_trakt_person, failed! to fetch data from Trakt:", response.status_code)
        if len(tmp) > 0: return tmp
        else:            return None