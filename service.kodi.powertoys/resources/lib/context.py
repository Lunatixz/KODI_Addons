#   Copyright (C) 2026 Lunatixz
#
# This file is part of Kodi PowerToys
# Kodi PowerToys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# -*- coding: utf-8 -*-
import sys, json, xbmc, xbmcaddon, xbmcgui

ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')
LANGUAGE   = ADDON.getLocalizedString

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
    elif action == 'clean_season':
        showid, season = xbmc.getInfoLabel('ListItem.TVShowDBID'), xbmc.getInfoLabel('ListItem.Season')
        if showid and season != '': notify('CleanSeason', {'tvshowid': int(showid), 'season': int(season)})
    elif action in ('mark_watched_season', 'mark_watched_show'):
        if action == 'mark_watched_season':
            showid, season = xbmc.getInfoLabel('ListItem.TVShowDBID'), xbmc.getInfoLabel('ListItem.Season')
            if not showid or season == '': return
            msg, data = 'WatchSeason', {'tvshowid': int(showid), 'season': int(season)}
        else:
            dbid = xbmc.getInfoLabel('ListItem.DBID')
            if not dbid: return
            msg, data = 'WatchShow', {'tvshowid': int(dbid)}
        idx = xbmcgui.Dialog().select(LANGUAGE(32065 if action == 'mark_watched_season' else 32066),
                                      [LANGUAGE(32067), LANGUAGE(32068)])
        if idx < 0: return
        data['watched'] = (idx == 0)
        notify(msg, data)
    elif action == 'scan_folder':
        path = xbmc.getInfoLabel('ListItem.Path') or xbmc.getInfoLabel('ListItem.FolderPath')
        if path: notify('ScanFolder', {'path': path})
    elif action == 'health_report':
        notify('HealthReport')

if __name__ == '__main__': main()
