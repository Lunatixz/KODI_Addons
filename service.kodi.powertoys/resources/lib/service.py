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
from globals     import *
from cqueue      import CustomQueue

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set): return list(obj)
        return json.JSONEncoder.default(self, obj)

class Player(xbmc.Player):
    def __init__(self, monitor=None):
        xbmc.Player.__init__(self)
        self.monitor = monitor
        self.service = monitor.service
        self.playingItem = {'listitem':xbmcgui.ListItem()}
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def isPseudoTV(self):
        return '@%s'%(slugify(ADDON_NAME)) in loadJSON(decodeString(self.getPlayerItem().getProperty('sysInfo'))).get('chid','')
        

    def assertPlaying(self):
        if self.isPlaying() and not self.isPseudoTV(): return True
        return False
        

    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        

    def onAVStarted(self):
        self.playingItem = {'listitem':self.getPlayerItem(), 'elapsed':self.getPlayedTime(), 'totaltime':self.getPlayerTime()}
        self.log('onAVStarted, playingItem = %s'%(self.playingItem))
        

    def onPlayBackError(self):
        self.log('onPlayBackError')
        self.playingItem = self.onStop(self.playingItem)
        
        
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        self.playingItem = self.onStop(self.playingItem)
        
        
    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        self.playingItem = self.onStop(self.playingItem)
        

    def onStop(self, playingItem={}):
        self.log('onStop, playingItem = %s'%(self.playingItem))
        '''
        TODO RUN ACTION FUNC HERE
        '''
        return {'listitem':xbmcgui.ListItem()}
        

    def getPlayerItem(self):
        try: return self.getPlayingItem()
        except:
            if self.isPlaying(): return self.getPlayerItem()
            else:                return xbmcgui.ListItem()


    def getPlayerFile(self):
        try:    return self.getPlayingFile()
        except: return self.pendingItem['listitem'].getPath()


    def getPlayerTime(self):
        try:    return (self.getTimeLabel('Duration') or self.getTotalTime())
        except: return (self.getPlayerItem().getProperty('runtime') or -1)
            
       
    def getPlayedTime(self):
        try:    return (self.getTimeLabel('Time') or self.getTime())
        except: return -1
       
            
    def getRemainingTime(self):
        try:    return self.getPlayerTime() - self.getPlayedTime()
        except: return (self.getTimeLabel('TimeRemaining') or -1)


    def getPlayerProgress(self):
        try:    return abs(int((self.getRemainingTime() / self.getPlayerTime()) * 100) - 100)
        except: return int((BUILTIN.getInfoLabel('Progress','Player') or '-1'))


    def getTimeLabel(self, prop: str='TimeRemaining') -> int and float: #prop='EpgEventElapsedTime'
        if self.isPlaying(): return timeString2Seconds(BUILTIN.getInfoLabel('%s(hh:mm:ss)'%(prop),'Player'))

class Monitor(xbmc.Monitor):
    def __init__(self, service=None):
        xbmc.Monitor.__init__(self)
        self.service = service
        self.player  = Player(self)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))

class Service(object):
    running = False
    cache   = SimpleCache()
    cache.enable_mem_cache = True
    
    def __init__(self):
        self.monitor  = Monitor(self)
        self.player   = self.monitor.player
        self.priority = CustomQueue(priority=True, service=self)
        self.tasks    = (self.cache.get('tasks', checksum=ADDON_VERSION, json_data=True) or dict())
        self.log('__init__ tasks = %s'%(dict([(key,len(value)) for key, value in list(self.tasks.items())])))
    
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def _que(self, func, priority=-1, *args, **kwargs):# priority -1 autostack, 1 Highest, 5 Lowest
        if priority == -1: priority = self.priority.qsize + 1
        self.log('_que, priority = %s, func = %s, args = %s, kwargs = %s' % (priority,func.__name__, args, kwargs))
        self.priority._push((func, args, kwargs), priority)

        
    def _start(self, wait=REAL_SETTINGS.getSettingInt('Start_Delay')):
        self.log('_start, wait = %s'%(wait))
        self.monitor.waitForAbort(wait)
        while not self.monitor.abortRequested():
            if    self.monitor.waitForAbort(2.0): break
            else: self._run()
        self._exit()
        
               
    def _run(self):
        if   self._chkPlaying() or isScanning():self.log('_run, waiting for scraper or player to finish...')
        elif self.tasks.get('scrapeDirectory'): self._que(self.scrapeDirectory, -1, self.tasks.get('scrapeDirectory').pop())
        elif self.tasks.get('cleanTV'):         self._que(self.cleanTV        , -1, findDupes((self.getEpisodes(self.tasks.get('cleanTV').pop()) or [])))
        elif self.tasks.get('refreshTVshow'):   self._que(refreshTVshow       , -1,*self.tasks.get('refreshTVshow').pop())
        elif self.tasks.get('cleanMovies'):     self._que(self.cleanMovies    , -1, self.tasks.get('cleanMovies').pop(0))
        elif self.tasks.get('refreshMovie'):    self._que(refreshMovie        , -1,*self.tasks.get('refreshMovie').pop())
        elif not self.running:
            self.running = True
            if REAL_SETTINGS.getSettingBool('Scraper_Enabled'):
                with self._chkUpdate(self.runScraper,(REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')*86400)): pass
            if REAL_SETTINGS.getSettingBool('Refresh_Enabled'):
                with self._chkUpdate(self.runRefresh,(REAL_SETTINGS.getSettingInt('Refresh_Interval_DAYS')*86400),None,
                                                      REAL_SETTINGS.getSettingBool('Refresh_Clean'),
                                                      REAL_SETTINGS.getSettingBool('Refresh_Ignore_NFO'),
                                                      REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')): pass
            self.running = False


    def _menu(self, sysARG):
        self.log('_menu')
        try:    param = sysARG[1]
        except: param = None
        
        if param is None: return
        
        # listItems = [buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in sorted(items,key=itemgetter('label'))]
        # if select is None: select = DIALOG.selectDialog(listItems, '%s - %s'%(ADDON_NAME,LANGUAGE(32126)),multi=False)
            
        # if not select is None:
            # try: 
                # selectItem = [item for item in items if item.get('label') == listItems[select].getLabel()][0]
                # self.log('buildMenu, selectItem = %s'%selectItem)
                # if selectItem.get('args'): selectItem['func'](*selectItem['args'])
                # else:                      selectItem['func']()
            # except Exception as e: 
                # self.log("buildMenu, failed! %s"%(e), xbmc.LOGERROR)
                # return DIALOG.notificationDialog(LANGUAGE(32000))
         
                
    def _exit(self):
        self.log('_exit tasks = %s'%(dict([(key,len(value)) for key, value in list(self.tasks.items())])))
        self.cache.set('tasks', json.dumps(self.tasks, cls=SetEncoder), checksum=ADDON_VERSION, expiration=datetime.timedelta(days=28), json_data=True)


    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getDirectory(self, param):
        return (getDirectory(param) or [])
        
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getTVshows(self):
        return (getTVshows() or [])
    
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getMovies(self):
        return (getMovies() or [])
    
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getEpisodes(self, param):
        return (getEpisodes(param) or [])
        

    @contextmanager
    def _chkUpdate(self, func, runevery=900, nextrun=None, *args, **kwargs):
        nxrun = (nextrun or self.cache.get(func.__name__) or 0) # nextrun == 0 => force run
        epoch = int(time.time())
        if epoch >= nxrun:
            try: 
                finished = func(*args, **kwargs)
                yield self.log('_chkUpdate, func = %s, last run %s, finished = %s' % (func.__name__, epoch - nxrun, finished))
            except: finished = False
            finally:
                if finished: 
                    self.cache.set(func.__name__, (epoch + runevery),expiration=datetime.timedelta(days=28))
        else: yield
         

    def _chkPlaying(self):
        return isPlaying() and not REAL_SETTINGS.getSettingBool('Run_Playing')
        
        
    def _chkIdle(self):
        if REAL_SETTINGS.getSettingBool('Run_Idling'): return int(xbmc.getGlobalIdleTime() or '0') > 30
        return False
        
        
    def runScraper(self):
        try:
            return (self.scrapeTV(REAL_SETTINGS.getSetting('Scraper_TV_Folder'), (self.getTVshows() or []),REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')) & 
                    self.scrapeMovies(REAL_SETTINGS.getSetting('Scraper_Movie_Folder'), (self.getMovies() or [])))
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))


    def runRefresh(self, clean=False, ignoreNFO=True, includeEpisodes=True):
        try:
            return (self.refreshTV((self.getTVshows() or []),clean,ignoreNFO,includeEpisodes) & 
                    self.refreshMovies((self.getMovies() or []),clean,ignoreNFO))
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
        

    def runDuplicate(self):
        try: return (self.cleanTV() & self.cleanMovies())
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
            
            
    def scrapeDirectory(self, path, show=REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')):
        self.log('scrapeDirectory, scraping [%s]'%(path))
        if sendJSON({"method":"VideoLibrary.Scan","params":{"directory":path,"showdialogs":show}}).get('result') == "OK":
            while not self.monitor.abortRequested():
                if self.monitor.waitForAbort(REAL_SETTINGS.getSettingInt('Start_Delay')): break
                elif isScanning(): self.log('scrapeDirectory, waiting for scraper to finish...')
                else: break
            self.log('scrapeDirectory, finished!')
            
            
    def cleanTV(self, matches, master=None):
        try:
            def __clean(duplicates):
                for episode in duplicates:
                    if xbmcvfs.exists(episode.get('file')):
                        master = duplicates.pop(episode)
                        break
                        
                if master is None: 
                    return self.log('cleanTV, duplicate files do not exist!') #all episodes found don't exist? todo user prompt to remove? check source?
                else:
                    for episode in duplicates:
                        if   self.monitor.waitForAbort(0.1): return False
                        elif master.get('label') == episode.get('label'):
                            #missing file
                            if not xbmcvfs.exists(episode.get('file')):
                                self.log('cleanTV, removing entry, missing file %s'%(episode.get('file')))
                                removeEpisode(episode.get('episodeid'))
                            #shadow duplicate entry
                            elif (master.get('file','-1') == episode.get('file') and master.get('episodeid',-1) != episode.get('episodeid')):
                                self.log('cleanTV, removing shadow duplicate %s'%(episode.get('file')))
                                removeEpisode(episode.get('episodeid'))
                            #duplicate file found
                            elif master.get('file','-1') != episode.get('file'):
                                self.log('cleanTV, removing duplicate physical file [%s] exists [%s]'%(episode.get('file'),xbmcvfs.exists(episode.get('file'))))
                                removeEpisode(episode.get('episodeid')) #todo prompt user to delete file?
                                
            [__clean(match) for match in matches if len(match) > 1]
            self.log('cleanTV, finished!')
            return True
        except Exception as e:
            self.log('cleanTV, failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
           
           
    def scrapeTV(self, path, shows=[], includeEpisodes=False):
        self.log('scrapeTV path = %s'%(path))
        items = dict([(show['file'],show) for show in shows if show.get('file')])
        files = (self.getDirectory(path) or [])
        if len(files) > 0: random.shuffle(files)
        for file in files:
            if self.monitor.waitForAbort(0.1): return False
            elif not file.get('file'): continue
            elif not file['file'] in items:
                self.tasks.setdefault('scrapeDirectory',set()).add(file['file'])
            elif includeEpisodes:
                missing = self.parseEpisodes(items[file['file']],(self.getEpisodes(items[file['file']]['tvshowid']) or [])).get('missing',[])
                if len(missing) > 0: 
                    random.shuffle(missing)
                    for episode in missing:
                        if self.monitor.waitForAbort(0.1): return False
                        self.tasks.setdefault('scrapeDirectory',set()).add(episode['file'])
        return True

      
    def refreshTV(self, shows=[], clean=False, ignoreNFO=True, includeEpisodes=True):
        self.log('refreshTV shows = %s, clean = %s, ignoreNFO = %s, includeEpisodes = %s'%(len(shows),clean,ignoreNFO,includeEpisodes))
        if len(shows) > 0: random.shuffle(shows)
        for show in shows:
            if self.monitor.waitForAbort(0.1): return False
            elif clean: self.tasks.setdefault('cleanTV',set()).add(show.get('tvshowid',-1))
            self.tasks.setdefault('refreshTVshow',set()).add((show.get('tvshowid'),ignoreNFO,includeEpisodes))
        return True
      

    def cleanMovies(self, movies, master=None):
        def __findShadowCopy(movies):
            for idx, mv in enumerate(movies):
                if xbmcvfs.exists(mv.get('file')):
                    try: return movies.pop(idx)
                    except Exception: pass
            self.log('cleanMovies, no shadows found!')#all episodes found don't exist? todo user prompt to remove?
        try:
            if master is None: master = __findShadowCopy(movies) #actual file, remaining shadow duplicates.
            for movie in movies:
                if self.monitor.waitForAbort(0.1): return False
                elif master.get('label') == movie.get('label') and master.get('movieid',-1) != movie.get('movieid'):
                    if not xbmcvfs.exists(movie.get('file')) or master.get('file','-1') == movie.get('file'):
                        self.log('cleanMovies, Queuing remove duplicate %s'%(movie.get('file')))
                        removeMovie(movie.get('movieid'))
                    elif master.get('file','-1') != movie.get('file'): #duplicate file found
                        self.log('cleanMovies, found duplicate physical file [%s] exists [%s]'%(movie.get('file'),xbmcvfs.exists(movie.get('file')))) #todo prompt user to delete? for now cache values
            self.log('cleanMovies, finished!')
            return True
        except Exception as e:
            self.log('cleanMovies, failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))


    def scrapeMovies(self, path, movies=[]):
        self.log('scrapeMovies, path = %s'%(path))
        paths = dict([(os.path.split(item['file'])[0],item) for item in movies if item.get('file')])
        items = (self.getDirectory(path) or [])
        if len(items) > 0: random.shuffle(items)
        for item in items:
            if self.monitor.waitForAbort(0.1): return False
            elif not item.get('file') in paths:
                self.tasks.setdefault('scrapeDirectory',set()).add(item.get('file'))
        return True


    def refreshMovies(self, movies=[], clean=False, ignore=True):
        self.log('refreshMovies, movies = %s, clean = %s, ignore = %s'%(len(movies),clean,ignore))
        if len(movies) > 0: random.shuffle(movies)
        for movie in movies:
            if self.monitor.waitForAbort(0.1): return False
            if clean: self.tasks.setdefault('cleanMovies',list()).extend(findMatch(movie.get('file'),movies))
            self.tasks.setdefault('refreshMovie',set()).add((movie.get('movieid'),ignore))
        return True
        
           
    #@cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def parseEpisodes(self, show={}, episodes=[]):
        self.log('parseEpisodes show = %s'%(show.get('tvshowid')))
        refresh   = [] #database entry w/file.
        missing   = [] #file w/o database entry
        abandoned = [] #database entry w/o file.
        
        if len(episodes) > 0: random.shuffle(episodes)
        for episode in episodes:
            if   self.monitor.waitForAbort(0.1): return False
            elif not episode.get('file'): continue
            items = (self.getDirectory(os.path.join(os.path.split(episode['file'])[0],'')) or [])
            for item in items:
                if   self.monitor.waitForAbort(0.1): return False
                elif not item.get('file'): continue
                elif item['file'] == episode['file']:       refresh.append(episode)
                elif not xbmcvfs.exists(episode['file']): abandoned.append(episode)
                else:                                       missing.append(item)
        return {'refresh': refresh, 'missing': missing, 'abandoned': abandoned}


if __name__ == '__main__': Service()._start()