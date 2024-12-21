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

# class IMDB:
    # def __init__(self, cache=None):
        # if cache is None: self.cache = SimpleCache()
        # else:
            # self.cache = cache
            # self.cache.enable_mem_cache = False
        
        # self.enabled = REAL_SETTINGS.getSetting('Enable_Trakt') == 'true'
        # self.name    = LANGUAGE(32100)
        # self.logo    = os.path.join(ADDON_PATH,'resources','images','trakt.png')
        
        
    # def log(self, msg, level=xbmc.LOGDEBUG):
        # return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    # def convert_type(self, list_type):
        # return {'movie':'movies','show':'tvshows','episode':'episodes'}[list_type]


    # def clean_string(self, string):
        # return string.replace('copy','').replace('\r\n\t','')
        
        
    # @cacheit(expiration=datetime.timedelta(minutes=15))
    # def get_lists(self, trakt_user=REAL_SETTINGS.getSetting('Trakt_Username'), client_id=REAL_SETTINGS.getSetting('Trakt_ClientID')):
        # self.log('get_lists, trakt_user = %s'%(trakt_user))
        # tmp = []
        # url = f"https://api.trakt.tv/users/{trakt_user}/lists"
        # headers = { 'Content-Type': 'application/json',
                    # 'trakt-api-version': '2',
                    # 'trakt-api-key': client_id}
        # response = requests.get(url, headers=headers)
        # if response.status_code == 200: 
            # for item in response.json():
                # tmp.append({'name':self.clean_string(item.get('name')),'description':self.clean_string(item.get('description')),'id':str(item.get('ids',{}).get('trakt')),'icon':self.logo})
        # else: self.log("get_lists, failed! to fetch data from Trakt:", response.status_code)
        # if len(tmp) > 0: return tmp
        # else:            return None


# import requests
# from bs4 import BeautifulSoup

# class IMDBSearch:
    # BASE_URL = "https://www.imdb.com"
    
    # def __init__(self, user_id):
        # self.user_id = user_id

    # def get_user_list(self, list_id):
        # url = f"{self.BASE_URL}/user/{self.user_id}/lists/{list_id}"
        # response = requests.get(url)
        # if response.status_code == 200:
            # soup = BeautifulSoup(response.content, "html.parser")
            # movies = []
            # for item in soup.select(".lister-item"):
                # title = item.select_one(".lister-item-header a").text
                # movies.append(title)
            # return movies
        # else:
            # print(f"Failed to retrieve list: {response.status_code}")
            # return []

# # Example usage
# imdb_search = IMDBSearch("ur12345678")
# movies = imdb_search.get_user_list("ls123456789")
# print(movies)


    # @cacheit(expiration=datetime.timedelta(hours=int(REAL_SETTINGS.getSetting('Run_Every')), minutes=15))
    # def get_list_items(self, list_id, client_id=REAL_SETTINGS.getSetting('Trakt_ClientID')):
        # self.log('get_list_items, list_id = %s'%(list_id))
        # tmp = {}
        # for list_type in ['movie','show','episode']:
            # url = f"https://api.trakt.tv/lists/{list_id}/items/{list_type}"
            # headers = { 'Content-Type': 'application/json',
                        # 'trakt-api-version': '2',
                        # 'trakt-api-key': client_id}
            # response = requests.get(url, headers=headers)
            # if response.status_code == 200:
                # for item in response.json():
                    # tmp.setdefault(self.convert_type(list_type),[]).append({'type':item.get('type'),'title':item.get(list_type,{}).get('title'),'year':item.get(list_type,{}).get('title'),'uniqueid':item.get(list_type,{}).get('ids'),'data':item})
            # else: self.log("get_list_items, failed! to fetch data from Trakt:", response.status_code)
        # if len(tmp) > 0: return tmp
        # else:            return None
