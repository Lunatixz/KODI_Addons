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
import time, traceback, json, os, platform, pathlib, re
import datetime, queue, heapq, random, pickle, sys

try:    from simplecache             import SimpleCache
except: from simplecache.simplecache import SimpleCache #pycharm stub

from contextlib  import contextmanager, closing
from collections import defaultdict
from functools   import partial, wraps, reduce, update_wrapper
from kodi_six    import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from threading   import Lock, Thread, Event, Timer, BoundedSemaphore
from infotagger.listitem import ListItemInfoTag

# Plugin Info
ADDON_ID            = 'service.kodi.powertoys'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE            = REAL_SETTINGS.getLocalizedString

def log(msg, level=xbmc.LOGDEBUG):
    if not REAL_SETTINGS.getSettingBool('Enable_Debugging') and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg = '%s, %s'%(msg,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,str(msg)),level)

def dumpJSON(item, idnt=None, sortkey=False, separators=(',', ':')):
    try:
        if not isinstance(item,str):
            return json.dumps(item, indent=idnt, sort_keys=sortkey, separators=separators)
        elif isinstance(item,str):
            return item
    except Exception as e: log("dumpJSON, failed! %s"%(e), xbmc.LOGERROR)
    return ''
    
def loadJSON(item):
    try:
        if hasattr(item, 'read'):
            return json.load(item)
        elif item and isinstance(item,str):
            return json.loads(item)
        elif item and isinstance(item,dict):
            return item
    except Exception as e: log("loadJSON, failed! %s\n%s"%(e,item), xbmc.LOGERROR)
    return {}
    
def dumpPICKLE(item):
    try:
        if not isinstance(item,str):
            return pickle.dumps(item)
        elif isinstance(item,str):
            return item
    except Exception as e: log("dumpPICKLE, failed! %s"%(e), xbmc.LOGERROR)
    return ''
    
def loadPICKLE(item):
    try:
        if hasattr(item, 'read'):
            return pickle.load(item)
        elif item and isinstance(item,str):
            return pickle.loads(item)
        elif item and isinstance(item,list):
            return item
    except Exception as e: log("loadPICKLE, failed! %s\n%s"%(e,item), xbmc.LOGERROR)
    return []
    
def cacheit(expiration=datetime.timedelta(seconds=REAL_SETTINGS.getSettingInt('Start_Delay')), checksum=ADDON_VERSION, json_data=True):
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

def timerit(method):
    @wraps(method)
    def wrapper(wait, *args, **kwargs):
        thread_name = 'timerit.%s'%(method.__qualname__.replace('.',': '))
        for timer in thread_enumerate():
            if timer.name == thread_name and timer.is_alive():
                if hasattr(timer, 'cancel'): 
                    timer.cancel()
                    log('%s, canceling existing timer %s'%(method.__qualname__.replace('.',': '),thread_name))    
                try: 
                    timer.join()
                    log('%s, joining existing timer %s'%(method.__qualname__.replace('.',': '),thread_name))    
                except: pass
        timer = Timer(float(wait), method, *args, **kwargs)
        timer.name = thread_name
        timer.start()
        log('%s, starting %s wait = %s'%(method.__qualname__.replace('.',': '),thread_name,wait))
        return timer
    return wrapper  

def isScanning():
    return (xbmc.getCondVisibility('Library.IsScanningVideo') or False)

def isPlaying():
    return (xbmc.getCondVisibility('Player.Playing') or False)

def matchItems(items, key='label', matches=defaultdict(list)):
    [matches[item[key]].append(item) for item in items if key in item]
    return [match for match in matches.values() if len(match) > 1]
    
def matchItem(match, items=[], key='file'):
    return [item for item in items if item.get(key) == match] 
    
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
        try:    xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
    return True
         
def sendJSON(param):
    command = param
    command["jsonrpc"] = "2.0"
    command["id"] = ADDON_ID
    log('sendJSON param [%s]'%(param))
    response = loadJSON(xbmc.executeJSONRPC(dumpJSON(command)))
    if response.get('error'): log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
    return response

def getTVshows():
    return sendJSON({"method":"VideoLibrary.GetTVShows","params":{"properties":["file"]}}).get('result',{}).get('tvshows', [])
       
def getEpisodes(tvshowid):
    return sendJSON({"method":"VideoLibrary.GetEpisodes","params":{"tvshowid":tvshowid,"properties":["file"]}}).get('result',{}).get('episodes', [])

def getMovies():
    return sendJSON({"method":"VideoLibrary.GetMovies","params":{"properties":["file"]}}).get('result',{}).get('movies', [])

def getDirectory(path):
    return sendJSON({"method":"Files.GetDirectory","params":{"directory":path,"media":"files"}}).get('result',{}).get('files', [])

def getSources(): #todo verify user TV/Movie path in sources?
    return sendJSON({"method":"Files.GetSources","params":{"media":"video"}}).get('result',{}).get('sources', [])

def removeEpisode(episodeid):
    return sendJSON({"method":"VideoLibrary.RemoveEpisode","params":{"episodeid":episodeid}}).get('result') == "OK"

def removeMovie(movieid):
    return sendJSON({"method":"VideoLibrary.RemoveMovie","params":{"movieid":movieid}}).get('result') == "OK"

def refreshTVshow(tvshowid, ignorenfo=True):
    return sendJSON({"method":"VideoLibrary.RefreshTVShow","params":{"tvshowid":tvshowid,"ignorenfo":ignorenfo,"refreshepisodes":True}}).get('result') == "OK"

def refreshMovie(movieid, ignorenfo=True):
    return sendJSON({"method":"VideoLibrary.RefreshMovie","params":{"movieid":movieid,"ignorenfo":ignorenfo,"refreshepisodes":True}}).get('result') == "OK"

def buildListItem(label="", label2="", icon=ICON, url="", info={}, art={}, props={}, media='video', playable=False, offscreen=False):
    if not art: art = {'thumb':icon,'logo':icon,'icon':icon,'fanart':FANART}
    listitem = xbmcgui.ListItem(label, label2, url, offscreen=offscreen)
    if playable: listitem.setProperty("IsPlayable","true")
    else:        listitem.setIsFolder(True)
    listitem.setArt(art)
    if info:
        infoTag = ListItemInfoTag(listitem, media)
        infoTag.set_info(self.cleanInfo(info,media))
    [listitem.setProperty(key, self.cleanProp(pvalue)) for key, pvalue in list(props.items())]
    return listitem
           
           