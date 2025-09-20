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

from functools   import wraps
from contextlib  import contextmanager, closing
from collections import defaultdict

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
    
def cacheit(expiration=datetime.timedelta(seconds=REAL_SETTINGS.getSettingInt('Start_Delay')), checksum=ADDON_VERSION, json_data=False):
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

def isScanning():
    return (xbmc.getCondVisibility('Library.IsScanningVideo') or False)

def isPlaying():
    return (xbmc.getCondVisibility('Player.Playing') or False)

def matchItems(items, key='label', matches=defaultdict(list)):
    [matches[item[key]].append(item) for item in items if key in item]
    return [match for match in matches.values() if len(match) > 1]
    
def matchItem(match, items=[], key='file'):
    return [item for item in items if item.get(key) == match]
    
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
             

    def _start(self, wait=REAL_SETTINGS.getSettingInt('Start_Delay')):
        self.log('_start, wait = %s'%(wait))
        self.monitor.waitForAbort(wait)
        while not self.monitor.abortRequested():
            if self.monitor.waitForAbort(wait): break
            elif self.chkPlaying(): pass
            elif not self.running:
                self.running = True
                ## Start ##
                if REAL_SETTINGS.getSettingBool('Scraper_Enabled') and not isScanning():
                    with self._run(self.runScraper,REAL_SETTINGS.getSettingInt('Scraper_Interval')): pass
                ## END ##
                self.running = False
            return wait

    
    @contextmanager
    def _run(self, func, runevery=900, nextrun=None, *args, **kwargs):
        if nextrun is None: nextrun = int(xbmcgui.Window(10000).getProperty(func.__name__) or "0") # nextrun == 0 => force run
        epoch = int(time.time())
        if epoch >= nextrun:
            try: 
                finished = func(*args, **kwargs)
                self.log('_run, func = %s, last run %s, finished = %s' % (func.__name__, epoch - nextrun, finished))
                yield
            finally:
                if finished: xbmcgui.Window(10000).setProperty(func.__name__, str(epoch + runevery))
        else: yield
         

    def chkPlaying(self):
        return isPlaying() and not REAL_SETTINGS.getSettingBool('Run_Playing')


    def sendJSON(self, param):
        command = param
        command["jsonrpc"] = "2.0"
        command["id"] = ADDON_ID
        self.log('sendJSON param [%s]'%(param))
        response = loadJSON(xbmc.executeJSONRPC(dumpJSON(command)))
        if response.get('error'): self.log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
        return response

        
    # @cacheit()
    def getDirectory(self, path):
        return self.sendJSON({"method":"Files.GetDirectory","params":{"directory":path,"media":"files"}}).get('result',{}).get('files', [])


    # @cacheit()
    def getTVshows(self):
        return self.sendJSON({"method":"VideoLibrary.GetTVShows","params":{"properties":["file"]}}).get('result',{}).get('tvshows', [])
           
           
    # @cacheit()
    def getEpisodes(self, tvshowid):
        return self.sendJSON({"method":"VideoLibrary.GetEpisodes","params":{"tvshowid":tvshowid,"properties":["file"]}}).get('result',{}).get('episodes', [])
        
        
    # @cacheit()
    def getMovies(self):
        return self.sendJSON({"method":"VideoLibrary.GetMovies","params":{"properties":["file"]}}).get('result',{}).get('movies', [])


    # @cacheit()
    def getSources(self): #todo verify user TV/Movie path in sources?
        return self.sendJSON({"method":"Files.GetSources","params":{"media":"video"}}).get('result',{}).get('sources', [])


    def runScraper(self):
        try:
            return (self.scanTV(REAL_SETTINGS.getSetting('Scraper_TV_Folder'), self.getTVshows()) & 
            self.scanMovies(REAL_SETTINGS.getSetting('Scraper_Movie_Folder'), self.getMovies()))
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))


    def _cleanEpisodes(self, matches, master=None):
        print('_cleanEpisodes',matches)
        try:
            def __clean(episodes):
                print('__clean',episodes)
                for idx, ep in enumerate(episodes):
                    if xbmcvfs.exists(ep.get('file')):
                        master = episodes.pop(idx)
                        break
                        
                if master is None: return self.log('__clean, all duplicate files do not exist!')#all episodes found don't exist? todo user prompt to remove?
                for episode in episodes:
                    if master.get('label') == episode.get('label') and master.get('episodeid',-1) != episode.get('episodeid'):
                        if not xbmcvfs.exists(episode.get('file')) or master.get('file','-1') == episode.get('file'): #duplicate library entry
                            if self.sendJSON({"method":"VideoLibrary.RemoveEpisode","params":{"episodeid":episode.get('episodeid')}}).get('result') == "OK":
                                self.log('_cleanEpisodes, removed duplicate %s'%(episode.get('file')))
                                if self.monitor.waitForAbort(REAL_SETTINGS.getSettingInt('Start_Delay')): break
                        elif master.get('file','-1') != episode.get('file'): #duplicate file found
                            self.log('__clean, found duplicate physical file [%s] exists [%s]'%(episode.get('file'),xbmcvfs.exists(episode.get('file')))) #todo prompt user to delete? for now cache values
                                
            [__clean(match) for match in matches if len(match) > 1]
            self.log('_cleanEpisodes, finished!')
            return True
        except Exception as e:
            self.log('_cleanEpisodes, failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))


    def scanTV(self, path, shows=[], force=REAL_SETTINGS.getSettingBool('Scraper_Force_TV')):
        paths = dict([(item['file'],item) for item in shows if item.get('file')])
        for item in self.getDirectory(path):
            if self.monitor.waitForAbort(0.1) or self.chkPlaying(): return False
            elif not item.get('file') in paths or force:
                if REAL_SETTINGS.getSettingBool('Duplicate_Enabled'): self._cleanEpisodes(matchItems(self.getEpisodes(paths[item.get('file')].get('tvshowid',-1))))
                self.log('scanTV, [%s] %s'%(item['label'],'Updating Meta...' if force else 'Scraping Meta!'))
                self.scrapeDirectory(item.get('file'))
        return True


    def _cleanMovies(self, movies, master=None):
        print('__clean',movies)
        try:
            for idx, mv in enumerate(movies):
                if xbmcvfs.exists(mv.get('file')):
                    master = movies.pop(idx)
                    break
            if master is None: return self.log('__clean, all duplicate files do not exist!')#all episodes found don't exist? todo user prompt to remove?
            for movie in movies:
                if master.get('label') == movie.get('label') and master.get('movieid',-1) != movie.get('movieid'):
                    if not xbmcvfs.exists(movie.get('file')) or master.get('file','-1') == movie.get('file'):
                        if self.sendJSON({"method":"VideoLibrary.RemoveMovie","params":{"movieid":movie.get('movieid')}}).get('result') == "OK":
                            self.log('_cleanMovies, removed duplicate %s'%(movie.get('file')))
                            if self.monitor.waitForAbort(REAL_SETTINGS.getSettingInt('Start_Delay')): break
                    elif master.get('file','-1') != movie.get('file'): #duplicate file found
                        self.log('__clean, found duplicate physical file [%s] exists [%s]'%(movie.get('file'),xbmcvfs.exists(movie.get('file')))) #todo prompt user to delete? for now cache values
            self.log('_cleanMovies, finished!')
            return True
        except Exception as e:
            self.log('_cleanMovies, failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))


    def scanMovies(self, path, movies=[], force=REAL_SETTINGS.getSettingBool('Scraper_Force_Movies')):
        paths = dict([(os.path.split(item['file'])[0],item) for item in movies if item.get('file')])
        for item in self.getDirectory(path):
            if self.monitor.waitForAbort(0.1) or self.chkPlaying(): return False
            elif not item.get('file') in list(paths.keys()) or force: 
                if REAL_SETTINGS.getSettingBool('Duplicate_Enabled'): self._cleanMovies(matchItem(item.get('file'),movies,'file'))
                self.log('scanMovies, [%s] %s'%(item['label'],'Updating Meta...' if force else 'Scraping Meta!'))
                self.scrapeDirectory(item.get('file'))
        return True


    def scrapeDirectory(self, path, show=REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')):
        self.log('scrapeDirectory, scraping [%s]'%(path))
        if self.sendJSON({"method":"VideoLibrary.Scan","params":{"directory":path,"showdialogs":show}}).get('result') == "OK":
            while not self.monitor.abortRequested():
                if   self.monitor.waitForAbort(REAL_SETTINGS.getSettingInt('Start_Delay')): break
                elif isScanning(): self.log('scrapeDirectory, waiting for scraper to finish...')
                else: break
            self.log('scrapeDirectory, finished!')
            

if __name__ == '__main__': Service()._start()