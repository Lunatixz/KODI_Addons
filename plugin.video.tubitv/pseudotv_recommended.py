#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of TubiTV.
#
# TubiTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# TubiTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TubiTV.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

"""PseudoTV Live / IPTV Manager Integration module"""
import os, re, json, time
from kodi_six    import xbmc, xbmcaddon, xbmcgui, xbmcvfs

# Plugin Info
ADDON_ID      = 'plugin.video.tubitv'
PROP_KEY      = 'PseudoTV_Recommended.%s'%(ADDON_ID)
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
MONITOR       = xbmc.Monitor()
LOGO          = os.path.join('special://home/addons/%s/'%(ADDON_ID),'resources','images','logo.png')

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

def load(text):
    try:    return json.loads(text)
    except: return {} 
    
class regPseudoTV:
    def __init__(self):
        ...
        
        
    def getDirs(self, path, version):
        json_query = '{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","properties":["file","art"]},"id":1}'%(path)
        return xbmc.executeJSONRPC(json_query)


    def chkVOD(self):
        return (time.time() > (float(xbmcgui.Window(10000).getProperty('Last_VOD') or '0') + 3600))
   

    def run(self):
        while not MONITOR.abortRequested():
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.pseudotv.live)'):   
                try:    asset = json.loads(xbmcgui.Window(10000).getProperty(PROP_KEY))
                except: asset = {}
                
                if self.chkVOD():# Build Recommend VOD
                    asset['vod'] = [] #clear older list
                    items = load(self.getDirs('plugin://%s'%(ADDON_ID),ADDON_VERSION)).get('result',{}).get('files',[])
                    for item in items:
                        if item.get('filetype') == 'directory':
                            label = '%s (%s)'%(item.get('label'),ADDON_NAME)
                            plot  = (item.get("plot","") or item.get("plotoutline","") or item.get("description",""))
                            asset.setdefault('vod',[]).append({'type':'vod','name':label,'description':plot,'icon':LOGO,'path':item.get('file'),'id':ADDON_ID})
                    xbmcgui.Window(10000).setProperty('Last_VOD',str(time.time()))
                xbmcgui.Window(10000).setProperty(PROP_KEY, json.dumps(asset))
                WAIT_TIME = 900
            else: 
                xbmcgui.Window(10000).clearProperty(PROP_KEY)
                WAIT_TIME = 300
            if MONITOR.waitForAbort(WAIT_TIME): break
if __name__ == '__main__': regPseudoTV().run()