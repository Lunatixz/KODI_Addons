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


from operator                        import itemgetter
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
ADDON_ID            = 'plugin.program.smartplaylist.generator'
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

def cacheit(expiration=datetime.timedelta(hours=int(REAL_SETTINGS.getSetting('Run_Every')), minutes=15), checksum=ADDON_VERSION, json_data=True):
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
        results = []
        with ThreadPoolExecutor(self.ThreadCount) as executor:
            try: [results.append(result) for result in executor.map(self.wrapped_partial(func, *args, **kwargs), items)]
            except Exception as e: self.log("executors, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)
        return results
        

    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try: return [self.wrapped_partial(func, *args, **kwargs)(i) for i in items]
        except Exception as e: self.log("generator, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR) 