#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of Smartthing Monitor.
#
# Smartthing Monitor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smartthing Monitor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smartthing Monitor.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import urllib, urllib2, socket, requests, json, traceback
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

# Plugin Info
ADDON_ID      = 'service.smartthings'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

# Globals
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == "true"
USERNAME      = (REAL_SETTINGS.getSetting('User_Email')  or None)
PASSWORD      = REAL_SETTINGS.getSetting('User_Password')
HUB_ID        = (REAL_SETTINGS.getSetting('Hub_ID') or None)
ACC_ID        = (REAL_SETTINGS.getSetting('Acc_ID') or None)
BASE_URL      = 'https://graph.api.smartthings.com/api'

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def notification(str1, header=ADDON_NAME):
    xbmcgui.Dialog().notification(header, str1, ICON, 4000)

#todo move to proper api token, allow device control.
socket.setdefaulttimeout(30)
class STAPI(object):
    def __init__(self):
        self.username   = USERNAME
        self.password   = PASSWORD
        
        
    def openURL(self, url, params=None, method='GET', ):
        log('openURL, url = ' + url)
        print self.username
        try:
            headers = {'Accept': 'application/json'}
            if params: params = urllib.urlencode(params, True).replace('+', '%20')
            if method == 'GET': request = requests.get(BASE_URL+url, auth=(self.username, self.password), params=params, headers=headers)
            elif method == 'POST': request = requests.post(BASE_URL+url, auth=(self.username, self.password), params=params, headers=headers)
            try: response = request.json()
            except: response = request.text
            print response
            if response and 'error' in response and response['error'] == 'unauthorized': raise Exception()
            return response
        except:
            notification(LANGUAGE(30003))
         
         
    def accounts(self):
        url = "/accounts"
        return self.openURL(url)

        
    def locations(self, account_id=ACC_ID):
        url = "/accounts/" + account_id + "/locations"
        return self.openURL(url)

        
    def events(self, account_id=ACC_ID, max=10, all=False, source=''):
        url = "/accounts/" + account_id + "/events"
        params = {'all': all, 'source': source, 'max': max}
        return self.openURL(url, params=params)

        
    def hubs(self):
        url = "/hubs"
        return self.openURL(url)

        
    def hub(self, hub_id=HUB_ID):
        url = "/hubs/" + hub_id
        return self.openURL(url)

        
    def hub_events(self, hub_id, max=10, all=False, source=None):
        url = "/hubs/" + hub_id + "/events"
        params = {'all': all, 'source': source, 'max': max}
        return self.openURL(url, params=params)

        
    def hub_devices(self, hub_id=HUB_ID):
        url = "/hubs/" + hub_id + "/devices"
        return self.openURL(url)

        
    def device(self, device_id):
        url = "/devices/" + device_id
        return self.openURL(url)

        
    def device_events(self, device_id, max=10, all=False, source=None):
        url = "/devices/" + device_id + "/events"
        params = {'all': all, 'source': source, 'max': max}
        return self.openURL(url, params=params)

        
    def device_roles(self, device_id):
        url = "/devices/" + device_id + "/roles"
        return self.openURL(url)

        
    def device_types(self):
        url = "/devicetypes"
        return self.openURL(url)

        
    def device_icons(self):
        url = "/devices/icons"
        return self.openURL(url)