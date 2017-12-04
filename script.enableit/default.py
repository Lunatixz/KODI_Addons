#   Copyright (C) 2016 Lunatixz
#
#
# This file is part of Enable it!.
#
# Enable it! is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Enable it! is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Enable it!.  If not, see <http://www.gnu.org/licenses/>.

import re, os, sys
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
    
# Plugin Info
ADDON_ID      = 'script.enableit'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID      = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = os.path.join(ADDON_PATH, 'icon.png')
FANART        = os.path.join(ADDON_PATH, 'fanart.jpg')

CONTENTS = ["unknown",
            "video",
            "audio",
            "image",
            "executable"]
            
TYPES    = ["unknown",
            "xbmc.player.musicviz",
            "xbmc.gui.skin",
            "xbmc.pvrclient",
            "kodi.adsp",
            "kodi.inputstream",
            "kodi.peripheral",
            "xbmc.python.script",
            "xbmc.python.weather",
            "xbmc.subtitle.module",
            "xbmc.python.lyrics",
            "xbmc.metadata.scraper.albums",
            "xbmc.metadata.scraper.artists",
            "xbmc.metadata.scraper.movies",
            "xbmc.metadata.scraper.musicvideos",
            "xbmc.metadata.scraper.tvshows",
            "xbmc.ui.screensaver",
            "xbmc.python.pluginsource",
            "xbmc.addon.repository",
            "xbmc.webinterface",
            "xbmc.service",
            "xbmc.audioencoder",
            "kodi.context.item",
            "kodi.audiodecoder",
            "kodi.resource.images",
            "kodi.resource.language",
            "kodi.resource.uisounds",
            "xbmc.addon.video",
            "xbmc.addon.audio",
            "xbmc.addon.image",
            "xbmc.addon.executable",
            "xbmc.metadata.scraper.library",
            "xbmc.python.library",
            "xbmc.python.module",
            "kodi.game.controller"]

CONTENT_TYPES = ["xbmc.python.script","xbmc.addon.repository","xbmc.addon.video","xbmc.addon.audio","xbmc.addon.image","xbmc.addon.executable","xbmc.python.library","xbmc.python.module"]#todo ask users to enable disable
        
        
def set_Kodi_JSON(params):
    xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params)
    
def set_Kodi_Enabled(plugin):
    set_Kodi_JSON('"method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":true}'%plugin)
        
def get_Kodi_JSON(params):
    return json.loads(unicode(xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params), 'utf-8', errors='ignore'))
    
def get_Kodi_Disabled(type,content):
     return get_Kodi_JSON('"method":"Addons.GetAddons","params":{"type":"%s","content":"%s","enabled":false,"installed":true}'%(type,content))

if xbmcgui.Dialog().yesno(ADDON_NAME, 'Enable all disabled plugins?'):
    percent       = 0
    count         = 0
    loop          = 0
    details       = []
    dlg           = xbmcgui.DialogProgress()
    dlg.create(ADDON_NAME)
    
    for content in CONTENTS:
        for type in CONTENT_TYPES:
            loop += 1
            if (dlg.iscanceled()):
                dlg.close()
                break
            percent = loop * 100 // len(CONTENT_TYPES)
            dlg.update(percent)
            details.append(get_Kodi_Disabled(type,content))
            
    for json_response in details:
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('addons'):
            count   = 0
            for item in json_response['result']['addons']:
                if (dlg.iscanceled()):
                    dlg.close()
                    break
                dlg.update((count * 100 // len(json_response['result']['addons'])),'Checking: %s'%item['type'],'Enabling: %s'%item['addonid'])
                set_Kodi_Enabled(item['addonid'])
                xbmc.sleep(10)
    dlg.update(100)
    dlg.close()
    
    
    
    
    
    
    
    
    
        