#   Copyright (C) 2026 Lunatixz
#
# This file is part of Kodi PowerToys
# Kodi PowerToys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# -*- coding: utf-8 -*-
import sys, json, xbmc, xbmcaddon, xbmcgui, xbmcvfs

ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')
LANGUAGE   = ADDON.getLocalizedString

def notify(message, data=None):
    cmd = {"jsonrpc":"2.0","method":"JSONRPC.NotifyAll",
           "params":{"sender":ADDON_ID,"message":message,"data":data or {}},
           "id":ADDON_ID}
    xbmc.executeJSONRPC(json.dumps(cmd))

def _json(method, params=None):
    cmd = {"jsonrpc":"2.0","method":method,"params":params or {},"id":ADDON_ID}
    return json.loads(xbmc.executeJSONRPC(json.dumps(cmd)))

def _fmt(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024: return ('%d %s' % (n, unit)) if unit == 'B' else ('%.1f %s' % (n, unit))
        n /= 1024.0
    return '%.1f PB' % n

def _fsize(path):
    try:
        if path and xbmcvfs.exists(path): return xbmcvfs.Stat(path).st_size()
    except Exception: pass
    return 0

def _action(entry):
    # spell out exactly what confirming will do, derived from the live gate settings
    txt = 'Remove %s from the library' % entry
    if not ADDON.getSettingBool('Dry_Run_Enabled'):
        txt += ' and delete the file(s) from disk' if ADDON.getSettingBool('Delete_Enabled') else ' (files kept on disk)'
    return txt + '?'

def _yesno(heading_id, body, entry):
    # one clear yes/no gate: identifying info, size, then exactly what happens on Yes.
    # prompts fire HERE, immediately on click - execution queues behind them, so rapid
    # multi-item confirmations breeze through instead of waiting on the task queue
    body = '%s\n\n%s' % (body, _action(entry))
    if ADDON.getSettingBool('Dry_Run_Enabled'): body = '[DRY RUN]\n%s' % body
    return xbmcgui.Dialog().yesno(LANGUAGE(heading_id), body)

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
        if not showid or season == '': return
        showid, season = int(showid), int(season)
        eps = _json('VideoLibrary.GetEpisodes', {'tvshowid': showid, 'properties': ['file','season','showtitle']}).get('result',{}).get('episodes', [])
        eps = [e for e in eps if e.get('season') == season]
        if not eps: return  # empty season - nothing to confirm
        total = sum(_fsize(e.get('file')) for e in eps)
        body = '%s - Season %d\n%d episode(s), %s' % (eps[0].get('showtitle',''), season, len(eps), _fmt(total))
        if _yesno(32062, body, "this season's episodes"): notify('CleanSeason', {'tvshowid': showid, 'season': season})
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
    elif action == 'remove_movie':
        dbid = xbmc.getInfoLabel('ListItem.DBID')
        if not dbid: return
        d = _json('VideoLibrary.GetMovieDetails', {'movieid': int(dbid), 'properties': ['label','file']}).get('result',{}).get('movie')
        if not d: return
        body = d.get('label','')
        size = _fsize(d.get('file'))
        if size: body = '%s\n%s' % (body, _fmt(size))
        if _yesno(32087, body, 'this movie'): notify('RemoveMovie', {'movieid': int(dbid)})
    elif action == 'remove_episode':
        dbid = xbmc.getInfoLabel('ListItem.DBID')
        if not dbid: return
        d = _json('VideoLibrary.GetEpisodeDetails', {'episodeid': int(dbid), 'properties': ['file','showtitle','title','season','episode']}).get('result',{}).get('episode')
        if not d: return
        body = '%s - S%02dE%02d %s' % (d.get('showtitle',''), d.get('season') or 0, d.get('episode') or 0, d.get('title',''))
        size = _fsize(d.get('file'))
        if size: body = '%s\n%s' % (body, _fmt(size))
        if _yesno(32088, body, 'this episode'): notify('RemoveEpisode', {'episodeid': int(dbid)})
    elif action == 'remove_show':
        dbid = xbmc.getInfoLabel('ListItem.DBID')
        if not dbid: return
        d = _json('VideoLibrary.GetTVShowDetails', {'tvshowid': int(dbid), 'properties': ['title']}).get('result',{}).get('tvshow')
        title = (d or {}).get('title','')
        eps = _json('VideoLibrary.GetEpisodes', {'tvshowid': int(dbid), 'properties': ['file']}).get('result',{}).get('episodes', [])
        total = sum(_fsize(e.get('file')) for e in eps)
        body = '%s\n%d episode(s), %s' % (title, len(eps), _fmt(total))
        if _yesno(32089, body, 'this show (all seasons and episodes)'): notify('RemoveTVShow', {'tvshowid': int(dbid)})
    elif action == 'scan_folder':
        path = xbmc.getInfoLabel('ListItem.Path') or xbmc.getInfoLabel('ListItem.FolderPath')
        if path: notify('ScanFolder', {'path': path})
    elif action == 'health_report':
        notify('HealthReport')

if __name__ == '__main__': main()
