#   Copyright (C) 2026 Lunatixz
#
#
# This file is part of Kodi PowerToys
#
# Kodi PowerToys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Kodi PowerToys is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kodi PowerToys.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-
from globals import *

NETWORK_PROTO = ('smb://', 'nfs://', 'ftp://', 'dav://', 'sftp://')

def tlog(msg, level=xbmc.LOGDEBUG):
    log('TextureManager: %s' % msg, level)

def getTextures():
    return sendJSON({"method": "Textures.GetTextures"}).get('result', {}).get('textures', [])

def removeTexture(textureid):
    return sendJSON({"method": "Textures.RemoveTexture", "params": {"textureid": textureid}}).get('result') == "OK"

def _libraryArtURLs():
    urls = set()
    try:
        for movie in (sendJSON({"method": "VideoLibrary.GetMovies", "params": {"properties": ["art"]}}).get('result', {}).get('movies', [])):
            urls.update((movie.get('art') or {}).values())
        for show in (sendJSON({"method": "VideoLibrary.GetTVShows", "params": {"properties": ["art"]}}).get('result', {}).get('tvshows', [])):
            urls.update((show.get('art') or {}).values())
        for artist in (sendJSON({"method": "AudioLibrary.GetArtists", "params": {"properties": ["art"]}}).get('result', {}).get('artists', [])):
            urls.update((artist.get('art') or {}).values())
        for album in (sendJSON({"method": "AudioLibrary.GetAlbums", "params": {"properties": ["art"]}}).get('result', {}).get('albums', [])):
            urls.update((album.get('art') or {}).values())
    except Exception as e:
        tlog('libraryArtURLs error: %s' % e, xbmc.LOGWARNING)
    return urls

def _isNetworkPath(url):
    return any((url or '').lower().startswith(p) for p in NETWORK_PROTO)

def prune(dry_run=True):
    delete_files = REAL_SETTINGS.getSettingBool('Texture_Delete_Files') and not REAL_SETTINGS.getSettingBool('Dry_Run_Enabled')
    referenced = _libraryArtURLs()
    removed = 0
    for tex in getTextures():
        url = (tex.get('url') or '').replace('image://', '')
        if not _isNetworkPath(url): continue
        if url in referenced: continue
        if dry_run:
            tlog('prune [DRY RUN] would remove: %s' % tex.get('url'))
        elif removeTexture(tex.get('id')):
            removed += 1
            tlog('prune removed texture id %s: %s' % (tex.get('id'), tex.get('url')))
            if delete_files and tex.get('cachedurl'):
                path = 'special://thumbnails/%s' % tex.get('cachedurl')
                if xbmcvfs.exists(path):
                    xbmcvfs.delete(path)
                    tlog('prune deleted file: %s' % path)
    if dry_run: tlog('prune [DRY RUN] complete')
    return removed

def recache_missing(dry_run=True):
    removed = 0
    for tex in getTextures():
        cachedurl = tex.get('cachedurl')
        if not cachedurl: continue
        path = 'special://thumbnails/%s' % cachedurl
        if xbmcvfs.exists(path): continue
        if dry_run:
            tlog('recache [DRY RUN] would remove stale row: %s' % tex.get('url'))
        elif removeTexture(tex.get('id')):
            removed += 1
            tlog('recache removed stale row id %s: %s' % (tex.get('id'), tex.get('url')))
    if dry_run: tlog('recache [DRY RUN] complete')
    return removed

def cache_stats():
    textures = getTextures()
    total = 0
    for tex in textures:
        cachedurl = tex.get('cachedurl')
        if not cachedurl: continue
        try:    total += xbmcvfs.Stat('special://thumbnails/%s' % cachedurl).st_size()
        except: pass
    return len(textures), total

def format_size(nbytes):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if nbytes < 1024: return '%.1f %s' % (nbytes, unit)
        nbytes /= 1024.0
    return '%.1f TB' % nbytes
