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
from globals import *
from cqueue  import CustomQueue

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        
    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))

class Service(object):
    running = False
    monitor = Monitor()
    cache   = SimpleCache()
    cache.enable_mem_cache = False
    
    
    def __init__(self):
        self.tasks = CustomQueue(priority=True, service=self)
       

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
             

    def _que(self, func, priority=-1, *args, **kwargs):# priority -1 autostack, 1 Highest, 5 Lowest
        if priority == -1: priority = self.tasks.qsize + 1
        self.log('_que, priority = %s, func = %s, args = %s, kwargs = %s' % (priority,func.__name__, args, kwargs))
        self.tasks._push((func, args, kwargs), priority)
        
        
    def _start(self, wait=REAL_SETTINGS.getSettingInt('Start_Delay')):
        self.log('_start, wait = %s'%(wait))
        self.monitor.waitForAbort(wait)
        while not self.monitor.abortRequested():
            if    self.monitor.waitForAbort(wait): break
            else: self._run()

               
    def _run(self):
        if not self.running:
            self.log('_run, starting')
            self.running = True
            if REAL_SETTINGS.getSettingBool('Scraper_Enabled') and not isScanning():
                with self._chkUpdate(self.runScraper,(REAL_SETTINGS.getSettingInt('Scraper_Interval_HRS')*3600)): pass
            self.running = False
            self.log('_run, stopping')
        
        
    @contextmanager
    def _chkUpdate(self, func, runevery=900, nextrun=None, *args, **kwargs):
        if nextrun is None: nextrun = int(xbmcgui.Window(10000).getProperty(func.__name__) or "0") # nextrun == 0 => force run
        epoch = int(time.time())
        if epoch >= nextrun:
            try: 
                finished = func(*args, **kwargs)
                yield self.log('_chkUpdate, func = %s, last run %s, finished = %s' % (func.__name__, epoch - nextrun, finished))
            except: finished = False
            finally:
                if finished: xbmcgui.Window(10000).setProperty(func.__name__, str(epoch + runevery))
        else: yield
         

    def _chkPlaying(self):
        return isPlaying() and not REAL_SETTINGS.getSettingBool('Run_Playing')
        
        
    def sendJSON(self, param):
        command = param
        command["jsonrpc"] = "2.0"
        command["id"] = ADDON_ID
        self.log('sendJSON param [%s]'%(param))
        response = loadJSON(xbmc.executeJSONRPC(dumpJSON(command)))
        if response.get('error'): self.log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
        return response


    def getTVshows(self):
        return self.sendJSON({"method":"VideoLibrary.GetTVShows","params":{"properties":["file"]}}).get('result',{}).get('tvshows', [])
           
           
    def getEpisodes(self, tvshowid):
        return self.sendJSON({"method":"VideoLibrary.GetEpisodes","params":{"tvshowid":tvshowid,"properties":["file"]}}).get('result',{}).get('episodes', [])
        
        
    def getMovies(self):
        return self.sendJSON({"method":"VideoLibrary.GetMovies","params":{"properties":["file"]}}).get('result',{}).get('movies', [])


    def getDirectory(self, path):
        return self.sendJSON({"method":"Files.GetDirectory","params":{"directory":path,"media":"files"}}).get('result',{}).get('files', [])


    def getSources(self): #todo verify user TV/Movie path in sources?
        return self.sendJSON({"method":"Files.GetSources","params":{"media":"video"}}).get('result',{}).get('sources', [])


    def remEpisode(self, episodeid):
        return self.sendJSON({"method":"VideoLibrary.RemoveEpisode","params":{"episodeid":episodeid}}).get('result') == "OK"


    def remMovie(self, movieid):
        return self.sendJSON({"method":"VideoLibrary.RemoveMovie","params":{"movieid":movieid}}).get('result') == "OK"


    def runScraper(self):
        try:
            return (self.scanTV(REAL_SETTINGS.getSetting('Scraper_TV_Folder'), self.getTVshows()) & 
            self.scanMovies(REAL_SETTINGS.getSetting('Scraper_Movie_Folder'), self.getMovies()))
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))


    def cleanTV(self, matches, master=None):
        try:
            def __clean(episodes):
                for idx, ep in enumerate(episodes):
                    if xbmcvfs.exists(ep.get('file')):
                        master = episodes.pop(idx)
                        break
                        
                if master is None: return self.log('__clean, duplicate files do not exist!') #all episodes found don't exist? todo user prompt to remove? check source?
                for episode in episodes:
                    if master.get('label') == episode.get('label') and master.get('episodeid',-1) != episode.get('episodeid'):
                        if not xbmcvfs.exists(episode.get('file')) or master.get('file','-1') == episode.get('file'): #duplicate library entry
                            self.log('cleanTV, Queuing removed duplicate %s'%(episode.get('file')))
                            self.remEpisode(episode.get('episodeid'))
                        elif master.get('file','-1') != episode.get('file'): #duplicate file found
                            self.log('__clean, found duplicate physical file [%s] exists [%s]'%(episode.get('file'),xbmcvfs.exists(episode.get('file')))) #todo prompt user to delete? for now cache values
                                
            [__clean(match) for match in matches if len(match) > 1]
            self.log('cleanTV, finished!')
            return True
        except Exception as e:
            self.log('cleanTV, failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))


    def scanTV(self, path, shows=[], force=REAL_SETTINGS.getSettingBool('Scraper_Force_TV')):
        paths = dict([(item['file'],item) for item in shows if item.get('file')])
        items = self.getDirectory(path)
        random.shuffle(items)
        for item in items:
            if self.monitor.waitForAbort(0.1): return False
            elif not item.get('file') in paths or force:
                if REAL_SETTINGS.getSettingBool('Duplicate_Enabled'): self._que(self.cleanTV, 1, matchItems(self.getEpisodes(paths[item.get('file')].get('tvshowid',-1))))
                self.log('scanTV, [%s] %s'%(item['label'],'Queuing Meta Update'))
                self._que(self.scrapeDirectory, 2, item.get('file'))
        return True


    def cleanMovies(self, movies, master=None):
        try:
            for idx, mv in enumerate(movies):
                if xbmcvfs.exists(mv.get('file')):
                    master = movies.pop(idx)
                    break
            if master is None: return self.log('__clean, duplicate files do not exist!')#all episodes found don't exist? todo user prompt to remove?
            for movie in movies:
                if master.get('label') == movie.get('label') and master.get('movieid',-1) != movie.get('movieid'):
                    if not xbmcvfs.exists(movie.get('file')) or master.get('file','-1') == movie.get('file'):
                        self.log('cleanMovies, Queuing removed duplicate %s'%(movie.get('file')))
                        self.remMovie(movie.get('movieid'))
                    elif master.get('file','-1') != movie.get('file'): #duplicate file found
                        self.log('__clean, found duplicate physical file [%s] exists [%s]'%(movie.get('file'),xbmcvfs.exists(movie.get('file')))) #todo prompt user to delete? for now cache values
            self.log('cleanMovies, finished!')
            return True
        except Exception as e:
            self.log('cleanMovies, failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))


    def scanMovies(self, path, movies=[], force=REAL_SETTINGS.getSettingBool('Scraper_Force_Movies')):
        paths = dict([(os.path.split(item['file'])[0],item) for item in movies if item.get('file')])
        items = self.getDirectory(path)
        random.shuffle(items)
        for item in items:
            if self.monitor.waitForAbort(0.1): return False
            elif not item.get('file') in list(paths.keys()) or force: 
                if REAL_SETTINGS.getSettingBool('Duplicate_Enabled'): self._que(self.cleanMovies, 1, (matchItem(item.get('file'),movies,'file')))
                self.log('scanMovies, [%s] %s'%(item['label'],'Queuing Meta Update'))
                self._que(self.scrapeDirectory, 2, item.get('file'))
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