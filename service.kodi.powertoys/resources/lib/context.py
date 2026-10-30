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

def log(msg):
    # INFO level: visible in kodi.log even with addon debugging off - this script
    # runs out-of-process, so its failures otherwise vanish without a trace
    xbmc.log('[%s/context] %s' % (ADDON_ID, msg), xbmc.LOGINFO)

def _dbid(label='ListItem.DBID'):
    raw = xbmc.getInfoLabel(label)
    log('%s = %r' % (label, raw))
    try:
        return int(raw)
    except (TypeError, ValueError):
        if raw:
            # non-empty but unreadable id (skin/odd node) - say it instead of dying silently
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), 'Cannot read %s: %s' % (label, raw), xbmcgui.NOTIFICATION_WARNING, 4000)
        return None

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

def _main():
    if not ADDON.getSettingBool('Report_Context_Menu'): return
    action = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
    log('action=%r argv=%r' % (action, sys.argv))
    if   action == 'clean_show':
        dbid = _dbid()
        if dbid is not None: notify('CleanTVShow', {'tvshowid': dbid})
    elif action == 'clean_movie':
        dbid = _dbid()
        if dbid is not None: notify('CleanMovie', {'movieid': dbid})
    elif action == 'clean_season':
        showid = _dbid('ListItem.TVShowDBID')
        raw = xbmc.getInfoLabel('ListItem.Season')
        log('ListItem.Season = %r' % (raw,))
        if showid is None or raw == '': return
        season = int(raw)
        eps = _json('VideoLibrary.GetEpisodes', {'tvshowid': showid, 'properties': ['file','season','showtitle']}).get('result',{}).get('episodes', [])
        eps = [e for e in eps if e.get('season') == season]
        if not eps: return  # empty season - nothing to confirm
        total = sum(_fsize(e.get('file')) for e in eps)
        body = '%s - Season %d\n%d episode(s), %s' % (eps[0].get('showtitle',''), season, len(eps), _fmt(total))
        if _yesno(32062, body, "this season's episodes"): notify('CleanSeason', {'tvshowid': showid, 'season': season})
    elif action in ('mark_watched_season', 'mark_watched_show'):
        if action == 'mark_watched_season':
            showid = _dbid('ListItem.TVShowDBID')
            raw = xbmc.getInfoLabel('ListItem.Season')
            if showid is None or raw == '': return
            msg, data = 'WatchSeason', {'tvshowid': showid, 'season': int(raw)}
        else:
            dbid = _dbid()
            if dbid is None: return
            msg, data = 'WatchShow', {'tvshowid': dbid}
        idx = xbmcgui.Dialog().select(LANGUAGE(32065 if action == 'mark_watched_season' else 32066),
                                      [LANGUAGE(32067), LANGUAGE(32068)])
        if idx < 0: return
        data['watched'] = (idx == 0)
        notify(msg, data)
    elif action == 'remove_movie':
        dbid = _dbid()
        if dbid is None: return
        d = _json('VideoLibrary.GetMovieDetails', {'movieid': dbid, 'properties': ['label','file']}).get('result',{}).get('movie')
        if not d: return
        body = d.get('label','')
        size = _fsize(d.get('file'))
        if size: body = '%s\n%s' % (body, _fmt(size))
        if _yesno(32087, body, 'this movie'): notify('RemoveMovie', {'movieid': dbid})
    elif action == 'remove_episode':
        dbid = _dbid()
        if dbid is None: return
        d = _json('VideoLibrary.GetEpisodeDetails', {'episodeid': dbid, 'properties': ['file','showtitle','title','season','episode']}).get('result',{}).get('episode')
        if not d: return
        body = '%s - S%02dE%02d %s' % (d.get('showtitle',''), d.get('season') or 0, d.get('episode') or 0, d.get('title',''))
        size = _fsize(d.get('file'))
        if size: body = '%s\n%s' % (body, _fmt(size))
        if _yesno(32088, body, 'this episode'): notify('RemoveEpisode', {'episodeid': dbid})
    elif action == 'remove_show':
        dbid = _dbid()
        if dbid is None: return
        d = _json('VideoLibrary.GetTVShowDetails', {'tvshowid': dbid, 'properties': ['title']}).get('result',{}).get('tvshow')
        title = (d or {}).get('title','')
        eps = _json('VideoLibrary.GetEpisodes', {'tvshowid': dbid, 'properties': ['file']}).get('result',{}).get('episodes', [])
        total = sum(_fsize(e.get('file')) for e in eps)
        body = '%s\n%d episode(s), %s' % (title, len(eps), _fmt(total))
        if _yesno(32089, body, 'this show (all seasons and episodes)'): notify('RemoveTVShow', {'tvshowid': dbid})
    elif action == 'scan_folder':
        path = xbmc.getInfoLabel('ListItem.Path') or xbmc.getInfoLabel('ListItem.FolderPath')
        if path: notify('ScanFolder', {'path': path})
    elif action == 'health_report':
        notify('HealthReport')
    else:
        log('unknown action - nothing dispatched')

def main():
    try:
        _main()
    except Exception as e:
        # a context script dies silently otherwise - always say why
        log('context action failed: %s' % e)
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), 'Context action failed: %s' % e, xbmcgui.NOTIFICATION_ERROR, 5000)

if __name__ == '__main__': main()
