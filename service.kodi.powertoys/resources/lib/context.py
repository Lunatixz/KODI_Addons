#   Copyright (C) 2026 Lunatixz
#
# This file is part of Kodi PowerToys
# Kodi PowerToys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# -*- coding: utf-8 -*-
import sys, json, xbmc, xbmcaddon

ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')

def notify(message, data=None):
    cmd = {"jsonrpc":"2.0","method":"JSONRPC.NotifyAll",
           "params":{"sender":ADDON_ID,"message":message,"data":data or {}},
           "id":ADDON_ID}
    xbmc.executeJSONRPC(json.dumps(cmd))

def main():
    if not ADDON.getSettingBool('Report_Context_Menu'): return
    action = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
    if   action == 'clean_show':
        dbid = xbmc.getInfoLabel('ListItem.DBID')
        if dbid: notify('CleanTVShow', {'tvshowid': int(dbid)})
    elif action == 'clean_movie':
        dbid = xbmc.getInfoLabel('ListItem.DBID')
        if dbid: notify('CleanMovie', {'movieid': int(dbid)})
    elif action == 'scan_folder':
        path = xbmc.getInfoLabel('ListItem.Path') or xbmc.getInfoLabel('ListItem.FolderPath')
        if path: notify('ScanFolder', {'path': path})
    elif action == 'health_report':
        notify('HealthReport')

if __name__ == '__main__': main()
