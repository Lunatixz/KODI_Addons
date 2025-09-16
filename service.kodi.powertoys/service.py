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
import time, traceback, json, os, platform, pathlib, re, datetime
from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs

try:    from simplecache             import SimpleCache
except: from simplecache.simplecache import SimpleCache #pycharm stub
        
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
    
def cacheit(expiration=datetime.timedelta(minutes=15), checksum=ADDON_VERSION, json_data=False):
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
    
def chkUpdate(key, runevery=900, nextrun=None):
    if nextrun is None: nextrun = int(xbmcgui.Window(10000).getProperty(key) or "0") # nextrun == 0 => force que
    epoch = int(time.time())
    if epoch >= nextrun:
        self.log('chkUpdate, key = %s, last run %s' % (key, epoch - nextrun))
        xbmcgui.Window(10000).setProperty(key, str(epoch + runevery))
        return True

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)

class Service(object):
    running = False
    monitor = Monitor()
    cache   = SimpleCache()
 
 
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def notification(self, message, header=ADDON_NAME, sound=False, time=4000, icon=ICON, show=None):
        self.log('notificationDialog: %s, show = %s'%(message,show))
        ## - Builtin Icons:
        ## - xbmcgui.NOTIFICATION_INFO
        ## - xbmcgui.NOTIFICATION_WARNING
        ## - xbmcgui.NOTIFICATION_ERROR
        if show:
            try:    xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
            except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
             

    def _start(self):
        self.log('_start')
        self.monitor.waitForAbort(REAL_SETTINGS.getSettingInt('Start_Delay_Seconds'))
        while not self.monitor.abortRequested():
            if self.monitor.waitForAbort(self._run()): break
            
            
    def _run(self):
        if not self.running:
            if not self.isScanning():
                self.log('_run, started')
                self.running = True
                try:
                    self.scanTV(REAL_SETTINGS.getSetting('TV_Source_Folder'), self.getTVshows())
                    self.scanMovies(REAL_SETTINGS.getSetting('Movie_Source_Folder'), self.getMovies())
                except Exception as e:
                    self.log('_run, Scan failed! %s'%(e), xbmc.LOGERROR)
                    self.notification(LANGUAGE(32009))
                self.running = False
                self.log('_run, ended')
            else: return REAL_SETTINGS.getSettingInt('Start_Delay_Seconds')
        return REAL_SETTINGS.getSettingInt('Run_Interval_Seconds')


    def scanTV(self, path, shows=[], force=REAL_SETTINGS.getSettingBool('Force_Scrape_TV')):
        paths = [item['file'] for item in shows if item.get('file')]
        for item in self.getDirectory(path):
            if self.monitor.waitForAbort(0.1): break
            elif not item.get('file') in paths  or force:
                self.log('scanTV, [%s] missing from library!'%(item['label']))
                self.scrapeDirectory(item.get('file'))


    def scanMovies(self, path, movies=[], force=REAL_SETTINGS.getSettingBool('Force_Scrape_Movies')):
        paths = [os.path.split(item['file'])[0] for item in movies if item.get('file')]
        for item in self.getDirectory(path):
            if self.monitor.waitForAbort(0.1): break
            elif not item.get('file') in paths or force:
                self.log('scanMovies, [%s] missing from library!'%(item['label']))
                self.scrapeDirectory(item.get('file'))


    def isScanning(self):
        return (xbmc.getCondVisibility('Library.IsScanningVideo') or False)

      
    def sendJSON(self, param):
        command = param
        command["jsonrpc"] = "2.0"
        command["id"] = ADDON_ID
        self.log('sendJSON param [%s]'%(param))
        response = loadJSON(xbmc.executeJSONRPC(dumpJSON(command)))
        if response.get('error'): self.log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
        return response


    def scrapeDirectory(self, path, show=REAL_SETTINGS.getSettingBool('Show_Dialog')):
        self.log('scrapeDirectory, scraping [%s]'%(path))
        if self.sendJSON({"method":"VideoLibrary.Scan","params":{"directory":path,"showdialogs":show}}).get('result') == "OK":
            while not self.monitor.abortRequested():
                if self.monitor.waitForAbort(REAL_SETTINGS.getSettingInt('Start_Delay_Seconds')): break
                elif self.isScanning(): self.log('scrapeDirectory, waiting for scraper to finish...')
                else: break
            self.log('scrapeDirectory, finished!')
        
 
    # @cacheit()
    def getDirectory(self, path):
        return self.sendJSON({"method":"Files.GetDirectory","params":{"directory":path,"media":"files"}}).get('result',{}).get('files', [])


    # @cacheit()
    def getTVshows(self):
        return self.sendJSON({"method":"VideoLibrary.GetTVShows","params":{"properties":["file"]}}).get('result',{}).get('tvshows', [])
           
           
    # @cacheit()
    def getMovies(self):
        return self.sendJSON({"method":"VideoLibrary.GetMovies","params":{"properties":["file"]}}).get('result',{}).get('movies', [])


    def getSources(self): #todo user drop down list with multi select source paths to check.
        return self.sendJSON({"method":"Files.GetSources","params":{"media":"video"}}).get('result',{}).get('sources', [])


if __name__ == '__main__': Service()._start()