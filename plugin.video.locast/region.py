#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of Locast.
#
# Locast is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Locast is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Locast.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import sys, os, re, json, requests, datetime

from simplecache   import SimpleCache, use_cache
from kodi_six      import xbmcaddon, xbmcgui, xbmc

# Plugin Info
ADDON_ID      = 'plugin.video.locast'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
BASE_URL      = 'https://www.locast.org'
BASE_API      = 'https://api.locastnet.org/api'
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'

def selectDialog(list, header=ADDON_NAME, preselect=-1, useDetails=True, autoclose=0):
    return xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
    
def notificationDialog(message, header=ADDON_NAME, sound=False, time=1000, icon=ICON):
    try:    return xbmcgui.Dialog().notification(header, message, icon, time, sound)
    except: return xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg), level)
         
class Region(object):
    def __init__(self, sysARG=sys.argv):
        self.cache = SimpleCache()
        self.token = (REAL_SETTINGS.getSetting('User_Token') or None)
        
        
    def buildHeader(self):
        header_dict                  = {}
        header_dict['Accept']        = 'application/json, text/javascript, */*; q=0.01'
        header_dict['Content-Type']  = 'application/json'
        header_dict['Connection']    = 'keep-alive'
        header_dict['Origin']        = BASE_URL
        header_dict['Referer']       = BASE_URL
        header_dict['Authorization'] = "Bearer %s" % self.token
        header_dict['User-Agent']    = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'
        return header_dict
        
        
    def getURL(self, url, param={}, header={'Content-Type':'application/json'}, life=datetime.timedelta(minutes=5)):
        log('getURL, url = %s, header = %s'%(url, header))
        cacheresponse = self.cache.get(ADDON_NAME + '.getURL, url = %s.%s.%s'%(url,param,header))
        if not cacheresponse:
            try:
                req = requests.get(url, param, headers=header)
                try: cacheresponse = req.json()
                except: return {}
                req.close()
                self.cache.set(ADDON_NAME + '.getURL, url = %s.%s.%s'%(url,param,header), json.dumps(cacheresponse), expiration=life)
                return cacheresponse
            except Exception as e: 
                log("getURL, Failed! %s"%(e), xbmc.LOGERROR)
                notificationDialog(LANGUAGE(30001))
                return {}
        else: return json.loads(cacheresponse)


    def getCities(self):
        log("getCities")
        return self.getURL(BASE_API + '/dma',header=self.buildHeader())


    def listRegions(self):
        log('listRegions')
        cities = sorted(self.getCities(), key=lambda k: k['name'])
        def getListItem():
            for k in cities:
                if k.get('name') == 'Lab': continue
                listitem = xbmcgui.ListItem(k.get('name'),path=str(k.get('id')))
                listitem.setArt({'thumb':k.get('imageLargeUrl')})
                yield listitem
                
        listItems = list(getListItem())
        pselect = ([idx for idx, dma in enumerate(listItems) if dma.getPath() == (REAL_SETTINGS.getSetting('User_Select_DMA') or REAL_SETTINGS.getSetting('User_DMA'))] or [-1])[0]
        select  = selectDialog(listItems,header='%s %s'%(ADDON_NAME,LANGUAGE(49013)),preselect=pselect)
        REAL_SETTINGS.setSetting('User_Select_DMA' ,listItems[select].getPath())
        REAL_SETTINGS.setSetting('User_Select_City',listItems[select].getLabel())
        REAL_SETTINGS.openSettings()
        xbmc.executebuiltin("RunScript(service.iptv.manager,refresh)")
if __name__ == '__main__': Region(sys.argv).listRegions()