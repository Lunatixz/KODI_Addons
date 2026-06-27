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
from cqueue  import CustomQueue

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (set, tuple)): return list(obj)
        return json.JSONEncoder.default(self, obj)

class Player(xbmc.Player):
    def __init__(self, monitor=None):
        super(Player, self).__init__()
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
        except: return int((getInfoLabel('Player.Progress') or '-1'))

    def getTimeLabel(self, prop: str='TimeRemaining') -> Union[int, float]:
        if self.isPlaying(): return timeString2Seconds(getInfoLabel('%s(hh:mm:ss)'%(prop),'Player'))
        return -1

class Monitor(xbmc.Monitor):
    def __init__(self, service=None):
        super(Monitor, self).__init__()
        self.service = service
        self.player  = Player(self)
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        
    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
        if self.service:
            if method == "VideoLibrary.OnScanFinished" and REAL_SETTINGS.getSettingBool('Clean_OnScanFinished'):
                self.log("Event Intercept -> Library Scan Finished. Injecting optimization pass.")
                self.service._que(self.service.runClean, priority=5)
            elif method in ["VideoLibrary.OnUpdate", "VideoLibrary.OnScanStarted"]:
                if hasattr(self.service, '_cache'):
                    self.service._cache.clear()

class Service(object):
    cache = SimpleCache()
    cache.enable_mem_cache = True
    
    def __init__(self):
        self.isRunning  = False
        self.monitor  = Monitor(self)
        self.player   = self.monitor.player
        self.queue    = CustomQueue(service=self)
        self.pid      = "%s_%s" % (platform.node(), os.getpid())
        self.wait     = REAL_SETTINGS.getSettingInt('Start_Delay')
        self._cache   = {}
        self._tasks   = self._load()

    def __del__(self):
        self._save()
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)

    def _load(self):
        _tasks = {}
        _raw   = (self.cache.get('tasks', checksum=ADDON_VERSION, json_data=True) or dict())
        if isinstance(_raw, str):
            try:              _raw = json.loads(_raw)
            except Exception: _raw = dict()
        for k, v in list(_raw.items()):
            if k in ['scrapeDirectory', 'cleanTV', 'refreshTVshow', 'refreshMovie']:
                _tasks[k] = set(tuple(x) if isinstance(x, list) else x for x in v)
            else:
                _tasks[k] = list(v)
        for k in ['scrapeDirectory', 'cleanTV', 'refreshTVshow', 'refreshMovie']:
            _tasks.setdefault(k, set())
        _tasks.setdefault('cleanMovies', list())
        self.log('_load tasks = %s'%(dict([(key,len(value)) for key, value in list(_tasks.items())])))
        return _tasks
        
    def _menu(self, sysARG):
        self.log('_menu')
        try:    param = sysARG[1]
        except: param = None
        if param is None: return
              
    def _que(self, func, priority=3, *args, **kwargs):
        self.log('_que, priority = %s, func = %s, args = %s, kwargs = %s' % (priority,func.__name__, args, kwargs))
        self.queue.push((func, args, kwargs), priority)

    def _sleep(self, wait=0.5) -> bool:
        while not self.monitor.abortRequested() and wait > 0:
            if self.monitor.waitForAbort(wait): return True
            wait -= 0.5
        return False
               
    def _start(self):
        self.log('_start, wait = %s'%(self.wait))
        self.monitor.waitForAbort(self.wait)
        while not self.monitor.abortRequested():
            if    self.monitor.waitForAbort(2.0): break
            else: self._run()
        self._save()

    def _save(self):
        self.log('_save tasks = %s'%(dict([(key,len(value)) for key, value in list(self._tasks.items())])))
        _tasks = {}
        for k, v in list(self._tasks.items()): _tasks[k] = list(v)
        self.cache.set('tasks', json.dumps(_tasks, cls=SetEncoder), checksum=ADDON_VERSION, expiration=datetime.timedelta(days=28), json_data=True)
            
    def _chkPlaying(self):
        return self.player.isPlaying() and not REAL_SETTINGS.getSettingBool('Run_Playing')
        
    def _chkIdle(self):
        if REAL_SETTINGS.getSettingBool('Run_Idling'): return int(xbmc.getGlobalIdleTime() or '0') > self.wait
        return False
        
    @contextmanager
    def _chkUpdate(self, func, days=1, nextrun=None, *args, **kwargs):
        nxrun    = (nextrun or self.cache.get(func.__name__) or 0) 
        epoch    = int(time.time())
        runevery = days * 86400
        if epoch >= nxrun:
            try: 
                finished = func(*args, **kwargs)
            except Exception as e: 
                finished = False
                self.log('_chkUpdate, failed! %s'%(e), xbmc.LOGERROR)
            finally:
                if finished: 
                    self.log('_chkUpdate, func = %s, next run in %s days, finished = %s' % (func.__name__, days, finished))
                    # self.cache.set(func.__name__, (epoch + runevery), expiration=datetime.timedelta(days=28))
        yield
         
    def _run(self):
        self.log('_run tasks = %s'%(dict([(key,len(value)) for key, value in list(self._tasks.items())])))
        if   self._chkPlaying() or isScanning(): self.log('_run, waiting for scraper or player to finish...')
        elif self._tasks.get('scrapeDirectory'):  self._que(self.scrapeDirectory, 2, self._tasks.get('scrapeDirectory').pop())
        elif self._tasks.get('cleanTV'):          self._que(self.cleanTV        , 3, self._tasks.get('cleanTV').pop())
        elif self._tasks.get('cleanMovies'):      self._que(self.cleanMovies    , 3, self._tasks.get('cleanMovies').pop(0))
        elif self._tasks.get('refreshTVshow'):    self._que(self.refreshTVshow  , 4, *self._tasks.get('refreshTVshow').pop())
        elif self._tasks.get('refreshMovie'):     self._que(self.refreshMovie   , 4, *self._tasks.get('refreshMovie').pop())
        elif not self.isRunning:
            self.isRunning = True
            if REAL_SETTINGS.getSettingBool('Scraper_Enabled'):
                with self._chkUpdate(self.runScraper,REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')): pass
            if REAL_SETTINGS.getSettingBool('Refresh_Enabled'):
                with self._chkUpdate(self.runRefresh,REAL_SETTINGS.getSettingInt('Refresh_Interval_DAYS')): pass
            self.isRunning = False
   
    # @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getDirectory(self, path):
        return getDirectory(path)
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getTVshows(self):
        return getTVshows()
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getMovies(self):
        return getMovies()
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getEpisodes(self, tvshowid):
        return getEpisodes(tvshowid)

    def scrapeDirectory(self, path, show_dialog=None):
        if show_dialog is None: show_dialog = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        self.log('scrapeDirectory, scraping [%s]'%(path))
        if sendJSON({"method":"VideoLibrary.Scan","params":{"directory":path,"showdialogs":show_dialog}}).get('result') == "OK":
            while not self.monitor.abortRequested():
                if   self.monitor.waitForAbort(0.5): break
                elif isScanning(): self.log('scrapeDirectory, waiting for scraper to finish...')
                else: break
            self.log('scrapeDirectory, finished!')

    def runScraper(self):
        try:
            return (self.scrapeTV(REAL_SETTINGS.getSetting('Scraper_TV_Folder')       , (self.getTVshows() or [])) & 
                    self.scrapeMovies(REAL_SETTINGS.getSetting('Scraper_Movie_Folder'), (self.getMovies()  or [])))
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            notification(LANGUAGE(32009))
            return False

    def scrapeTV(self, path, shows=[], includeEpisodes=None):
        if includeEpisodes is None: includeEpisodes = REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')
        files = (self.getDirectory(path) or [])
        if len(files) > 0:
            self.log('scrapeTV path = %s, files = %s'%(path,len(files)))
            items = dict([(show['file'],show) for show in shows if show.get('file')])
            random.shuffle(files)
            for file in files:
                if   self.monitor.waitForAbort(0.01): return 
                elif file.get('file') and not filefile.get('file') in items: 
                    self._tasks.setdefault('scrapeDirectory',set()).add(file['file'])
                    if includeEpisodes:
                        missing = self.parseEpisodes(items[file['file']],(self.getEpisodes(items[file['file']]['tvshowid']) or [])).get('missing',[])
                        if len(missing) > 0: 
                            random.shuffle(missing)
                            for episode in missing: 
                                self._tasks.setdefault('scrapeDirectory',set()).add(episode['file'])
        return True
        
    def scrapeMovies(self, path, movies=[]):
        files = (self.getDirectory(path) or [])
        if len(files) > 0: 
            self.log('scrapeMovies path = %s, files = %s'%(path,len(files)))
            items = dict([(self._pathKey(self._directoryPath(movie['file'])),movie) for movie in movies if movie.get('file')])
            random.shuffle(files)
            for file in files:
                if   self.monitor.waitForAbort(0.01): return False
                elif not self._pathKey(file.get('file')) in items:
                    self._tasks.setdefault('scrapeDirectory',set()).add(file.get('file'))
        return True

    def cleanTV(self, tvshowid, show_dialog=None):
        pDialog     = None
        processed   = set()
        episodes    = (self.getEpisodes(tvshowid) or [])
        message     = '[DRY RUN] Processing:' if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled') else 'Processing:'
        if episodes and episodes[0] and not self._verifySource(episodes[0].get('file')): return False
        episodes   = [self._episodeKey(episode) for episode in episodes]
        
        if show_dialog is None: show_dialog = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        duplicates = findDupes(episodes, key='episode_key')
        if show_dialog and duplicates:
            pDialog = xbmcgui.DialogProgressBG()
            pDialog.create(ADDON_NAME, 'Cleaning TV library entries...')

        for eidx, episode in enumerate(episodes):
            percent = int((eidx / len(episodes)) * 100) if len(episodes) > 0 else 0
            if self.monitor.waitForAbort(0.01): return False
            elif not episode: continue
            elif not xbmcvfs.exists(episode.get('file', '')):
                self.log('cleanTV, episode file no longer exists: %s' % episode.get('file'))
                if pDialog: pDialog.update(percent, message="%s %s\nAbandoned: %s" % (message,episode.get('showtitle',tvshowid),episode.get('label', '')))
                self._removeEpisode(episode.get('episodeid'), episode.get('file'), "cleanTV (Missing File)")
            else:
                if episode.get('episode_key') in processed: continue
                shadow_copies = sorted(duplicates.get(episode.get('episode_key'),{}), key=lambda x: self.get_stream_weight(x.get('file', '')), reverse=True)
                print('shadow_copies',shadow_copies)
                if shadow_copies:
                    processed.add(episode.get('episode_key'))
                    self.log("cleanTV, episode = %s, shadow_copies = %s" % (episode.get('label'), len(shadow_copies)))
                    master_copy = shadow_copies.pop(0) #duplicate we want to keep weighted by quality keywords.
                    for sidx, shadow_copy in enumerate(shadow_copies):
                        if not shadow_copy: continue
                        elif self.monitor.waitForAbort(0.01): return False
                        if master_copy.get('label') == shadow_copy.get('label'):
                            if pDialog: pDialog.update(int((sidx / len(shadow_copies)) * 100) if len(shadow_copies) > 0 else 0, message="%s %s\nDuplicates: %s" % (message,episode.get('showtitle',tvshowid),shadow_copy.get('label', '')))

                            #todo playcount shadow_copy and add to master_copy?
                            if not xbmcvfs.exists(shadow_copy.get('file')):
                                self.log('cleanTV, shadow entry file no longer exists: %s' % shadow_copy.get('file'))
                                self._removeEpisode(shadow_copy.get('episodeid'), shadow_copy.get('file'), "cleanTV (Missing File)")
                                    
                            elif master_copy.get('file','-1') == shadow_copy.get('file','0'):
                                if master_copy.get('episode') != shadow_copy.get('episode'):
                                    self.log('cleanTV, skipping multi-episode stack tracking link: %s' % shadow_copy.get('file'))
                                    continue
                                elif master_copy.get('episodeid',-1) != shadow_copy.get('episodeid'):
                                    self.log('cleanTV, duplicate shadow entry detected: %s' % shadow_copy.get('file'))
                                    self._removeEpisode(shadow_copy.get('episodeid'), shadow_copy.get('file'), "cleanTV (Shadow Duplicate)")
                                    
                            elif master_copy.get('file','-1') != shadow_copy.get('file','0'):
                                self.log('cleanTV, duplicate entry detected: %s' % shadow_copy.get('file'))
                                self._removeEpisode(shadow_copy.get('episodeid'), shadow_copy.get('file'), "cleanTV (Physical Duplicate)")

        if pDialog: pDialog.close()
        return True

    def cleanMovies(self, movies, show_dialog=None):
        pDialog = None
        movies = [movie for movie in (movies or []) if movie]
        if not movies: return True
        if movies and not self._verifySource(movies[0].get('file')): return False
        if show_dialog is None: show_dialog = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        if show_dialog:
            pDialog = xbmcgui.DialogProgressBG()
            pDialog.create(ADDON_NAME, 'Cleaning Movie library entries...')
        
        message = '[DRY RUN] Processing:' if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled') else 'Processing:'
        shadow_copies = sorted(list(movies), key=lambda x: self.get_stream_weight(x.get('file', '')), reverse=True)
        master_copy   = None
        while not self.monitor.abortRequested():
            if not shadow_copies: break
            master_copy = shadow_copies.pop(0)
            if xbmcvfs.exists(master_copy.get('file')): break
            else: 
                self.log('cleanMovies, movie file no longer exists: %s' % master_copy.get('file'))
                self._removeMovie(master_copy.get('movieid'), master_copy.get('file'), "cleanMovies (Missing File)")
        if master_copy:
            self.log("cleanMovies, duplicate movies detected (%s) - %s" % (len(movies), master_copy.get('label')))
            for midx, movie in enumerate(shadow_copies):
                percent = int((midx / len(shadow_copies)) * 100) if len(shadow_copies) > 0 else 0
                if self.monitor.waitForAbort(0.01): return False
                elif not movie: continue
                elif not xbmcvfs.exists(movie.get('file')):
                    self.log('cleanMovies, movie file no longer exists: %s' % movie.get('file'))
                    if pDialog: pDialog.update(percent, message="%s\nAbandoned: %s" % (message,movie.get('label','')))
                    self._removeMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Missing File)")
                else:
                    if pDialog: pDialog.update(percent, message="Processing: %s" % movie.get('label', ''))
                    if master_copy.get('movieid',-1) != movie.get('movieid') and master_copy.get('file','-1') == movie.get('file','0'):
                        self.log('cleanMovies, duplicate shadow entry detected: %s' % master_copy.get('file'))
                        self._removeMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Shadow copy)")
                    elif master_copy.get('file','-1') != movie.get('file'):
                        self.log('cleanMovies, duplicate file detected: %s' % master_copy.get('file'))
                        self._removeMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Physical Duplicate)")
                            
        if pDialog: pDialog.close()
        return True
       
    def refreshTV(self, shows=[]):
        clean           = REAL_SETTINGS.getSettingBool('Refresh_Clean')
        ignoreNFO       = REAL_SETTINGS.getSettingBool('Refresh_Ignore_NFO')
        includeEpisodes = REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')
        self.log('refreshTV shows = %s, clean = %s, ignoreNFO = %s, includeEpisodes = %s'%(len(shows),clean,ignoreNFO,includeEpisodes))
        if len(shows) > 0: random.shuffle(shows)
        for show in shows:
            if   self.monitor.waitForAbort(0.01): return False
            elif clean: self._tasks.setdefault('cleanTV',set()).add(show.get('tvshowid',-1))
            self._tasks.setdefault('refreshTVshow',set()).add((show.get('tvshowid'),ignoreNFO,includeEpisodes))
        return True

    def refreshMovies(self, movies=[], clean=None, ignoreNFO=None):
        if clean is None: clean = REAL_SETTINGS.getSettingBool('Refresh_Clean')
        if ignoreNFO is None: ignoreNFO = REAL_SETTINGS.getSettingBool('Refresh_Ignore_NFO')
        self.log('refreshMovies, movies = %s, clean = %s, ignoreNFO = %s'%(len(movies),clean,ignoreNFO))
        if len(movies) > 0: random.shuffle(movies)
        if clean:
            for group in self._movieDuplicateGroups(movies):
                self._tasks.setdefault('cleanMovies',list()).append(group)
        for movie in movies:
            if self.monitor.waitForAbort(0.01): return False
            self._tasks.setdefault('refreshMovie',set()).add((movie.get('movieid'),ignoreNFO))
        return True

    def _verifySource(self, path):
        if not path: return True
        root_share = None
        for proto in ['smb://', 'nfs://', 'ftp://', 'dav://', 'sftp://']:
            if path.lower().startswith(proto):
                parts = path.split('/')
                if   len(parts) >= 4: root_share = f"{parts[0]}//{parts[2]}/{parts[3]}/"
                elif len(parts) >= 3: root_share = f"{parts[0]}//{parts[2]}/"
                if root_share and not xbmcvfs.exists(root_share):
                    self.log("_verifySource, Network mount root %s is offline! Aborting removal." % root_share, xbmc.LOGERROR)
                    return False
                break
        return True

    def refreshTVshow(self, tvshowid, ignorenfo=True, includeEpisodes=True):
        self.log('refreshTVshow, tvshowid = %s, ignorenfo = %s, includeEpisodes = %s' % (tvshowid, ignorenfo, includeEpisodes))
        return refreshTVshow(tvshowid, ignorenfo, includeEpisodes)

    def refreshMovie(self, movieid, ignorenfo=True):
        self.log('refreshMovie, movieid = %s, ignorenfo = %s' % (movieid, ignorenfo))
        return refreshMovie(movieid, ignorenfo)

    def _episodeKey(self, episode):
        episode = dict(episode or {})
        episode['episode_key'] = (
            episode.get('tvshowid'),
            episode.get('season'),
            episode.get('episode')
        )
        return episode

    def _movieKey(self, movie):
        return (movie.get('label'), movie.get('year'))

    def _movieDuplicateGroups(self, movies):
        groups = {}
        for movie in movies or []:
            if not movie: continue
            groups.setdefault(self._movieKey(movie), []).append(movie)
        return [group for group in groups.values() if len(group) > 1]

    def _directoryPath(self, path):
        path = path or ''
        if '://' in path:
            idx = path.rstrip('/').rfind('/')
            return path[:idx + 1] if idx > -1 else path
        directory = os.path.dirname(path)
        if directory and not directory.endswith((os.sep, '/', '\\')):
            directory += os.sep
        return directory

    def _pathKey(self, path):
        return (path or '').replace('\\', '/').rstrip('/').lower()

    def get_stream_weight(self, file_path):
        weight = 0
        normalized = (file_path or '').lower()
        if   "2160p" in normalized or "4k" in normalized: weight += 50
        elif "1080p" in normalized: weight += 30
        elif "720p"  in normalized: weight += 10
        if   "remux" in normalized: weight += 20
        if   "x265"  in normalized or "hevc" in normalized: weight += 15
        if   "x264"  in normalized or "h264" in normalized: weight += 5
        if not normalized.startswith(('smb:', 'nfs:')): weight += 5
        return weight

    def runRefresh(self):
        try:
            return (self.refreshTV((self.getTVshows()    or [])) & 
                    self.refreshMovies((self.getMovies() or [])))
        except Exception as e:
            self.log('runRefresh, Scan failed! %s'%(e), xbmc.LOGERROR)
            notification(LANGUAGE(32009))
            return False

    def runClean(self):
        try:
            tvshows  = self.getTVshows()
            movies   = self.getMovies()
            tv_ok    = True
            movie_ok = True
            for show in tvshows:
                if self.monitor.waitForAbort(0.01): return False
                tv_ok = self.cleanTV(show.get('tvshowid')) and tv_ok
            for group in self._movieDuplicateGroups(movies):
                if self.monitor.waitForAbort(0.01): return False
                movie_ok = self.cleanMovies(group) and movie_ok
            return tv_ok and movie_ok
        except Exception as e:
            self.log('runClean, Scan failed! %s'%(e), xbmc.LOGERROR)
            notification(LANGUAGE(32009))
            return False

    def _removeEpisode(self, episode_id, file_path, context=""):
        if not self._verifySource(file_path): return False
        if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled'):
            self.log('[DRY RUN] %s -> Skipping removal of Episode ID: %s (%s)' % (context, episode_id, file_path))
            return False
        self.log('%s -> Removing Database Entry for Episode ID: %s' % (context, episode_id))
        if removeEpisode(episode_id) and REAL_SETTINGS.getSettingBool('Delete_Enabled'):
            xbmcvfs.delete(file_path)
        return True

    def _removeMovie(self, movie_id, file_path, context=""):
        if not self._verifySource(file_path): return False
        if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled'):
            self.log('[DRY RUN] %s -> Skipping removal of Movie ID: %s (%s)' % (context, movie_id, file_path))
            return False
        self.log('%s -> Removing Database Entry for Movie ID: %s' % (context, movie_id))
        if removeMovie(movie_id) and REAL_SETTINGS.getSettingBool('Delete_Enabled'):
            xbmcvfs.delete(file_path)
        return True

    def parseEpisodes(self, show={}, episodes=[]):
        self.log('parseEpisodes tvshowid = %s'%(show.get('tvshowid')))
        refresh   = [] 
        missing   = [] 
        abandoned = []
        processed = set()
        episode_files = set([episode.get('file') for episode in episodes if episode.get('file')])
        if len(episodes) > 0: random.shuffle(episodes)
        
        for episode in episodes:
            if self.monitor.waitForAbort(0.01): break
            elif not episode.get('file'): continue
            dir_path = self._directoryPath(episode['file'])
            if dir_path not in self._cache:
                self._cache[dir_path] = {f.get('file'): f for f in (self.getDirectory(dir_path) or []) if f.get('file')}
                
            items_dict = self._cache[dir_path]
            if episode['file'] in items_dict: 
                refresh.append(episode)
            else:
                if not xbmcvfs.exists(episode['file']): 
                    abandoned.append(episode)
                    
            if dir_path not in processed:
                for f_path, item in items_dict.items():
                    if f_path not in episode_files:
                        missing.append(item)
                processed.add(dir_path)
        return {'refresh': refresh, 'missing': missing, 'abandoned': abandoned}
        
if __name__ == '__main__': Service()._start()
