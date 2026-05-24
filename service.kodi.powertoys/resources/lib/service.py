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
from cqueue import CustomQueue

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (set, tuple)): return list(obj)
        return json.JSONEncoder.default(self, obj)

class Player(xbmc.Player):
    def __init__(self, monitor=None):
        xbmc.Player.__init__(self)
        self.monitor = monitor
        self.service = monitor.service if monitor else None
        self.playingItem = {'listitem':xbmcgui.ListItem()}
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    def isPseudoTV(self):
        try:
            sys_info = self.getPlayerItem().getProperty('sysInfo')
            if not sys_info: return False
            return '@%s'%(slugify(ADDON_NAME)) in loadJSON(decodeString(sys_info)).get('chid','')
        except:
            return False

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
        except: return self.playingItem['listitem'].getPath()

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
        except: return int((BUILTIN.getInfoLabel('Player.Progress') or '-1'))

    def getTimeLabel(self, prop: str='TimeRemaining') -> Union[int, float]:
        if self.isPlaying(): return timeString2Seconds(BUILTIN.getInfoLabel('%s(hh:mm:ss)'%(prop),'Player'))
        return -1

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
        
        raw_tasks = (self.cache.get('tasks', checksum=ADDON_VERSION, json_data=True) or dict())
        if isinstance(raw_tasks, str):
            try:
                raw_tasks = json.loads(raw_tasks)
            except Exception:
                raw_tasks = dict()
        self.tasks = {}
        for k, v in list(raw_tasks.items()):
            if k in ['scrapeDirectory', 'cleanTV', 'refreshTVshow', 'refreshMovie']:
                self.tasks[k] = set(tuple(x) if isinstance(x, list) else x for x in v)
            else:
                self.tasks[k] = list(v)

        self.log('__init__ tasks = %s'%(dict([(key,len(value)) for key, value in list(self.tasks.items())])))
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)

    def _que(self, func, priority=-1, *args, **kwargs):
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
                 
    def _exit(self):
        self.log('_exit tasks = %s'%(dict([(key,len(value)) for key, value in list(self.tasks.items())])))
        serialized_tasks = {}
        for k, v in list(self.tasks.items()):
            serialized_tasks[k] = list(v)
        self.cache.set('tasks', json.dumps(serialized_tasks, cls=SetEncoder), checksum=ADDON_VERSION, expiration=datetime.timedelta(days=28), json_data=True)

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
        nxrun = (nextrun or self.cache.get(func.__name__) or 0) 
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
            return False

    def runRefresh(self, clean=False, ignoreNFO=True, includeEpisodes=True):
        try:
            return (self.refreshTV((self.getTVshows() or []),clean,ignoreNFO,includeEpisodes) & 
                    self.refreshMovies((self.getMovies() or []),clean,ignoreNFO))
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
            return False

    def runDuplicate(self):
        try: return (self.cleanTV([]) & self.cleanMovies([]))
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
            return False
            
    def scrapeDirectory(self, path, show=None):
        if show is None: show = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        self.log('scrapeDirectory, scraping [%s]'%(path))
        if sendJSON({"method":"VideoLibrary.Scan","params":{"directory":path,"showdialogs":show}}).get('result') == "OK":
            while not self.monitor.abortRequested():
                if self.monitor.waitForAbort(REAL_SETTINGS.getSettingInt('Start_Delay')): break
                elif isScanning(): self.log('scrapeDirectory, waiting for scraper to finish...')
                else: break
            self.log('scrapeDirectory, finished!')

    def remapPath(self, path):
        """ Remap network source path rules safely to local filesystem equivalents """
        if REAL_SETTINGS.getSettingBool('PathMapping_Enabled'):
            remote_prefix = REAL_SETTINGS.getSetting('PathMapping_Remote')
            local_prefix = REAL_SETTINGS.getSetting('PathMapping_Local')
            if remote_prefix and path.startswith(remote_prefix):
                return path.replace(remote_prefix, local_prefix, 1)
        return path

    def executeRemoveEpisode(self, episode_id, file_path, context=""):
        if REAL_SETTINGS.getSettingBool('Dry_Run_Mode'):
            self.log('[DRY RUN] %s -> Skipping removal of Episode ID: %s (%s)' % (context, episode_id, file_path))
            return False
        self.log('%s -> Removing Database Entry for Episode ID: %s' % (context, episode_id))
        removeEpisode(episode_id)
        return True

    def executeRemoveMovie(self, movie_id, file_path, context=""):
        if REAL_SETTINGS.getSettingBool('Dry_Run_Mode'):
            self.log('[DRY RUN] %s -> Skipping removal of Movie ID: %s (%s)' % (context, movie_id, file_path))
            return False
        self.log('%s -> Removing Database Entry for Movie ID: %s' % (context, movie_id))
        removeMovie(movie_id)
        return True

    def trashPhysicalFile(self, file_path):
        """ Move files to hidden .kodi_trash container instead of hard wipe """
        if not REAL_SETTINGS.getSettingBool('Physical_Delete_Enabled'):
            return False
        try:
            base_dir  = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            trash_dir = os.path.join(base_dir, '.kodi_trash')
            if not trash_dir.endswith(('/', '\\')): trash_dir += '/'
            
            if not xbmcvfs.exists(trash_dir):
                xbmcvfs.mkdirs(trash_dir)
            new_position = os.path.join(trash_dir, file_name)
            
            if REAL_SETTINGS.getSettingBool('Dry_Run_Mode'):
                self.log('[DRY RUN] Trash physical file: %s -> %s' % (file_path, new_position))
                return True
            return xbmcvfs.rename(file_path, new_position)
        except Exception as e:
            self.log('trashPhysicalFile failed: %s' % str(e), xbmc.LOGERROR)
        return False
            
    def cleanTV(self, matches, master=None, show=None):
        pDialog = None
        if show is None: show = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        try:
            if show:
                pDialog = xbmcgui.DialogProgressBG()
                pDialog.create(ADDON_NAME, 'Cleaning TV library entries...')
            total_matches = len(matches)

            for idx, match in enumerate(matches):
                if self.monitor.waitForAbort(0.01): break
                if len(match) <= 1: continue
                
                percent = int((idx / total_matches) * 100) if total_matches > 0 else 0
                if pDialog: pDialog.update(percent, message="Processing: %s" % match[0].get('label', ''))
                
                duplicates = list(match)
                master_episode = None
                
                for i, episode in enumerate(duplicates):
                    mapped_path = self.remapPath(episode.get('file', ''))
                    if xbmcvfs.exists(mapped_path):
                        master_episode = duplicates.pop(i)
                        break
                        
                if master_episode is None: 
                    self.log('cleanTV, duplicate files do not exist physically!')
                    continue

                for episode in duplicates:
                    if self.monitor.waitForAbort(0.1): 
                        if pDialog: pDialog.close()
                        return False
                        
                    if master_episode.get('label') == episode.get('label'):
                        mapped_ep_path = self.remapPath(episode.get('file', ''))
                        
                        # Multi-Episode Stacked File Handling check guard
                        if master_episode.get('file') == episode.get('file'):
                            if master_episode.get('episode') != episode.get('episode'):
                                self.log('cleanTV, skipping multi-episode stack tracking link: %s' % episode.get('file'))
                                continue

                        # Missing link drop action
                        if not xbmcvfs.exists(mapped_ep_path):
                            self.executeRemoveEpisode(episode.get('episodeid'), episode.get('file'), "cleanTV (Missing File)")
                                
                        # Virtual shadow entry drop action
                        elif (master_episode.get('file','-1') == episode.get('file') and master_episode.get('episodeid',-1) != episode.get('episodeid')):
                            self.executeRemoveEpisode(episode.get('episodeid'), episode.get('file'), "cleanTV (Shadow Duplicate)")
                                
                        # Physical conflict mirror drop action
                        elif master_episode.get('file','-1') != episode.get('file'):
                            if self.executeRemoveEpisode(episode.get('episodeid'), episode.get('file'), "cleanTV (Physical Duplicate)"):
                                self.trashPhysicalFile(mapped_ep_path)

            if pDialog: pDialog.close()
            self.log('cleanTV, finished!')
            return True
        except Exception as e:
            if 'pDialog' in locals(): pDialog.close()
            self.log('cleanTV, failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
            return False
           
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

    def cleanMovies(self, movies, master=None, show=None):
        pDialog = None
        if show is None: show = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        try:
            if show:
                pDialog = xbmcgui.DialogProgressBG()
                pDialog.create(ADDON_NAME, 'Cleaning Movie library entries...')
            
            working_list = list(movies)
            total_movies = len(working_list)
            
            def __findShadowCopy(m_list):
                for idx, mv in enumerate(m_list):
                    mapped_mv_path = self.remapPath(mv.get('file', ''))
                    if xbmcvfs.exists(mapped_mv_path):
                        try: return m_list.pop(idx)
                        except Exception: pass
                return None

            if master is None: master = __findShadowCopy(working_list)
            if master is None:
                if pDialog: pDialog.close()
                self.log('cleanMovies, no master file found physically available!')
                return True

            for idx, movie in enumerate(working_list):
                if self.monitor.waitForAbort(0.01): break
                
                # Dynamic visual feedback tracking loop passes
                percent = int((idx / total_movies) * 100) if total_movies > 0 else 0
                if pDialog: pDialog.update(percent, message="Processing: %s" % movie.get('label', ''))

                if master.get('label') == movie.get('label') and master.get('movieid',-1) != movie.get('movieid'):
                    mapped_movie_path = self.remapPath(movie.get('file', ''))
                    
                    if not xbmcvfs.exists(mapped_movie_path) or master.get('file','-1') == movie.get('file'):
                        self.executeRemoveMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Missing or Shadow)")
                    elif master.get('file','-1') != movie.get('file'):
                        if self.executeRemoveMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Physical Duplicate)"):
                            self.trashPhysicalFile(mapped_movie_path)
                            
            if pDialog: pDialog.close()
            self.log('cleanMovies, finished!')
            return True
        except Exception as e:
            if 'pDialog' in locals(): pDialog.close()
            self.log('cleanMovies, failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
            return False

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

    def parseEpisodes(self, show={}, episodes=[]):
        self.log('parseEpisodes show = %s'%(show.get('tvshowid')))
        refresh   = [] 
        missing   = [] 
        abandoned = [] 
        
        if len(episodes) > 0: random.shuffle(episodes)
        directory_cache = {}
        
        for episode in episodes:
            if self.monitor.waitForAbort(0.1): break
            if not episode.get('file'): continue
            
            dir_path = os.path.dirname(episode['file'])
            if dir_path not in directory_cache:
                directory_cache[dir_path] = self.getDirectory(os.path.join(dir_path,'')) or []
                
            items = directory_cache[dir_path]
            file_matched = False
            mapped_ep_path = self.remapPath(episode['file'])
            
            for item in items:
                if not item.get('file'): continue
                if item['file'] == episode['file']:
                    refresh.append(episode)
                    file_matched = True
                    break
            
            if not file_matched:
                if not xbmcvfs.exists(mapped_ep_path): 
                    abandoned.append(episode)
                else:
                    for item in items:
                        if item.get('file') and item['file'] != episode['file']:
                            missing.append(item)
                            
        return {'refresh': refresh, 'missing': missing, 'abandoned': abandoned}

if __name__ == '__main__': Service()._start()