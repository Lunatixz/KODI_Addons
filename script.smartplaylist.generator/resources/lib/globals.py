#   Copyright (C) 2024 Lunatixz
#
#
# This file is part of Smartplaylist Generator.
#
# Smartplaylist Generator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smartplaylist Generator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-

import os, sys, re
import requests
import json, random, traceback
import uuid, zlib, base64
import time, datetime
import xml.etree.ElementTree as ET


from functools                       import wraps
from contextlib                      import contextmanager, closing
from infotagger.listitem             import ListItemInfoTag
from kodi_six                        import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from concurrent.futures              import ThreadPoolExecutor, TimeoutError
from itertools                       import repeat, count
from functools                       import partial, wraps, reduce, update_wrapper

try:    from simplecache             import SimpleCache
except: from simplecache.simplecache import SimpleCache #pycharm stub

#info
ADDON_ID            = 'script.smartplaylist.generator'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
DUMMY_ICON          = 'https://dummyimage.com/512x512/%s/%s.png&text={text}'%('01416b','ffffff')
LANGUAGE            = REAL_SETTINGS.getLocalizedString

#api
MONITOR             = xbmc.Monitor
PLAYER              = xbmc.Player

SELECT_DELAY        = 900  #secs
AUTOCLOSE_DELAY     = 300  #secs
PROMPT_DELAY        = 4000 #msecs
DTFORMAT            = '%Y-%m-%d %I:%M %p'

def log(event, level=xbmc.LOGDEBUG):
    if REAL_SETTINGS.getSetting('Debug_Enable') == 'true' or level >= 3:
        if level >= 3: event = '%s\n%s'%(event, traceback.format_exc())
        event = '%s-%s-%s'%(ADDON_ID, ADDON_VERSION, event)
        xbmc.log(event,level)
        
def poolit(method):
    @wraps(method)
    def wrapper(items=[], *args, **kwargs):
        try:
            pool = ThreadPool()
            name = '%s.%s'%('poolit',method.__qualname__.replace('.',': '))
            log('%s, starting %s'%(method.__qualname__.replace('.',': '),name))
            results = pool.executors(method, items, *args, **kwargs)
        except Exception as e:
            log('poolit, failed! %s'%(e), xbmc.LOGERROR)
            results = pool.generator(method, items, *args, **kwargs)
        log('%s poolit => %s'%(pool.__class__.__name__, method.__qualname__.replace('.',': ')))
        return list([_f for _f in results if _f])
    return wrapper

def cacheit(expiration=datetime.timedelta(hours=12), checksum=ADDON_VERSION, json_data=True):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            method_class = args[0]
            cacheName = "%s.%s"%(method_class.__class__.__name__, method.__name__)
            for item in args[1:]: cacheName += u".%s"%item
            for k, v in list(kwargs.items()): cacheName += u".%s"%(v)
            results = method_class.cache.get(cacheName.lower(), checksum, json_data)
            if results: return results
            value = method(*args, **kwargs)
            method_class.cache.set(cacheName.lower(), value, checksum, expiration, json_data)
            return value
        return wrapper
    return internal

def encodeString(text):
    base64_bytes = base64.b64encode(zlib.compress(text.encode(DEFAULT_ENCODING)))
    return base64_bytes.decode(DEFAULT_ENCODING)

def decodeString(base64_bytes):
    try:
        message_bytes = zlib.decompress(base64.b64decode(base64_bytes.encode(DEFAULT_ENCODING)))
        return message_bytes.decode(DEFAULT_ENCODING)
    except Exception as e: return ''

def validString(s):
    return "".join(x for x in s if (x.isalnum() or x not in '\/:*?"<>|')).rstrip()
   
def strpTime(datestring, format=DTFORMAT):
    try:              return datetime.datetime.strptime(datestring, format)
    except TypeError: return datetime.datetime.fromtimestamp(time.mktime(time.strptime(datestring, format)))
    except:           return datetime.datetime.now()
           
class ThreadPool:
    CPUCount    = 4
    ThreadCount = CPUCount*8
    
    def __init__(self):
        self.log("__init__, ThreadPool Threads = %s, CPU's = %s"%(self.ThreadCount, self.CPUCount))


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def wrapped_partial(self, func, *args, **kwargs):
        partial_func = partial(func, *args, **kwargs)
        update_wrapper(partial_func, func)
        return partial_func
        

    def executor(self, func, timeout=None, *args, **kwargs):
        self.log("executor, func = %s, timeout = %s"%(func.__name__,timeout))
        with ThreadPoolExecutor(self.ThreadCount) as executor:
            try: return executor.submit(func, *args, **kwargs).result(timeout)
            except Exception as e: self.log("executor, func = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,e,args,kwargs), xbmc.LOGERROR)


    def executors(self, func, items=[], *args, **kwargs):
        self.log("executors, func = %s, items = %s"%(func.__name__,len(items)))
        with ThreadPoolExecutor(self.ThreadCount) as executor:
            try: return executor.map(self.wrapped_partial(func, *args, **kwargs), items)
            except Exception as e: self.log("executors, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)


    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try: return [self.wrapped_partial(func, *args, **kwargs)(i) for i in items]
        except Exception as e: self.log("generator, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR) 


class Kodi:
    def __init__(self, cache=None):
        if cache is None: self.cache = SimpleCache()
        else:
            self.cache = cache
            self.cache.enable_mem_cache = False


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getEXTProperty(self, key):
        return xbmcgui.Window(10000).getProperty(key)
        
        
    def getEXTPropertyBool(self, key):
        return (self.getEXTProperty(key) or '').lower() == "true"
        
        
    def setEXTProperty(self, key, value):
        xbmcgui.Window(10000).setProperty(key,str(value))
        return value
        
        
    def setEXTPropertyBool(self, key, value):
        return self.setEXTProperty(key,str(value).lower()) == 'true'
        
        
    def isRunning(self, key):
        return self.getEXTPropertyBool('%s.Running.%s'%(ADDON_ID,key))


    @contextmanager
    def setRunning(self, key):
        if not self.isRunning(key):
            self.setEXTPropertyBool('%s.Running.%s'%(ADDON_ID,key),True)
            try: yield
            finally: self.setEXTPropertyBool('%s.Running.%s'%(ADDON_ID,key),False)
        else: yield


    def setCacheSetting(self, key, value, checksum=1, life=datetime.timedelta(days=84), json_data=False):
        self.log('setCacheSetting, key = %s, value = %s'%(key, value))
        self.cache.set(key, value, checksum, life, json_data)
        return value
            
            
    def getCacheSetting(self, key, checksum=1, json_data=False, revive=True, default=[]):
        if revive: value = self.setCacheSetting(key, self.cache.get(key, checksum, json_data), checksum, json_data=json_data)
        else:      value = self.cache.get(key, checksum, json_data)
        self.log('getCacheSetting, key = %s, value = %s'%(key, value))
        return (value or default)
        
        
    def getInfoBool(self, key, param='Library', default=False):
        value = (xbmc.getCondVisibility('%s.%s'%(param,key)) or default)
        self.log('getInfoBool, key = %s.%s, value = %s'%(param,key,value))
        return value
        
        
    def executebuiltin(self, key, wait=False):
        self.log('executebuiltin, key = %s, wait = %s'%(key,wait))
        xbmc.executebuiltin('%s'%(key),wait)
        return True
        
    @contextmanager
    def busy_dialog(self):
        if not self.isBusyDialog() and not self.getInfoBool('Playing','Player'):
            self.executebuiltin('ActivateWindow(busydialognocancel)')
            try:
                if self.getInfoBool('Playing','Player'):
                    self.executebuiltin('Dialog.Close(busydialognocancel)')
                yield
            finally:
                self.executebuiltin('Dialog.Close(busydialognocancel)')
        else: yield
       

    def isBusyDialog(self):
        return (self.getInfoBool('IsActive(busydialognocancel)','Window') | self.getInfoBool('IsActive(busydialog)','Window'))


    def closeBusyDialog(self):
        if self.getInfoBool('IsActive(busydialognocancel)','Window'):
            self.executebuiltin('Dialog.Close(busydialognocancel)')
        elif self.getInfoBool('IsActive(busydialog)','Window'):
            self.executebuiltin('Dialog.Close(busydialog)')
        

    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=PROMPT_DELAY, icon=ICON):
        self.log('notificationDialog: %s'%(message))
        ## - Builtin Icons:
        ## - xbmcgui.NOTIFICATION_INFO
        ## - xbmcgui.NOTIFICATION_WARNING
        ## - xbmcgui.NOTIFICATION_ERROR
        try:    xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except: self.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
             

    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME, silent=None):
        # if silent is None and self.settings.getSettingBool('Silent_OnPlayback'): 
            # silent = (self.properties.getPropertyBool('OVERLAY') | self.builtin.getInfoBool('Playing','Player'))
        
        # if silent:
            # if hasattr(control, 'close'): control.close()
            # self.log('progressBGDialog, silent = %s; closing dialog'%(silent))
            # return 
            
        if control is None and int(percent) == 0:
            control = xbmcgui.DialogProgressBG()
            control.create(header, message)
        elif control:
            if int(percent) == 100 or control.isFinished(): 
                if hasattr(control, 'close'):
                    control.close()
                    return None
            elif hasattr(control, 'update'):  control.update(int(percent), header, message)
        return control
        
        
    def yesnoDialog(self, message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=AUTOCLOSE_DELAY): 
        if customlabel:
            # Returns the integer value for the selected button (-1:cancelled, 0:no, 1:yes, 2:custom)
            return xbmcgui.Dialog().yesnocustom(heading, message, customlabel, nolabel, yeslabel, (autoclose*1000))
        else: 
            # Returns True if 'Yes' was pressed, else False.
            return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, (autoclose*1000))


    def selectDialog(self, items, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=SELECT_DELAY, multi=True):
        self.log('selectDialog, items = %s, header = %s, preselect = %s, useDetails = %s, autoclose = %s, multi = %s'%(len(items),header,preselect,useDetails,autoclose,multi))
        if multi == True:
            if not preselect: preselect = [-1]
            select = xbmcgui.Dialog().multiselect(header, items, (autoclose*1000), preselect, useDetails)
            if select == [-1]: return
        else:
            if not preselect: preselect = -1
            elif isinstance(preselect,list) and len(preselect) > 0: preselect = preselect[0]
            select = xbmcgui.Dialog().select(header, items, (autoclose*1000), preselect, useDetails)
            if select == -1: return
        return select
            
            
    def getListItem(self, label='', label2='', path='', offscreen=False):
        return xbmcgui.ListItem(label,label2,path,offscreen)


    def infoTagVideo(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)
              
                      
    def findItemsInLST(self, items, values, item_key='getLabel', val_key='', index=True):
        if not values: return [-1]
        if not isinstance(values,list): values = [values]
        matches = []
        def _match(fkey,fvalue):
            if str(fkey).lower() == str(fvalue).lower():
                matches.append(idx if index else item)
                        
        for value in values:
            if isinstance(value,dict): 
                value = value.get(val_key,'')
                
            for idx, item in enumerate(items): 
                if isinstance(item,xbmcgui.ListItem): 
                    if item_key == 'getLabel':  
                        _match(item.getLabel() ,value)
                    elif item_key == 'getLabel2': 
                        _match(item.getLabel2(),value)
                    elif item_key == 'getPath': 
                        _match(item.getPath(),value)
                elif isinstance(item,dict):       
                    _match(item.get(item_key,''),value)
                else: _match(item,value)
        return matches
     
     
    def buildMenuListItem(self, label="", label2="", icon=ICON, url="", info={}, art={}, props={}, oscreen=False, media='video'):
        if not art: art = {'thumb':icon,'logo':icon,'icon':icon}
        listitem = self.getListItem(label, label2, url, offscreen=oscreen)
        listitem.setIsFolder(True)
        listitem.setArt(art)
        if info:
            infoTag = ListItemInfoTag(listitem, media)
            infoTag.set_info(self.cleanInfo(info,media))
        [listitem.setProperty(key, self.cleanProp(pvalue)) for key, pvalue in list(props.items())]
        return listitem
           
                   
    def cleanInfo(self, ninfo, media='video', properties={}):
        LISTITEM_TYPES = MUSIC_LISTITEM_TYPES if media == 'music' else VIDEO_LISTITEM_TYPES  
        tmpInfo = ninfo.copy()
        for key, value in list(tmpInfo.items()):
            types = LISTITEM_TYPES.get(key,None)
            if not types:# key not in json enum schema, add to customproperties
                ninfo.pop(key)
                properties[key] = value
                continue
                
            elif not isinstance(value,types):# convert to schema type
                for type in types:
                    try:   ninfo[key] = type(value)
                    except Exception as e: self.log("cleanInfo failed! %s\nkey = %s, value = %s, type = %s\n%s"%(e,key,value,type,ninfo), xbmc.LOGWARNING)
                     
            if isinstance(ninfo[key],list):
                for n in ninfo[key]:
                    if isinstance(n,dict): n, properties = self.cleanInfo(n,media,properties)
            if isinstance(ninfo[key],dict): ninfo[key], properties = self.cleanInfo(ninfo[key],media,properties)
        return ninfo, properties


    def cleanProp(self, pvalue):
        if       isinstance(pvalue,dict): return dumpJSON(pvalue)
        elif     isinstance(pvalue,list): return '|'.join(map(str, pvalue))
        elif not isinstance(pvalue,str):  return str(pvalue)
        else:                             return pvalue
            
    
    @cacheit()
    def get_kodi_movies(self):
        return json.loads(xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","id":"test","method":"VideoLibrary.GetMovies","params":{"properties":["title","genre","year","tagline","playcount","studio","file","thumbnail","uniqueid","imdbnumber","runtime","mpaa"]}}))).get('result', {}).get('movies', [])


    @cacheit()
    def get_kodi_shows(self):
        return json.loads(xbmc.executeJSONRPC(json.dumps({"jsonrpc": "2.0", "id": "test", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "genre", "year", "season", "episode", "playcount", "studio", "file", "thumbnail","uniqueid", "imdbnumber", "runtime", "mpaa"]}}))).get('result', {}).get('tvshows', [])


    @cacheit()
    def get_kodi_episodes(self):
        return json.loads(xbmc.executeJSONRPC(json.dumps({"jsonrpc": "2.0", "id": "test", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["title", "genre", "firstaired", "season", "episode", "showtitle", "studio", "file", "thumbnail","uniqueid", "tvshowid", "runtime", "rating"]}}))).get('result', {}).get('episodes', [])

