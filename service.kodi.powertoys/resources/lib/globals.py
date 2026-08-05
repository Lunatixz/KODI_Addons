#   Copyright (C) 2025 Lunatixz
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
import time, traceback, json, os, platform, re, base64, zlib
import datetime, heapq, random, sys

try:    from simplecache             import SimpleCache
except: from simplecache.simplecache import SimpleCache #pycharm stub

from typing      import Union
from contextlib  import contextmanager
from functools   import wraps
from kodi_six    import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from threading   import Lock, Thread

# Plugin Info
ADDON_ID            = 'service.kodi.powertoys'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE            = REAL_SETTINGS.getLocalizedString

DEFAULT_ENCODING    = "utf-8"

def log(msg, level=xbmc.LOGDEBUG):
    if not REAL_SETTINGS.getSettingBool('Enable_Debugging') and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg = '%s, %s'%(msg,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,str(msg)),level)
    
def dumpJSON(item={}, fle=None, idnt=None, sortkey=False, separators=(',', ':')):
    try:
        if fle and hasattr(item,'write'):    
            json.dump(item, fle, indent=idnt, sort_keys=sortkey, separators=separators)
            return True
        if isinstance(item, (str, bytes)): return item
        return json.dumps(item, indent=idnt, sort_keys=sortkey, separators=separators)
    except Exception as e:
        log('dumpJSON failed! %s'%(e), xbmc.LOGERROR)
        return ''
        
def loadJSON(item=""):
    try:
        if not item: return {}
        if isinstance(item, (dict, list)): return item
        if hasattr(item, 'read'):          return json.load(item)
        if isinstance(item, (str, bytes)): return json.loads(item)
    except json.JSONDecodeError: return {}
    except Exception as e:
        log('loadJSON failed! %s'%(e), xbmc.LOGERROR)
        return {}
        
def cacheit(expiration=datetime.timedelta(hours=1), checksum=ADDON_VERSION, json_data=True):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            method_class = args[0]
            cacheName = "%s.%s"%(method_class.__class__.__name__, method.__name__)
            for item in args[1:]: cacheName += u".%s"%item
            for k, v in list(kwargs.items()): cacheName += u".%s"%(v)
            results = method_class.cache.get(cacheName.lower(), checksum, json_data)
            if results: return results
            return method_class.cache.set(cacheName.lower(), method(*args, **kwargs), checksum, expiration, json_data)
        return wrapper
    return internal
    
def getInfoLabel(key, default=""):
    return (xbmc.getInfoLabel(key) or default)
    
def isScanning():
    return (xbmc.getCondVisibility('Library.IsScanningVideo') or False)

def isPlaying():
    return (xbmc.getCondVisibility('Player.Playing') or False)

def decodeString(base64_bytes):
    try:
        message_bytes = zlib.decompress(base64.b64decode(base64_bytes.encode(DEFAULT_ENCODING)))
        return message_bytes.decode(DEFAULT_ENCODING)
    except Exception as e: return ''

def slugify(s, lowercase=False):
  if lowercase: s = s.lower()
  s = s.strip()
  s = re.sub(r'[^\w\s-]', '', s)
  s = re.sub(r'[\s_-]+', '_', s)
  s = re.sub(r'^-+|-+$', '', s)
  return s

def findDupes(items=[], key='label'):
    if items is None: items = []
    matches = {}
    for item in items:
        if key in item: 
            matches.setdefault(item[key],[]).append(item)
    return {k: v for k, v in matches.items() if len(v) > 1}
    
def timeString2Seconds(string): #hh:mm:ss
    try:    return int(sum(x*y for x, y in zip(list(map(float, string.split(':')[::-1])), (1, 60, 3600, 86400))))
    except: return -1

def notification(message, header=ADDON_NAME, sound=False, time=4000, icon=ICON, show=None):
    log('notificationDialog: %s, show = %s'%(message,show))
    ## - Builtin Icons:
    ## - xbmcgui.NOTIFICATION_INFO
    ## - xbmcgui.NOTIFICATION_WARNING
    ## - xbmcgui.NOTIFICATION_ERROR
    if show:
        try:    xbmcgui.Dialog().notification(header, message, icon, time, sound=sound)
        except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
    return True
         
def sendJSON(param):
    command = dict(param)
    command["jsonrpc"] = "2.0"
    command["id"] = ADDON_ID
    log('sendJSON param [%s]'%(param))
    response = loadJSON(xbmc.executeJSONRPC(dumpJSON(command)))
    if response.get('error'): log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
    return response

def getTVshows():
    return sendJSON({"method":"VideoLibrary.GetTVShows","params":{"properties":["file"]}}).get('result',{}).get('tvshows', [])
       
def getEpisodes(tvshowid):
    return sendJSON({"method":"VideoLibrary.GetEpisodes","params":{"tvshowid":tvshowid,"properties":["file","season","episode","showtitle","tvshowid"]}}).get('result',{}).get('episodes', [])

def getMovies():
    return sendJSON({"method":"VideoLibrary.GetMovies","params":{"properties":["file","year","label"]}}).get('result',{}).get('movies', [])

def getDirectory(path):
    return sendJSON({"method":"Files.GetDirectory","params":{"directory":path,"media":"files"}}).get('result',{}).get('files', [])

def removeEpisode(episodeid):
    return sendJSON({"method":"VideoLibrary.RemoveEpisode","params":{"episodeid":episodeid}}).get('result') == "OK"

def removeMovie(movieid):
    return sendJSON({"method":"VideoLibrary.RemoveMovie","params":{"movieid":movieid}}).get('result') == "OK"

def refreshTVshow(tvshowid, ignorenfo=True, includeEpisodes=True):
    return sendJSON({"method":"VideoLibrary.RefreshTVShow","params":{"tvshowid":tvshowid,"ignorenfo":ignorenfo,"refreshepisodes":includeEpisodes}}).get('result') == "OK"

def refreshMovie(movieid, ignorenfo=True):
    return sendJSON({"method":"VideoLibrary.RefreshMovie","params":{"movieid":movieid,"ignorenfo":ignorenfo}}).get('result') == "OK"


           
