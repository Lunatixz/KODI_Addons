#   Copyright (C) 2020 Lunatixz
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

# -*- coding: utf-8 -*-
from globals import *

def set_Kodi_JSON(params):
    xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params)
    
def get_Kodi_JSON(params):
    return json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params))

def set_Kodi_Plugin_State(plugin,enabled="true"):
    set_Kodi_JSON('"method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":%s}'%(plugin,enabled))
        
def get_Kodi_Plugin_State(type,content,enabled="false"):
     return get_Kodi_JSON('"method":"Addons.GetAddons","params":{"type":"%s","content":"%s","enabled":%s,"installed":true}'%(type,content,enabled))

if xbmcgui.Dialog().yesno(ADDON_NAME,LANGUAGE(30006)):
    details = []
    Content_pselect = REAL_SETTINGS.getSetting('PreSelect_CONTENTS').split('|')
    Content_Items   = [citem for idx, citem in enumerate(CONTENTS) if str(idx) in Content_pselect]
    Types_pselect   = REAL_SETTINGS.getSetting('PreSelect_CONTENT_TYPES').split('|')
    Types_Items     = [citem for idx, citem in enumerate(CONTENT_TYPES) if str(idx) in Types_pselect]

    if len(Content_Items) == 0: 
        xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(30008), LANGUAGE(30009), LANGUAGE(30010))
        REAL_SETTINGS.openSettings()
    else:
        if ENABLE: msg = 'Enabling'
        else: msg = 'Disabling'
            
        dlg = xbmcgui.DialogProgress()
        dlg.create(ADDON_NAME)
        for content in Content_Items:
            for idx, type in enumerate(Types_Items):
                if (dlg.iscanceled()):
                    dlg.close()
                    break
                dlg.update(idx * 100 // len(Types_Items))
                if ENABLE: details.append(get_Kodi_Plugin_State(type,content,"false"))
                else: details.append(get_Kodi_Plugin_State(type,content,"true"))
                
        for count, json_response in enumerate(details):
            if 'result' in json_response:
                items = json_response['result'].get('addons',[])
                for item in items:
                    if (dlg.iscanceled()):
                        dlg.close()
                        break
                    dlg.update((count * 100 // len(items)),'Checking: %s'%item['type'],'%s: %s'%(msg,item['addonid']))
                    if ENABLE: set_Kodi_Plugin_State(item['addonid'],"true")
                    else: set_Kodi_Plugin_State(item['addonid'],"false")
                    xbmc.sleep(10)
        dlg.update(100)
        dlg.close()