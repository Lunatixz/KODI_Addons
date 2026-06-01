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
        
        if self.service:
            if method == "VideoLibrary.OnScanFinished" and REAL_SETTINGS.getSettingBool('Clean_OnScanFinished'):
                self.log("Event Intercept -> Library Scan Finished. Injecting optimization pass.")
                self.service._que(self.service.runClean, priority=1)
            elif method in ["VideoLibrary.OnUpdate", "VideoLibrary.OnScanStarted"]:
                if hasattr(self.service, 'directory_cache'):
                    self.service.directory_cache.clear()


class Service(object):
    cache = SimpleCache()
    cache.enable_mem_cache = True
    
    def __init__(self):
        self.running  = False
        self.monitor  = Monitor(self)
        self.player   = self.monitor.player
        self.priority = CustomQueue(priority=True, service=self)
        self.pid      = "%s_%s" % (platform.node(), os.getpid())
        self.waitTime = REAL_SETTINGS.getSettingInt('Start_Delay')
        self.directory_cache = {}
        
        raw_tasks = (self.cache.get('tasks', checksum=ADDON_VERSION, json_data=True) or dict())
        if isinstance(raw_tasks, str):
            try:              raw_tasks = json.loads(raw_tasks)
            except Exception: raw_tasks = dict()
                
        self.tasks = {}
        for k, v in list(raw_tasks.items()):
            if k in ['scrapeDirectory', 'cleanTV', 'refreshTVshow', 'refreshMovie']:
                self.tasks[k] = set(tuple(x) if isinstance(x, list) else x for x in v)
            else:
                self.tasks[k] = list(v)

        for k in ['scrapeDirectory', 'cleanTV', 'refreshTVshow', 'refreshMovie']:
            self.tasks.setdefault(k, set())
        self.tasks.setdefault('cleanMovies', list())
        self.log('__init__ tasks = %s'%(dict([(key,len(value)) for key, value in list(self.tasks.items())])))
    
    
    def __del__(self):
        self._exit()
        
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)

    def _menu(self, sysARG):
        self.log('_menu')
        try:    param = sysARG[1]
        except: param = None
        if param is None: return
              
    def _que(self, func, priority=-1, *args, **kwargs):
        if priority == -1: priority = self.priority.qsize + 1
        self.log('_que, priority = %s, func = %s, args = %s, kwargs = %s' % (priority,func.__name__, args, kwargs))
        self.priority._push((func, args, kwargs), priority)

    def _start(self):
        self.waitTime = REAL_SETTINGS.getSettingInt('Start_Delay')
        self.log('_start, wait = %s'%(self.waitTime))
        self.monitor.waitForAbort(self.waitTime)
        while not self.monitor.abortRequested():
            if    self.monitor.waitForAbort(2.0): break
            else: self._run()
        self._exit()

    def _run(self):
        if   self._chkPlaying() or isScanning(): self.log('_run, waiting for scraper or player to finish...')
        elif self.tasks.get('scrapeDirectory'):  self._que(self.scrapeDirectory, -1, self.tasks.get('scrapeDirectory').pop())
        elif self.tasks.get('cleanTV'):          self._que(self.cleanTV        , -1, self.tasks.get('cleanTV').pop())
        elif self.tasks.get('cleanMovies'):      self._que(self.cleanMovies    , -1, self.tasks.get('cleanMovies').pop(0))
        elif self.tasks.get('refreshTVshow'):    self._que(self.refreshTV      , -1, self.tasks.get('refreshTVshow').pop())
        elif self.tasks.get('refreshMovie'):     self._que(self.refreshMovie   , -1, self.tasks.get('refreshMovie').pop())
        elif not self.running:
            self.running = True
            if REAL_SETTINGS.getSettingBool('Scraper_Enabled'):
                self.log('_run, starting background scraper...')
                with self._chkUpdate(self.runScraper,REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')): pass
            if REAL_SETTINGS.getSettingBool('Refresh_Enabled'):
                self.log('_run, starting background refresh...')
                with self._chkUpdate(self.runRefresh,REAL_SETTINGS.getSettingInt('Refresh_Interval_DAYS')): pass
            self.running = False
   
    def _exit(self):
        self.log('_exit tasks = %s'%(dict([(key,len(value)) for key, value in list(self.tasks.items())])))
        serialized_tasks = {}
        for k, v in list(self.tasks.items()):
            serialized_tasks[k] = list(v)
        self.cache.set('tasks', json.dumps(serialized_tasks, cls=SetEncoder), checksum=ADDON_VERSION, expiration=datetime.timedelta(days=28), json_data=True)
                   
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getDirectory(self, path):
        return (getDirectory(path) or [])
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getTVshows(self):
        return (getTVshows() or [])
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getMovies(self):
        return (getMovies() or [])
    
    @cacheit(expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')))
    def getEpisodes(self, tvshowid):
        return (getEpisodes(tvshowid) or [])

    def _chkPlaying(self):
        return self.player.isPlaying() and not REAL_SETTINGS.getSettingBool('Run_Playing')
        
    def _chkIdle(self):
        if REAL_SETTINGS.getSettingBool('Run_Idling'): return int(xbmc.getGlobalIdleTime() or '0') > self.waitTime
        return False
        
    @contextmanager
    def _chkUpdate(self, func, days=1, nextrun=None, *args, **kwargs):
        nxrun    = (nextrun or self.cache.get(func.__name__) or 0) 
        epoch    = int(time.time())
        runevery = days * 86400
        if epoch >= nxrun:
            try: 
                finished = func(*args, **kwargs)
                yield self.log('_chkUpdate, func = %s, next run in %s days, finished = %s' % (func.__name__, days, finished))
            except Exception as e: 
                finished = False
                self.log('_chkUpdate, failed! %s'%(e), xbmc.LOGERROR)
            finally:
                if finished: 
                    self.cache.set(func.__name__, (epoch + runevery), expiration=datetime.timedelta(days=28))
        else: yield
         
    def scrapeDirectory(self, path, show=None):
        if show is None: show = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        self.log('scrapeDirectory, scraping [%s]'%(path))
        if sendJSON({"method":"VideoLibrary.Scan","params":{"directory":path,"showdialogs":show}}).get('result') == "OK":
            while not self.monitor.abortRequested():
                if   self.monitor.waitForAbort(0.5): break
                elif isScanning(): self.log('scrapeDirectory, waiting for scraper to finish...')
                else: break
            self.log('scrapeDirectory, finished!')

    def cleanTV(self, tvshowid, show=None):
        episodes    = self.getEpisodes(tvshowid)
        duplicates  = findDupes(episodes)
        pDialog     = None
        master      = None
        message     = '[DRY RUN] Processing:' if REAL_SETTINGS.getSettingBool('Dry_Run_Mode') else 'Processing:'
        if show is None: show = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        self.log(f'cleanTV, episodes = {len(episodes)}, show = {show}')
        try:
            if episodes and episodes[0] and not self._verifyNetwork(episodes[0].get('file')): return False
            if show:
                pDialog = xbmcgui.DialogProgressBG()
                pDialog.create(ADDON_NAME, 'Cleaning TV library entries...')

            for eidx, episode in enumerate(episodes):
                if self.monitor.waitForAbort(0.01): break
                elif not episode: continue
                shadow_copies = sorted(duplicates.get(episode.get('label'),{}), key=lambda x: self.get_stream_weight(x.get('file', '')), reverse=True)
                self.log(f'cleanTV, episode = {episode.get('label')}, shadow_copies = {len(shadow_copies)}')
                if shadow_copies:
                    master_copy = shadow_copies.pop(0) #duplicate we want to keep.
                    for sidx, shadow_copy in enumerate(shadow_copies):
                        if self.monitor.waitForAbort(0.01): break
                        elif not shadow_copy: continue
                        if master_copy.get('label') == shadow_copy.get('label'):
                            mapped_ep_path = self.remapPath(shadow_copy.get('file', ''))
                            if pDialog: pDialog.update(int((sidx / len(shadow_copies)) * 100) if len(shadow_copies) > 0 else 0, message="%s %s\nDuplicates: %s" % (message,episode.get('showtitle',tvshowid),shadow_copy.get('label', '')))
                            
                            if master_copy.get('file') == shadow_copy.get('file'):
                                if master_copy.get('episode') != shadow_copy.get('episode'):
                                    self.log('cleanTV, skipping multi-episode stack tracking link: %s' % shadow_copy.get('file'))
                                    continue

                            state_snapshot = self.get_media_bookmark("episode", shadow_copy.get('episodeid'))
                            if not xbmcvfs.exists(mapped_ep_path):
                                if self.executeRemoveEpisode(shadow_copy.get('episodeid'), shadow_copy.get('file'), "cleanTV (Missing File)"):
                                    self.restore_media_bookmark("episode", master_copy.get('file'), state_snapshot)
                                    
                            if (master_copy.get('file','-1') == shadow_copy.get('file') and master_copy.get('episodeid',-1) != shadow_copy.get('episodeid')):
                                if self.executeRemoveEpisode(shadow_copy.get('episodeid'), shadow_copy.get('file'), "cleanTV (Shadow Duplicate)"):
                                    self.restore_media_bookmark("episode", master_copy.get('file'), state_snapshot)
                                    
                            elif master_copy.get('file','-1') != shadow_copy.get('file'):
                                if self.executeRemoveEpisode(shadow_copy.get('episodeid'), shadow_copy.get('file'), "cleanTV (Physical Duplicate)"):
                                    self.executeTrashFile(mapped_ep_path)
                                    self.restore_media_bookmark("episode", master_copy.get('file'), state_snapshot)

                if not xbmcvfs.exists(self.remapPath(episode.get('file', ''))):
                    percent = int((eidx / len(episodes)) * 100) if len(episodes) > 0 else 0
                    if pDialog: pDialog.update(percent, message="%s %s\nAbandoned: %s" % (message,episode.get('showtitle',tvshowid),episode.get('label', '')))
                    self.executeRemoveEpisode(episode.get('episodeid'), episode.get('file'), "cleanTV (Missing File)")

            if pDialog: pDialog.close()
            self.log('cleanTV, finished!')
            return True
        except Exception as e:
            if 'pDialog' in locals() and pDialog: pDialog.close()
            self.log('cleanTV, failed! %s'%(e), xbmc.LOGERROR)
            return False

    def refreshTV(self, shows=[]):
        clean           = REAL_SETTINGS.getSettingBool('Refresh_Clean')
        ignoreNFO       = REAL_SETTINGS.getSettingBool('Refresh_Ignore_NFO')
        includeEpisodes = REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')
        self.log('refreshTV shows = %s, clean = %s, ignoreNFO = %s, includeEpisodes = %s'%(len(shows),clean,ignoreNFO,includeEpisodes))
        if len(shows) > 0: random.shuffle(shows)
        for show in shows:
            if   self.monitor.waitForAbort(0.1): return False
            elif clean: self.tasks.setdefault('cleanTV',set()).add(show.get('tvshowid',-1))
            self.tasks.setdefault('refreshTVshow',set()).add((show.get('tvshowid')))
        return True

    def cleanMovies(self, movies, master=None, show=None):
        pDialog = None
        if show is None: show = REAL_SETTINGS.getSettingBool('Scraper_Show_Dialog')
        
        if movies and not self._verifyNetwork(movies[0].get('file')):
            return False

        try:
            if show:
                pDialog = xbmcgui.DialogProgressBG()
                pDialog.create(ADDON_NAME, 'Cleaning Movie library entries...')
            
            working_list = sorted(list(movies), key=lambda x: self.get_stream_weight(x.get('file', '')), reverse=True)
            total_movies = len(working_list)
            
            if master is None and working_list: 
                master = working_list.pop(0)
            if master is None:
                if pDialog: pDialog.close()
                self.log('cleanMovies, no master file found physically available!')
                return True

            for idx, movie in enumerate(working_list):
                if self.monitor.waitForAbort(0.01): break
                
                percent = int((idx / total_movies) * 100) if total_movies > 0 else 0
                if pDialog: pDialog.update(percent, message="Processing: %s" % movie.get('label', ''))

                if master.get('label') == movie.get('label') and master.get('movieid',-1) != movie.get('movieid'):
                    mapped_movie_path = self.remapPath(movie.get('file', ''))
                    state_snapshot = self.get_media_bookmark("movie", movie.get('movieid'))

                    if not xbmcvfs.exists(mapped_movie_path) or master.get('file','-1') == movie.get('file'):
                        if self.executeRemoveMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Missing or Shadow)"):
                            self.restore_media_bookmark("movie", master.get('file'), state_snapshot)
                    elif master.get('file','-1') != movie.get('file'):
                        if self.executeRemoveMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Physical Duplicate)"):
                            self.executeTrashFile(mapped_movie_path)
                            self.restore_media_bookmark("movie", master.get('file'), state_snapshot)
                            
            if pDialog: pDialog.close()
            self.log('cleanMovies, finished!')
            return True
        except Exception as e:
            if 'pDialog' in locals() and pDialog: pDialog.close()
            self.log('cleanMovies, failed! %s'%(e), xbmc.LOGERROR)
            return False

    def refreshMovies(self, movies=[], clean=None, ignore=None):
        if clean is None: clean = REAL_SETTINGS.getSettingBool('Refresh_Clean')
        if ignoreNFO is None: ignoreNFO = REAL_SETTINGS.getSettingBool('Refresh_Ignore_NFO')
        self.log('refreshMovies, movies = %s, clean = %s, ignore = %s'%(len(movies),clean,ignore))
        if len(movies) > 0: random.shuffle(movies)
        for movie in movies:
            if self.monitor.waitForAbort(0.1): return False
            if clean: self.tasks.setdefault('cleanMovies',list()).extend(findMatch(movie.get('file'),movies))
            self.tasks.setdefault('refreshMovie',set()).add((movie.get('movieid'),ignore))
        return True

    def _verifyNetwork(self, path):
        if not path: return True
        root_share = None
        for proto in ['smb://', 'nfs://', 'ftp://', 'dav://', 'sftp://']:
            if path.lower().startswith(proto):
                parts = path.split('/')
                if   len(parts) >= 4: root_share = f"{parts[0]}//{parts[2]}/{parts[3]}/"
                elif len(parts) >= 3: root_share = f"{parts[0]}//{parts[2]}/"
                if root_share and not xbmcvfs.exists(root_share):
                    self.log("_verifyNetwork, Network mount root %s is offline! Aborting removal." % root_share, xbmc.LOGERROR)
                    return False
                break
        return True

    def get_stream_weight(self, file_path):
        weight = 0
        normalized = file_path.lower()
        if "2160p" in normalized or "4k" in normalized: weight += 50
        elif "1080p" in normalized: weight += 30
        elif "720p" in normalized: weight += 10
        if "remux" in normalized: weight += 20
        if "x265" in normalized or "hevc" in normalized: weight += 15
        if "x264" in normalized or "h264" in normalized: weight += 5
        if not normalized.startswith(('smb:', 'nfs:')): weight += 5
        return weight

    def get_media_bookmark(self, media_type, media_id):
        method = "VideoLibrary.GetEpisodeDetails" if media_type == "episode" else "VideoLibrary.GetMovieDetails"
        parkey = "episodeid" if media_type == "episode" else "movieid"
        try:
            result = sendJSON({"method": method, "params": {parkey: int(media_id), "properties": ["resume", "playcount"]}})
            if "result" in result:
                details = result["result"].get('%sdetails' % media_type, {})
                return {"resume": details.get("resume", {"position": 0.0, "total": 0.0}), "playcount": details.get("playcount", 0)}
        except Exception: pass
        return {}

    def restore_media_bookmark(self, media_type, file_path, state):
        if not state or "resume" not in state: return
        try:
            method  = "VideoLibrary.GetEpisodes" if media_type == "episode" else "VideoLibrary.GetMovies"
            results = sendJSON({"method": method_search, "params": {"properties": ["file"]}})
            details = results.get("result", {}).get("episodes" if media_type == "episode" else "movies", [])
            for item in details:
                if item.get('file') == file_path:
                    new_id = item.get('episodeid') if media_type == "episode" else item.get('movieid')
                    parmethod = "VideoLibrary.SetEpisodeDetails" if media_type == "episode" else "VideoLibrary.SetMovieDetails"
                    parkey    = "episodeid" if media_type == "episode" else "movieid"
                    sendJSON({"method": parmethod, "params": {parkey: int(new_id), "resume": state["resume"], "playcount": state["playcount"]}})
                    break
        except Exception: pass

    def runScraper(self):
        try:
            return (self.scrapeTV(REAL_SETTINGS.getSetting('Scraper_TV_Folder'), (self.getTVshows() or []),REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')) & 
                    self.scrapeMovies(REAL_SETTINGS.getSetting('Scraper_Movie_Folder'), (self.getMovies() or [])))
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
            return False

    def runRefresh(self):
        try:
            return (self.refreshTV((self.getTVshows()    or [])) & 
                    self.refreshMovies((self.getMovies() or [])))
        except Exception as e:
            self.log('runRefresh, Scan failed! %s'%(e), xbmc.LOGERROR)
            self.notification(LANGUAGE(32009))
            return False

    def runClean(self):
        ...
        # try: return (self.cleanTV([findDupes(self.getEpisodes(get 'tvshowid'))]) & self.cleanMovies([findMatch(get movie file,self.getMovies())]))
        # except Exception as e:
            # self.log('runClean, Scan failed! %s'%(e), xbmc.LOGERROR)
            # self.notification(LANGUAGE(32009))
            # return False

    def remapPath(self, path):
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

    def executeTrashFile(self, file_path):
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
        except Exception as e: self.log('executeTrashFile failed: %s' % str(e), xbmc.LOGERROR)
        return False
            
    def parseEpisodes(self, show={}, episodes=[]):
        self.log('parseEpisodes show = %s'%(show.get('tvshowid')))
        refresh   = [] 
        missing   = [] 
        abandoned = [] 
        
        if len(episodes) > 0: random.shuffle(episodes)
        for episode in episodes:
            if self.monitor.waitForAbort(0.1): break
            elif not episode.get('file'): continue
            
            dir_path = os.path.dirname(episode['file'])
            if dir_path not in self.directory_cache:
                self.directory_cache[dir_path] = {f.get('file'): f for f in (self.getDirectory(os.path.join(dir_path,'')) or []) if f.get('file')}
                
            items_dict = self.directory_cache[dir_path]
            mapped_ep_path = self.remapPath(episode['file'])
            if episode['file'] in items_dict:
                refresh.append(episode)
            else:
                if not xbmcvfs.exists(mapped_ep_path): 
                    abandoned.append(episode)
                else:
                    for f_path, item in items_dict.items():
                        if f_path != episode['file']:
                            missing.append(item)
        return {'refresh': refresh, 'missing': missing, 'abandoned': abandoned}

    def scrapeTV(self, path, shows=[], includeEpisodes=None):
        if includeEpisodes is None: includeEpisodes = REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')
        self.log('scrapeTV path = %s'%(path))
        items = dict([(show['file'],show) for show in shows if show.get('file')])
        files = (self.getDirectory(path) or [])
        if len(files) > 0: random.shuffle(files)
        for file in files:
            if   not file.get('file'): continue
            elif not file['file'] in items:
                self.tasks.setdefault('scrapeDirectory',set()).add(file['file'])
            elif not self.monitor.waitForAbort(0.1) and includeEpisodes:
                missing = self.parseEpisodes(items[file['file']],(self.getEpisodes(items[file['file']]['tvshowid']) or [])).get('missing',[])
                if len(missing) > 0: 
                    random.shuffle(missing)
                    for episode in missing:
                        self.tasks.setdefault('scrapeDirectory',set()).add(episode['file'])
        return True

    def scrapeMovies(self, path, movies=[]):
        self.log('scrapeMovies, path = %s'%(path))
        paths = dict([(os.path.split(item['file'])[0],item) for item in movies if item.get('file')])
        items = (self.getDirectory(path) or [])
        if len(items) > 0: random.shuffle(items)
        for item in items:
            if not item.get('file') in paths:
                self.tasks.setdefault('scrapeDirectory',set()).add(item.get('file'))
        return True

if __name__ == '__main__': Service()._start()