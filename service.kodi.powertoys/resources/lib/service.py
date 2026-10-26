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
from zeroconf import Zeroconf, ServiceBrowser
from texture import prune, recache_missing, cache_stats, format_size
from webserver import start_server as startWebServer, stop_server as stopWebServer
import socket, urllib.request, threading, gc, ctypes

class Player(xbmc.Player):
    def __init__(self, monitor=None):
        super(Player, self).__init__()
        self.monitor = monitor
        self.service = monitor.service if monitor else None
        self.playingItem = {'listitem':xbmcgui.ListItem()}
        self._playingDB = {}
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    def isPseudoTV(self):
        try:
            sys_info = self.getPlayerItem().getProperty('sysInfo')
            if not sys_info: return False
            return '@%s'%(slugify(ADDON_NAME)) in loadJSON(decodeString(sys_info)).get('chid','')
        except:
            return False

    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        if self.service and not REAL_SETTINGS.getSettingBool('Run_Playing'):
            self.service._playing = True

    def onAVStarted(self):
        self.playingItem = {'listitem':self.getPlayerItem(), 'elapsed':self.getPlayedTime(), 'totaltime':self.getPlayerTime()}
        try:
            # capture library identity while VideoPlayer.* labels are valid (watched-state sync)
            self._playingDB = {'dbtype': xbmc.getInfoLabel('VideoPlayer.DBType') or '',
                               'dbid': int(xbmc.getInfoLabel('VideoPlayer.DBID') or '0'),
                               'file': self.getPlayerItem().getPath() or xbmc.getInfoLabel('VideoPlayer.Filename') or ''}
        except Exception:
            self._playingDB = {}
        self.log('onAVStarted, playingItem = %s'%(self.playingItem))

    def onPlayBackError(self):
        self.log('onPlayBackError')
        self._pushWatchedState()
        self.playingItem = self.onStop(self.playingItem)
        if self.service:
            self.service._playing = False
        
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        self._pushWatchedState()
        self.playingItem = self.onStop(self.playingItem)
        if self.service:
            self.service._playing = False
        
    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        self._pushWatchedState()
        self.playingItem = self.onStop(self.playingItem)
        if self.service:
            self.service._playing = False

    def _pushWatchedState(self):
        # after playback, push fresh playcount/lastplayed/resume to peers via the sync outbox
        db, self._playingDB = self._playingDB, {}
        if not self.service or not db or db.get('dbtype') not in ('movie', 'episode') or not db.get('dbid'):
            return
        try:
            method, key = (('VideoLibrary.GetMovieDetails', 'movieid') if db['dbtype'] == 'movie'
                           else ('VideoLibrary.GetEpisodeDetails', 'episodeid'))
            d = sendJSON({"method": method, "params": {key: db['dbid'],
                          "properties": ["playcount", "lastplayed", "resume", "file"]}}).get('result', {})
            d = d.get('movie') or d.get('episode') or {}
            f = d.get('file') or db.get('file')
            if f and self.service.sync:
                self.service.sync.queue_msg('WatchedUpdate', {'items': {f: {
                    'playcount': d.get('playcount', 0),
                    'lastplayed': d.get('lastplayed'),
                    'resume': d.get('resume')}}})
        except Exception as e:
            self.log('_pushWatchedState: %s' % e, xbmc.LOGWARNING)

    def onStop(self, playingItem={}):
        self.log('onStop, playingItem = %s'%(self.playingItem))
        return {'listitem':xbmcgui.ListItem()}

    def getPlayerItem(self):
        try: return self.getPlayingItem()
        except:
            if self.isPlaying(): return self.getPlayerItem()
            else:                return xbmcgui.ListItem()

    def getPlayerTime(self):
        try:    return (self.getTimeLabel('Duration') or self.getTotalTime())
        except: return (self.getPlayerItem().getProperty('runtime') or -1)
            
    def getPlayedTime(self):
        try:    return (self.getTimeLabel('Time') or self.getTime())
        except: return -1
            
    def getRemainingTime(self):
        try:    return self.getPlayerTime() - self.getPlayedTime()
        except: return (self.getTimeLabel('TimeRemaining') or -1)

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
            if sender == ADDON_ID and method.endswith(".RefreshLibrary"):
                self.log("Peer refresh signal received")
                xbmc.executebuiltin("Container.Refresh")
                self._confirm(data, "RefreshConfirmed")
            if sender == ADDON_ID and method.endswith(".RefreshConfirmed"):
                self.log("Peer refresh confirmed")
                if self.service and hasattr(self.service, 'sync'):
                    self.service.sync.on_confirm(data)
            if sender == ADDON_ID and method.endswith(".SyncConfirmed"):
                self.log("Peer sync confirmed")
                if self.service and hasattr(self.service, 'sync'):
                    self.service.sync.on_confirm(data)
            if sender == ADDON_ID and method.endswith(".ScanLibrary"):
                self._handle_peer_scan(data)
            if sender == ADDON_ID and method.endswith(".WatchedUpdate"):
                self._handle_peer_watched(data)
            if method == "VideoLibrary.OnScanFinished" and REAL_SETTINGS.getSettingBool('Clean_OnScanFinished'):
                self.log("Event Intercept -> Library Scan Finished. Injecting optimization pass.")
                self.service._que(self.service.runClean, priority=5)
            if method in ["VideoLibrary.OnUpdate", "VideoLibrary.OnScanStarted"]:
                if hasattr(self.service, '_cache'):
                    self.service._cache.clear()
            if method == "VideoLibrary.OnUpdate" and hasattr(self.service, '_onLibraryUpdate'):
                self.service._onLibraryUpdate(method, data)
            if method == "VideoLibrary.OnScanFinished":
                if self.service and hasattr(self.service, 'sync'):
                    self.service.sync.broadcast_refresh()
            if method == "VideoLibrary.OnScanError" and REAL_SETTINGS.getSettingBool('Scan_Retry_On_Error'):
                now = time.time()
                if self.service and not self.service.isRunning and (now - self.service._lastScanRetry) > 3600:
                    self.service._lastScanRetry = now
                    self.log('Scan error detected, re-queuing scraper (cooldown 1h)', xbmc.LOGWARNING)
                    self.service._que(self.service.runScraper, 2)
            if sender == ADDON_ID and method.endswith(".HealthReport"):
                if self.service: threading.Thread(target=self.service.healthReport, daemon=True).start()
            if sender == ADDON_ID and method.endswith(".RunScraper"):
                if self.service:
                    if hasattr(self.service, 'sync'): self.service.sync.queue_msg('ScanLibrary', {'path': None})
                    if REAL_SETTINGS.getSettingBool('Scraper_Enabled') and not self.service.isRunning:
                        self.service._que(self.service.runScraper, 2)
            if sender == ADDON_ID and method.endswith(".RunRefresh"):
                if self.service and REAL_SETTINGS.getSettingBool('Refresh_Enabled'):
                    self.service._que(self.service.runRefresh, 2)
            if sender == ADDON_ID and method.endswith(".RunClean"):
                if self.service: self.service._que(self.service.runClean, 3)
            if sender == ADDON_ID and method.endswith(".RunTexture"):
                if self.service and REAL_SETTINGS.getSettingBool('Texture_Enabled'):
                    self.service._que(self.service.runTexture, 3)
            if sender == ADDON_ID and method.endswith(".RunBackup"):
                if self.service and REAL_SETTINGS.getSettingBool('Backup_Enabled'):
                    self.service._que(self.service.runBackup, 3)
            if sender == ADDON_ID and method.endswith(".RunMusic"):
                if self.service and REAL_SETTINGS.getSettingBool('Music_Enabled'):
                    self.service._que(self.service.runMusic, 3)
            if sender == ADDON_ID and method.endswith(".RunCacheClean"):
                if self.service: threading.Thread(target=self.service.runCacheClean, daemon=True).start()
            if sender == ADDON_ID and method.endswith(".RunFreeRam"):
                if self.service: self.service._que(self.service.runRamFree, 3)
            if sender == ADDON_ID and method.endswith(".CleanTVShow"):
                try:
                    tvshowid = int((json.loads(data) if isinstance(data, str) else (data or {})).get('tvshowid', -1))
                    if tvshowid >= 0 and self.service: self.service._que(self.service.cleanTV, 3, tvshowid)
                except Exception as e: self.log('CleanTVShow error: %s' % e, xbmc.LOGWARNING)
            if sender == ADDON_ID and method.endswith(".CleanMovie"):
                try:
                    payload = json.loads(data) if isinstance(data, str) else (data or {})
                    movieid = int(payload.get('movieid', -1))
                    if movieid >= 0 and self.service:
                        movies = [m for m in (self.service.getMovies() or []) if m.get('movieid') == movieid]
                        if movies:
                            group = next((g for g in self.service._movieDuplicateGroups(self.service.getMovies() or []) if any(m.get('movieid') == movieid for m in g)), movies)
                            self.service._que(self.service.cleanMovies, 3, group)
                except Exception as e: self.log('CleanMovie error: %s' % e, xbmc.LOGWARNING)
            if sender == ADDON_ID and method.endswith(".CleanSeason"):
                try:
                    payload = json.loads(data) if isinstance(data, str) else (data or {})
                    tvshowid, season = int(payload.get('tvshowid', -1)), int(payload.get('season', -99))
                    if tvshowid >= 0 and season > -99 and self.service: self.service._que(self.service.cleanSeason, 3, tvshowid, season)
                except Exception as e: self.log('CleanSeason error: %s' % e, xbmc.LOGWARNING)
            if sender == ADDON_ID and method.endswith(".WatchSeason"):
                try:
                    payload = json.loads(data) if isinstance(data, str) else (data or {})
                    tvshowid, season, watched = int(payload.get('tvshowid', -1)), int(payload.get('season', -99)), bool(payload.get('watched', True))
                    if tvshowid >= 0 and season > -99 and self.service: self.service._que(self.service.markWatched, 3, tvshowid, season, watched)
                except Exception as e: self.log('WatchSeason error: %s' % e, xbmc.LOGWARNING)
            if sender == ADDON_ID and method.endswith(".WatchShow"):
                try:
                    payload = json.loads(data) if isinstance(data, str) else (data or {})
                    tvshowid, watched = int(payload.get('tvshowid', -1)), bool(payload.get('watched', True))
                    if tvshowid >= 0 and self.service: self.service._que(self.service.markWatched, 3, tvshowid, None, watched)
                except Exception as e: self.log('WatchShow error: %s' % e, xbmc.LOGWARNING)
            if sender == ADDON_ID and method.endswith(".ScanFolder"):
                try:
                    payload = json.loads(data) if isinstance(data, str) else (data or {})
                    path = payload.get('path')
                    if path and self.service:
                        if hasattr(self.service, 'sync'): self.service.sync.queue_msg('ScanLibrary', {'path': path})
                        self.service._que(self.service.scrapeDirectory, 2, path)
                except Exception as e: self.log('ScanFolder error: %s' % e, xbmc.LOGWARNING)

    def _peerTokenSeen(self, token):
        # shared re-ack-no-requeue LRU for peer push tokens (safe resends if acks get lost)
        if not token: return False
        if not getattr(self.service, '_peerTokens', None): self.service._peerTokens = {}
        now = time.time()
        for t, ts in list(self.service._peerTokens.items()):
            if now - ts > 600: self.service._peerTokens.pop(t, None)
        if token in self.service._peerTokens: return True
        self.service._peerTokens[token] = now
        return False

    def _handle_peer_scan(self, data):
        try:
            payload = json.loads(data) if isinstance(data, str) else (data or {})
            token, path = payload.get('token'), payload.get('path')
            if not self.service: return
            if self._peerTokenSeen(token):
                self._confirm(data, "SyncConfirmed"); return
            if path:
                self.log('Peer scan received (path): %s' % path)
                self.service._que(self.service.scrapeDirectory, 2, path)
            elif REAL_SETTINGS.getSettingBool('Scraper_Enabled') and not self.service.isRunning:
                self.log('Peer scan received (full)')
                self.service._que(self.service.runScraper, 2)
            if token: self._confirm(data, "SyncConfirmed")
        except Exception as e:
            self.log('ScanLibrary error: %s' % e, xbmc.LOGWARNING)

    def _handle_peer_watched(self, data):
        try:
            payload = json.loads(data) if isinstance(data, str) else (data or {})
            token = payload.get('token')
            if not self.service: return
            if self._peerTokenSeen(token):
                self._confirm(data, "SyncConfirmed"); return
            items = payload.get('items') or {}
            if items: self.service._suppressWatchPush = time.time() + 2  # suppress echo before applying
            applied = 0
            for f, st in items.items():
                try:
                    # newest-lastplayed-wins: skip only when both sides have lastplayed and local is strictly newer
                    local_lp = sendJSON({"method":"Files.GetFileDetails","params":{"file":f,"media":"video",
                                        "properties":["lastplayed"]}}).get('result',{}).get('filedetails',{}).get('lastplayed')
                    inc_lp = st.get('lastplayed')
                    if local_lp and inc_lp and str(local_lp) > str(inc_lp):
                        self.log('WatchedUpdate: local lastplayed newer, skipping %s' % f)
                        continue
                    params = {"file": f, "media": "video",
                              "playcount": st.get('playcount', 0),
                              "lastplayed": st.get('lastplayed'),
                              "resume": st.get('resume')}
                    if sendJSON({"method":"Files.SetFileDetails","params":params}).get('result') == 'OK':
                        applied += 1
                except Exception as fe:
                    self.log('WatchedUpdate item failed (%s): %s' % (f, fe), xbmc.LOGWARNING)
            if applied: self.log('WatchedUpdate: applied %d/%d from peer' % (applied, len(items)))
            if token: self._confirm(data, "SyncConfirmed")
        except Exception as e:
            self.log('WatchedUpdate error: %s' % e, xbmc.LOGWARNING)

    def _confirm(self, data, message="RefreshConfirmed"):
        try:
            payload = json.loads(data) if isinstance(data, str) else (data or {})
            cb_ip, cb_port, token = payload.get('ip'), payload.get('port'), payload.get('token')
            if not (cb_ip and token): return
            confirm = {"jsonrpc":"2.0","method":"JSONRPC.NotifyAll",
                       "params":{"sender":ADDON_ID,"message":message,"data":{"token":token}},
                       "id":"kodi.powertoys.sync"}
            url = 'http://%s:%d/jsonrpc' % (cb_ip, cb_port or 8080)
            req = urllib.request.Request(url, data=json.dumps(confirm).encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(req, timeout=5)
            self.log('Confirmed (%s) to %s:%s' % (message, cb_ip, cb_port))
        except Exception as e:
            self.log('Failed to confirm %s: %s' % (message, e), xbmc.LOGWARNING)

class SyncManager:
    SERVICE_TYPE = "_xbmc-jsonrpc-h._tcp.local."
    DEBOUNCE_SECONDS = 5
    CONFIRM_TIMEOUT = 15
    MAX_RETRIES = 3

    def __init__(self, service=None):
        self.log('SyncManager.__init__')
        self.service = service
        self.zeroconf = None
        self.browser = None
        self.peers = {}
        self._known_peers = {}   # session roster, survives removeService
        self._entries = []       # durable outbox: [{id, msg, payload, ts, targets:{name:{ip,port,fails,next,sent_ts,token,delivered}}}]
        self._seq = 0
        self._sweeper_stop = threading.Event()
        self._last_broadcast = 0
        self._lock = threading.Lock()
        self._local_ip = self._get_local_ip()
        self._pending = {}   # token -> {peer, ip, port, ts, retries} (refresh confirm path)
        self._token = 0

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('SyncManager: %s' % msg, level)

    def start(self):
        if not REAL_SETTINGS.getSettingBool('Sync_Enabled') and not REAL_SETTINGS.getSettingBool('WebServer_Enabled'):
            self.log('Sync_Enabled and WebServer_Enabled are False, not starting')
            return
        self.log('Starting')
        self._load_outbox()
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(self.zeroconf, self.SERVICE_TYPE, self)
        self._sweeper_stop.clear()
        threading.Thread(target=self._sweep_loop, name='%s.sweeper' % ADDON_ID, daemon=True).start()

    def stop(self):
        self.log('Stopping')
        self._sweeper_stop.set()
        if self.browser:
            self.browser.cancel()
        if self.zeroconf:
            self.zeroconf.close()
        self.save_outbox()

    def addService(self, zeroconf, service_type, name):
        try:
            info = zeroconf.getServiceInfo(service_type, name)
            if not info or not info.getAddress():
                return
            ip = socket.inet_ntoa(info.getAddress())
            if ip == self._local_ip:
                self.log('Skipping self: %s' % ip)
                return
            with self._lock:
                if name not in self.peers:
                    self.log('New peer: %s:%d (%s)' % (ip, info.getPort(), info.getServer()))
                self.peers[name] = {"ip": ip, "host": info.getServer(), "port": info.getPort()}
                self._known_peers[name] = {"ip": ip, "host": info.getServer(), "port": info.getPort()}
                # peer (re)appeared: refresh any outbox targets, reset backoff, sweep now
                woken = False
                for e in self._entries:
                    t = e['targets'].get(name)
                    if t and not t['delivered']:
                        t['ip'], t['port'] = ip, info.getPort()
                        t['fails'], t['next'], t['sent_ts'] = 0, 0, None
                        woken = True
            if woken:
                self.log('Peer %s returned, retrying pending sync entries' % name)
                threading.Thread(target=self._sweep, daemon=True).start()
        except Exception as e:
            self.log('addService error: %s' % e, xbmc.LOGWARNING)

    def removeService(self, zeroconf, service_type, name):
        with self._lock:
            self.peers.pop(name, None)  # keep _known_peers roster for durable retries

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    @property
    def _local_web_port(self):
        try:
            return sendJSON({"method":"Settings.GetSettingValue","params":{"setting":"services.webserverport"}}).get('result',{}).get('value', 8080)
        except Exception:
            return 8080

    # ── durable outbox (ScanLibrary / WatchedUpdate) ────────────────────
    def queue_msg(self, msg, payload):
        if not REAL_SETTINGS.getSettingBool('Sync_Enabled'):
            return
        new_entry = True
        with self._lock:
            if msg == 'ScanLibrary':
                path = (payload or {}).get('path')
                for e in self._entries:
                    if e['msg'] == msg and (e['payload'] or {}).get('path') == path and any(not t['delivered'] for t in e['targets'].values()):
                        return  # exact duplicate still pending
            elif msg == 'WatchedUpdate':
                # batch merge: fold into the pending entry; new eid + reset targets so the
                # union is (re)sent under fresh tokens - applies are idempotent, stale acks no-op
                for e in self._entries:
                    if e['msg'] == msg and any(not t['delivered'] for t in e['targets'].values()):
                        e['payload'].setdefault('items', {}).update((payload or {}).get('items') or {})
                        self._seq += 1
                        e['id'] = self._seq
                        for name, t in e['targets'].items():
                            t.update({'token': 'sync:%d:%s' % (e['id'], name), 'sent_ts': None,
                                      'next': 0, 'fails': 0, 'delivered': False})
                        new_entry = False
                        break
            if new_entry:
                if not self._known_peers:
                    self.log('queue_msg: no known peers, dropping %s %s' % (msg, payload), xbmc.LOGDEBUG)
                    return
                self._seq += 1
                eid = self._seq
                targets = {}
                for name, peer in self._known_peers.items():
                    token = 'sync:%d:%s' % (eid, name)
                    targets[name] = {'ip': peer['ip'], 'port': peer['port'], 'fails': 0, 'next': 0, 'sent_ts': None, 'token': token, 'delivered': False}
                self._entries.append({'id': eid, 'msg': msg, 'payload': payload, 'ts': time.time(), 'targets': targets})
                while len(self._entries) > 50:  # ponytail: FIFO cap, oldest undelivered shed first
                    self._entries.pop(0)
                self.log('Queued %s to %d peers (payload=%s)' % (msg, len(targets), payload))
        self.save_outbox()
        threading.Thread(target=self._sweep, daemon=True).start()

    def _sweep_loop(self):
        while not self._sweeper_stop.is_set() and not (self.service and self.service.monitor.abortRequested()):
            if self._sweeper_stop.wait(15): break
            try:
                if REAL_SETTINGS.getSettingBool('Sync_Enabled'):
                    self._sweep()
            except Exception as e:
                self.log('sweep error: %s' % e, xbmc.LOGWARNING)

    def _sweep(self):
        now = time.time()
        if not REAL_SETTINGS.getSettingBool('Sync_Enabled'):
            return
        with self._lock:
            entries = list(self._entries)
        done = False
        for e in entries:
            all_done = True
            for name, t in list(e['targets'].items()):
                if t['delivered']:
                    continue
                all_done = False
                if now < t['next']:
                    continue
                if t['sent_ts'] and now - t['sent_ts'] <= self.CONFIRM_TIMEOUT:
                    continue  # awaiting ack
                if t['sent_ts']:  # ack timed out -> resend with backoff
                    t['fails'] += 1
                    t['next'] = now + min(15 * (2 ** min(t['fails'], 6)), 900)
                    t['sent_ts'] = None
                    self.log('No ack from %s for entry %d, retry %d in %ds' % (name, e['id'], t['fails'], int(t['next'] - now)))
                threading.Thread(target=self._deliver, args=(e['id'], e['msg'], e['payload'], name, t), daemon=True).start()
            if all_done and e['targets']:
                with self._lock:
                    if e in self._entries:
                        self._entries.remove(e)
                        done = True
                self.log('Entry %d (%s) fully delivered, dropping' % (e['id'], e['msg']))
        if done:
            self.save_outbox()

    def _deliver(self, eid, msg, payload, name, t):
        try:
            data = dict(payload or {})
            data.update({'ip': self._local_ip, 'port': self._local_web_port, 'token': t['token']})
            cmd = {"jsonrpc":"2.0","method":"JSONRPC.NotifyAll",
                   "params":{"sender":ADDON_ID,"message":msg,"data":data},
                   "id":"kodi.powertoys.sync"}
            url = 'http://%s:%d/jsonrpc' % (t['ip'], t['port'])
            req = urllib.request.Request(url, data=json.dumps(cmd).encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(req, timeout=5)
            with self._lock:
                t['sent_ts'] = time.time()
            self.log('%s sent to %s:%s, awaiting confirm (token %s)' % (msg, t['ip'], t['port'], t['token']))
        except Exception as e:
            with self._lock:
                t['fails'] += 1
                t['next'] = time.time() + min(15 * (2 ** min(t['fails'], 6)), 900)
                t['sent_ts'] = None
            self.log('Deliver %s to %s failed: %s' % (msg, name, e), xbmc.LOGWARNING)
            if t['fails'] == 1:  # first failure -> peer may be asleep, try waking it once per entry
                threading.Thread(target=self._wake_once, daemon=True).start()

    def _wake_once(self):
        now = time.time()
        with self._lock:
            if now - getattr(self, '_last_wake', 0) < 60:
                return
            self._last_wake = now
        self.wake_peers()

    def on_confirm(self, data):
        try:
            payload = json.loads(data) if isinstance(data, str) else (data or {})
            token = payload.get('token')
            with self._lock:
                entry = self._pending.pop(token, None)  # legacy refresh confirm path
                if not entry:
                    for e in self._entries:
                        t = e['targets'].get(token.split(':', 2)[-1]) if token and token.startswith('sync:') else None
                        if t and t['token'] == token:
                            t['delivered'] = True
                            t['sent_ts'] = None
                            self.log('Confirmed %s entry %d by %s' % (e['msg'], e['id'], token.split(':', 2)[-1]))
                            break
            if entry:
                self.log('Refresh confirmed by %s (%s:%d)' % (entry['peer'], entry['ip'], entry['port']))
        except Exception as e:
            self.log('on_confirm error: %s' % e, xbmc.LOGWARNING)

    def save_outbox(self):
        try:
            if not self.service: return
            with self._lock:
                slim = [{'id': e['id'], 'msg': e['msg'], 'payload': e['payload'], 'ts': e['ts'],
                         'targets': {n: {'ip': t['ip'], 'port': t['port'], 'token': t['token']} for n, t in e['targets'].items() if not t['delivered']}}
                        for e in self._entries]
                slim = [e for e in slim if e['targets']]
            self.service.cache.set('syncoutbox', json.dumps(slim), ADDON_VERSION, json_data=True)
        except Exception as e:
            self.log('save_outbox error: %s' % e, xbmc.LOGWARNING)

    def _load_outbox(self):
        try:
            if not self.service: return
            raw = self.service.cache.get('syncoutbox', checksum=ADDON_VERSION, json_data=True)
            if isinstance(raw, str): raw = json.loads(raw)
            for e in (raw or []):
                targets = {n: dict(t, fails=0, next=0, sent_ts=None, delivered=False) for n, t in (e.get('targets') or {}).items()}
                if targets:
                    self._entries.append({'id': e['id'], 'msg': e['msg'], 'payload': e.get('payload'), 'ts': e.get('ts', time.time()), 'targets': targets})
                    self._seq = max(self._seq, e['id'])
            if self._entries:
                self.log('Restored %d undelivered sync entries' % len(self._entries))
        except Exception as e:
            self.log('_load_outbox error: %s' % e, xbmc.LOGWARNING)

    def broadcast_refresh(self):
        if not REAL_SETTINGS.getSettingBool('Sync_Enabled'):
            return
        now = time.time()
        if now - self._last_broadcast < self.DEBOUNCE_SECONDS:
            self.log('Debounce: skipping refresh (last broadcast %.1fs ago)' % (now - self._last_broadcast))
            return
        self._last_broadcast = now
        self._retry_stale()
        self.log('Broadcasting refresh to %d peers (%d pending)' % (len(self.peers), len(self._pending)))
        threading.Thread(target=self._broadcast_loop, daemon=True).start()

    def wake_peers(self):
        # Wake-on-LAN: broadcast magic packets for every configured MAC (stdlib only)
        macs = [m.strip() for m in (REAL_SETTINGS.getSetting('Sync_Wake_MACs') or '').replace(';', ',').split(',') if m.strip()]
        if not macs:
            self.log('wake_peers: no MACs configured', xbmc.LOGDEBUG)
            return 0
        sent = 0
        for mac in macs:
            try:
                raw = bytes.fromhex(mac.replace(':', '').replace('-', ''))
                if len(raw) != 6: continue
                pkt = b'\xff' * 6 + raw * 16
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(pkt, ('255.255.255.255', 9))
                s.close()
                sent += 1
                self.log('WOL magic packet sent for %s' % mac)
            except Exception as e:
                self.log('WOL failed for %s: %s' % (mac, e), xbmc.LOGWARNING)
        return sent

    def _broadcast_loop(self):
        for name, peer in list(self.peers.items()):
            if name in self._pending: continue
            self._send_refresh(name, peer['ip'], peer['port'])

    def _send_refresh(self, name, ip, port):
        self._token += 1
        token = '%s:%d:%d' % (ip, port, self._token)
        try:
            cmd = {"jsonrpc":"2.0","method":"JSONRPC.NotifyAll",
                   "params":{"sender":ADDON_ID,"message":"RefreshLibrary",
                             "data":{"ip":self._local_ip,"port":self._local_web_port,"token":token}},
                   "id":"kodi.powertoys.sync"}
            url = 'http://%s:%d/jsonrpc' % (ip, port)
            req = urllib.request.Request(url, data=json.dumps(cmd).encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            response = urllib.request.urlopen(req, timeout=5)
            with self._lock:
                self._pending[token] = {'peer':name,'ip':ip,'port':port,'ts':time.time(),'retries':0}
            self.log('Refresh sent to %s:%d, awaiting confirm (token %s)' % (ip, port, token))
        except Exception as e:
            self.log('Failed to send refresh to %s:%d: %s' % (ip, port, e), xbmc.LOGWARNING)
            with self._lock:
                self._pending[token] = {'peer':name,'ip':ip,'port':port,'ts':time.time(),'retries':1}

    def _retry_stale(self):
        now = time.time()
        with self._lock:
            stale = [t for t, e in self._pending.items() if now - e['ts'] > self.CONFIRM_TIMEOUT]
        for token in stale:
            with self._lock:
                entry = self._pending.pop(token, None)
            if not entry: continue
            if entry['retries'] >= self.MAX_RETRIES:
                self.log('Giving up on %s after %d retries' % (entry['peer'], entry['retries']))
            else:
                self.log('Retrying %s (attempt %d)' % (entry['peer'], entry['retries']+1))
                self._send_refresh(entry['peer'], entry['ip'], entry['port'])

class Service(object):
    cache = SimpleCache()
    cache.enable_mem_cache = False
    
    def __init__(self):
        self.isRunning  = False
        self._playing   = False
        self.monitor  = Monitor(self)
        self.player   = self.monitor.player
        self.queue    = CustomQueue(service=self)
        self.sync     = SyncManager(self)
        self.pid      = "%s_%s" % (platform.node(), os.getpid())
        self.wait     = REAL_SETTINGS.getSettingInt('Start_Delay')
        self._cache   = {}
        self._tasks   = self._load()
        self._warned  = set()
        self._lastScanRetry = 0
        self._peerTokens = {}
        self._shareState = {}
        self._lastShareCheck = 0
        self._suppressWatchPush = 0  # deadline; set when applying a remote watched update

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
        

    def _que(self, func, priority=3, *args, **kwargs):
        self.log('_que, priority = %s, func = %s, args = %s, kwargs = %s' % (priority,func.__name__, args, kwargs))
        self.queue.push((func, args, kwargs), priority)

    def _start(self):
        self.log('_start, wait = %s'%(self.wait))
        self.monitor.waitForAbort(self.wait)
        self._detectSources()
        self.sync.start()
        if REAL_SETTINGS.getSettingBool('WebServer_Enabled'):
            startWebServer(self)
        while not self.monitor.abortRequested():
            if    self.monitor.waitForAbort(5.0): break
            else: self._run()
        stopWebServer()
        self.sync.stop()
        self._save()

    def _detectSources(self):
        if REAL_SETTINGS.getSetting('Scraper_TV_Folder') and REAL_SETTINGS.getSetting('Scraper_Movie_Folder'): return
        sources = sendJSON({"method":"Files.GetSources","params":{"media":"video"}}).get('result',{}).get('sources',[])
        self.log('_detectSources, kodi video sources = %s' % [(s.get('label'),s.get('file')) for s in sources])
        tv_kw, movie_kw = ('tv','show','series','season'), ('movie','film')
        for src in sources:
            label = (src.get('label') or '').lower()
            path  = (src.get('file')  or '').lower()
            text  = '%s %s' % (label, path)
            if not REAL_SETTINGS.getSetting('Scraper_TV_Folder') and any(k in text for k in tv_kw) and not any(k in text for k in movie_kw):
                REAL_SETTINGS.setSetting('Scraper_TV_Folder', src.get('file',''))
                self.log('_detectSources, set TV source: %s' % src.get('file'))
            elif not REAL_SETTINGS.getSetting('Scraper_Movie_Folder') and any(k in text for k in movie_kw) and not any(k in text for k in tv_kw):
                REAL_SETTINGS.setSetting('Scraper_Movie_Folder', src.get('file',''))
                self.log('_detectSources, set movie source: %s' % src.get('file'))

    def _save(self):
        for func_name, args in self.queue.snapshot():
            if   func_name == 'scrapeDirectory': self._tasks.setdefault('scrapeDirectory',set()).add(args[0])
            elif func_name == 'cleanTV':         self._tasks.setdefault('cleanTV',set()).add(args[0])
            elif func_name == 'cleanMovies':     self._tasks.setdefault('cleanMovies',list()).append(args[0])
            elif func_name == 'refreshTVshow':   self._tasks.setdefault('refreshTVshow',set()).add(tuple(args))
            elif func_name == 'refreshMovie':    self._tasks.setdefault('refreshMovie',set()).add(tuple(args))
        self.log('_save tasks = %s'%(dict([(key,len(value)) for key, value in list(self._tasks.items())])))
        _tasks = {}
        for k, v in list(self._tasks.items()): _tasks[k] = list(v)
        self.cache.set('tasks', json.dumps(_tasks, default=list), checksum=ADDON_VERSION, expiration=datetime.timedelta(days=28), json_data=True)
            
    def _chkIdle(self):
        if REAL_SETTINGS.getSettingBool('Run_Idling'): return int(xbmc.getGlobalIdleTime() or '0') > self.wait
        return True
        
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
                    self.cache.set(func.__name__, (epoch + runevery), checksum=ADDON_VERSION, expiration=datetime.timedelta(days=28))
        yield
         
    def _pauseWhilePlaying(self):
        if not self._playing: return True
        self.log('_pauseWhilePlaying, playback started - holding...')
        while self._playing and not self.monitor.abortRequested():
            if self.monitor.waitForAbort(5.0): return False
        self.log('_pauseWhilePlaying, playback stopped - resuming...')
        return True

    def _onLibraryUpdate(self, method, data):
        # manual mark-watched (context/skin) -> push fresh state; suppressed right after
        # we ourselves applied a remote update (breaks A->B->A ping-pong)
        try:
            if not REAL_SETTINGS.getSettingBool('Sync_Enabled'): return
            if time.time() < self._suppressWatchPush: return
            if isScanning(): return  # scan-driven adds aren't watched changes
            payload = json.loads(data) if isinstance(data, str) else (data or {})
            changed = payload.get('changedfields')
            if changed is not None and not any(('playcount' in str(c) or 'lastplayed' in str(c) or 'resume' in str(c)) for c in changed):
                return
            item = payload.get('item') or {}
            dbtype, dbid = item.get('type'), item.get('id')
            if dbtype not in ('movie', 'episode') or not dbid: return
            method, key = (('VideoLibrary.GetMovieDetails', 'movieid') if dbtype == 'movie'
                           else ('VideoLibrary.GetEpisodeDetails', 'episodeid'))
            d = sendJSON({"method": method, "params": {key: dbid,
                          "properties": ["playcount", "lastplayed", "resume", "file"]}}).get('result', {})
            d = d.get('movie') or d.get('episode') or {}
            f = d.get('file')
            if f:
                self.sync.queue_msg('WatchedUpdate', {'items': {f: {
                    'playcount': d.get('playcount', 0),
                    'lastplayed': d.get('lastplayed'),
                    'resume': d.get('resume')}}})
        except Exception as e:
            self.log('_onLibraryUpdate: %s' % e, xbmc.LOGWARNING)

    def _run(self):
        self._watchShares()
        if isScanning():
            return
        if not self._chkIdle():
            return
        if self._tasks.get('scrapeDirectory'):
            while self._tasks.get('scrapeDirectory'):
                self._que(self.scrapeDirectory, 2, self._tasks.get('scrapeDirectory').pop())
        elif self._tasks.get('cleanTV'):
            while self._tasks.get('cleanTV'):
                self._que(self.cleanTV, 3, self._tasks.get('cleanTV').pop())
        elif self._tasks.get('cleanMovies'):
            while self._tasks.get('cleanMovies'):
                self._que(self.cleanMovies, 3, self._tasks.get('cleanMovies').pop(0))
        elif self._tasks.get('refreshTVshow'):
            while self._tasks.get('refreshTVshow'):
                self._que(self.refreshTVshow, 4, *self._tasks.get('refreshTVshow').pop())
        elif self._tasks.get('refreshMovie'):
            while self._tasks.get('refreshMovie'):
                self._que(self.refreshMovie, 4, *self._tasks.get('refreshMovie').pop())
        elif not self.isRunning:
            self.isRunning = True
            if REAL_SETTINGS.getSettingBool('Scraper_Enabled'):
                with self._chkUpdate(self.runScraper,REAL_SETTINGS.getSettingInt('Scraper_Interval_DAYS')): pass
            if REAL_SETTINGS.getSettingBool('Refresh_Enabled'):
                with self._chkUpdate(self.runRefresh,REAL_SETTINGS.getSettingInt('Refresh_Interval_DAYS')): pass
            if not self._playing and REAL_SETTINGS.getSettingBool('Backup_Enabled'):
                with self._chkUpdate(self.runBackup,REAL_SETTINGS.getSettingInt('Backup_Interval_DAYS')): pass
            if not self._playing and REAL_SETTINGS.getSettingBool('Texture_Enabled'):
                with self._chkUpdate(self.runTexture,REAL_SETTINGS.getSettingInt('Texture_Interval_DAYS')): pass
            if not self._playing and REAL_SETTINGS.getSettingBool('Music_Enabled'):
                with self._chkUpdate(self.runMusic,REAL_SETTINGS.getSettingInt('Music_Interval_DAYS')): pass
            if not self._playing and REAL_SETTINGS.getSettingBool('FreeRam_Enabled'):
                with self._chkUpdate(self.runRamFree, REAL_SETTINGS.getSettingInt('FreeRam_Interval_HOURS') / 24.0): pass
            self.isRunning = False
   
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
                elif self._playing: break
                elif isScanning(): self.log('scrapeDirectory, waiting for scraper to finish...')
                else: break
        self.log('scrapeDirectory, finished!')

    def runScraper(self):
        try:
            result = (self.scrapeTV(REAL_SETTINGS.getSetting('Scraper_TV_Folder')       , (self.getTVshows() or [])) & 
                    self.scrapeMovies(REAL_SETTINGS.getSetting('Scraper_Movie_Folder'), (self.getMovies()  or [])))
            if result: notification(LANGUAGE(32024))
            return result
        except Exception as e:
            self.log('runScraper, Scan failed! %s'%(e), xbmc.LOGERROR)
            notification(LANGUAGE(32009))
            return False

    def scrapeTV(self, path, shows=[], includeEpisodes=None):
        if not path or not xbmcvfs.exists(path):
            self.log('scrapeTV, path not accessible: %s' % path, xbmc.LOGWARNING)
            return False
        if includeEpisodes is None: includeEpisodes = REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')
        files = (self.getDirectory(path) or [])
        if len(files) > 0:
            self.log('scrapeTV path = %s, files = %s'%(path,len(files)))
            items = dict([(show['file'],show) for show in shows if show.get('file')])
            random.shuffle(files)
            for file in files:
                if   self.monitor.waitForAbort(0.01): return 
                elif file.get('file') and file.get('file') not in items: 
                    self._tasks.setdefault('scrapeDirectory',set()).add(file['file'])
        return True
        
    def scrapeMovies(self, path, movies=[]):
        if not path or not xbmcvfs.exists(path):
            self.log('scrapeMovies, path not accessible: %s' % path, xbmc.LOGWARNING)
            return False
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
        if episodes and self._excluded(episodes[0].get('showtitle')):
            self.log('cleanTV, excluded show: %s' % episodes[0].get('showtitle'))
            return True
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
            elif not self._pauseWhilePlaying(): return False
            elif not episode: continue
            elif not xbmcvfs.exists(episode.get('file', '')):
                self.log('cleanTV, episode file no longer exists: %s' % episode.get('file'))
                if pDialog: pDialog.update(percent, message="%s %s\nAbandoned: %s" % (message,episode.get('showtitle',tvshowid),episode.get('label', '')))
                self._removeEpisode(episode.get('episodeid'), episode.get('file'), "cleanTV (Missing File)")
            else:
                if episode.get('episode_key') in processed: continue
                shadow_copies = sorted(duplicates.get(episode.get('episode_key'),{}), key=lambda x: self.get_stream_weight(x.get('file', '')), reverse=True)
                if shadow_copies:
                    processed.add(episode.get('episode_key'))
                    self.log("cleanTV, episode = %s, shadow_copies = %s" % (episode.get('label'), len(shadow_copies)))
                    master_copy = shadow_copies.pop(0) #duplicate we want to keep weighted by quality keywords.
                    for sidx, shadow_copy in enumerate(shadow_copies):
                        if not shadow_copy: continue
                        elif self.monitor.waitForAbort(0.01): return False
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
        if self._excluded(movies[0].get('label')):
            self.log('cleanMovies, excluded movie: %s' % movies[0].get('label'))
            return True
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
                elif not self._pauseWhilePlaying(): return False
                elif not movie: continue
                elif not xbmcvfs.exists(movie.get('file')):
                    self.log('cleanMovies, movie file no longer exists: %s' % movie.get('file'))
                    if pDialog: pDialog.update(percent, message="%s\nAbandoned: %s" % (message,movie.get('label','')))
                    self._removeMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Missing File)")
                else:
                    if pDialog: pDialog.update(percent, message="Processing: %s" % movie.get('label', ''))
                    if master_copy.get('movieid',-1) != movie.get('movieid'):
                        if master_copy.get('file','-1') == movie.get('file','0'):
                            self.log('cleanMovies, duplicate shadow entry detected: %s' % master_copy.get('file'))
                            self._removeMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Shadow copy)")
                        else:
                            self.log('cleanMovies, physical duplicate detected: %s' % movie.get('file'))
                            self._removeMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Physical Duplicate)")
                            
        if pDialog: pDialog.close()
        return True
       
    def refreshTV(self, shows=[]):
        clean           = REAL_SETTINGS.getSettingBool('Refresh_Clean')
        ignoreNFO       = REAL_SETTINGS.getSettingBool('Refresh_Ignore_NFO')
        includeEpisodes = REAL_SETTINGS.getSettingBool('Refresh_Include_Episodes')
        artOnly         = REAL_SETTINGS.getSettingBool('Refresh_Art_Only')
        self.log('refreshTV shows = %s, clean = %s, ignoreNFO = %s, includeEpisodes = %s, artOnly = %s'%(len(shows),clean,ignoreNFO,includeEpisodes,artOnly))
        if len(shows) > 0: random.shuffle(shows)
        for show in shows:
            if   self.monitor.waitForAbort(0.01): return False
            elif artOnly and not self._needsRefresh(show): continue
            elif clean: self._tasks.setdefault('cleanTV',set()).add(show.get('tvshowid',-1))
            self._tasks.setdefault('refreshTVshow',set()).add((show.get('tvshowid'),ignoreNFO,includeEpisodes))
        return True

    def refreshMovies(self, movies=[], clean=None, ignoreNFO=None):
        if clean is None: clean = REAL_SETTINGS.getSettingBool('Refresh_Clean')
        if ignoreNFO is None: ignoreNFO = REAL_SETTINGS.getSettingBool('Refresh_Ignore_NFO')
        artOnly = REAL_SETTINGS.getSettingBool('Refresh_Art_Only')
        self.log('refreshMovies, movies = %s, clean = %s, ignoreNFO = %s, artOnly = %s'%(len(movies),clean,ignoreNFO,artOnly))
        if len(movies) > 0: random.shuffle(movies)
        if clean:
            for group in self._movieDuplicateGroups(movies):
                self._tasks.setdefault('cleanMovies',list()).append(group)
        for movie in movies:
            if self.monitor.waitForAbort(0.01): return False
            elif artOnly and not self._needsRefresh(movie): continue
            self._tasks.setdefault('refreshMovie',set()).add((movie.get('movieid'),ignoreNFO))
        return True

    def _needsRefresh(self, item):
        art = item.get('art') or {}
        if not (art.get('poster') and art.get('fanart')): return True
        if REAL_SETTINGS.getSettingBool('Refresh_QA_Blank'):
            if not (item.get('plot') or '').strip(): return True
            if not (item.get('mpaa') or '').strip(): return True
        return False

    def _excluded(self, name):
        if not name: return False
        exclude = (REAL_SETTINGS.getSetting('Clean_Exclude') or '').strip()
        if not exclude: return False
        return any(x.strip().lower() == name.strip().lower() for x in exclude.split(',') if x.strip())


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
        imdb = (movie.get('imdbnumber') or '').strip()
        if imdb: return ('imdb', imdb)
        return ('label', movie.get('label'), movie.get('year'))

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
            result = (self.refreshTV((self.getTVshows()    or [])) & 
                    self.refreshMovies((self.getMovies() or [])))
            if result: notification(LANGUAGE(32024))
            return result
        except Exception as e:
            self.log('runRefresh, Scan failed! %s'%(e), xbmc.LOGERROR)
            notification(LANGUAGE(32009))
            return False

    def runClean(self):
        try:
            self._alertOfflineShares()
            tvshows  = self.getTVshows()
            movies   = self.getMovies()
            tv_ok    = True
            movie_ok = True
            for show in tvshows:
                if self.monitor.waitForAbort(0.01): return False
                tv_ok = self.cleanTV(show.get('tvshowid')) and tv_ok
            for movie in movies:
                if self.monitor.waitForAbort(0.01): return False
                elif not self._pauseWhilePlaying(): return False
                if movie.get('file') and not xbmcvfs.exists(movie.get('file')):
                    self.log('cleanMovies, movie file no longer exists: %s' % movie.get('file'))
                    self._removeMovie(movie.get('movieid'), movie.get('file'), "cleanMovies (Missing File)")
            for group in self._movieDuplicateGroups(movies):
                if self.monitor.waitForAbort(0.01): return False
                movie_ok = self.cleanMovies(group) and movie_ok
            result = tv_ok and movie_ok
            if result: notification(LANGUAGE(32024))
            return result
        except Exception as e:
            self.log('runClean, Scan failed! %s'%(e), xbmc.LOGERROR)
            notification(LANGUAGE(32009))
            return False

    def cleanSeason(self, tvshowid, season):
        try:
            eps = [e for e in (getEpisodes(tvshowid) or []) if e.get('season') == season]  # module-level: cached self.getEpisodes goes stale after removals
            if not eps:
                self.log('cleanSeason, no episodes for showid=%s season=%s' % (tvshowid, season))
                return True
            showtitle = eps[0].get('showtitle', '')
            if self._excluded(showtitle): return False
            total = 0
            for e in eps:
                f = e.get('file', '')
                if f and xbmcvfs.exists(f):
                    try:    total += xbmcvfs.Stat(f).st_size()
                    except Exception: pass
            body = '%s - Season %d\n%d episode(s), %s' % (showtitle, season, len(eps), format_size(total))
            if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled'): body = '[DRY RUN]\n%s' % body
            # always confirm, regardless of Dry Run (prompt is unconditional; the gate lives in _removeEpisode)
            if not xbmcgui.Dialog().yesno(LANGUAGE(32062), body): return False
            removed = 0
            for e in eps:
                if self.monitor.waitForAbort(0.01): return False
                elif not self._pauseWhilePlaying(): return False
                if self._removeEpisode(e.get('episodeid'), e.get('file'), 'cleanSeason'): removed += 1
            if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled'): notification(LANGUAGE(32063))
            else: notification(LANGUAGE(32064) % (removed, len(eps)))
            return True
        except Exception as e:
            self.log('cleanSeason failed! %s' % e, xbmc.LOGERROR)
            return False

    def markWatched(self, tvshowid, season, watched):
        try:
            eps = sendJSON({"method":"VideoLibrary.GetEpisodes",
                            "params":{"tvshowid":tvshowid,"properties":["season","episode","playcount"]}}).get('result',{}).get('episodes', [])
            if season is not None: eps = [e for e in eps if e.get('season') == season]
            if not eps:
                self.log('markWatched, no episodes for showid=%s season=%s' % (tvshowid, season))
                return True
            now = datetime.datetime.now().replace(microsecond=0).isoformat()
            updated = 0
            for e in eps:
                if self.monitor.waitForAbort(0.01): return False
                params = {'episodeid': e.get('episodeid')}
                if watched:
                    params.update({'playcount': (e.get('playcount') or 0) + 1, 'lastplayed': now})
                else:
                    params.update({'playcount': 0, 'lastplayed': None, 'resume': None})
                if sendJSON({"method":"VideoLibrary.SetEpisodeDetails","params":params}).get('result') == 'OK':
                    updated += 1
            notification(LANGUAGE(32069) % updated)
            return True
        except Exception as e:
            self.log('markWatched failed! %s' % e, xbmc.LOGERROR)
            return False

    def _shareRoot(self, path):
        if not path or not path.startswith(('smb:','nfs:','ftp:','dav:','sftp:')): return None
        parts = path.split('/')
        return (f"{parts[0]}//{parts[2]}/{parts[3]}/" if len(parts) >= 4 else f"{parts[0]}//{parts[2]}/") if len(parts) >= 3 else None

    def _alertOfflineShares(self):
        if not REAL_SETTINGS.getSettingBool('Alert_Offline_Shares'): return
        for path in [REAL_SETTINGS.getSetting('Scraper_TV_Folder'), REAL_SETTINGS.getSetting('Scraper_Movie_Folder')]:
            root_share = self._shareRoot(path)
            if root_share and not xbmcvfs.exists(root_share) and root_share not in self._warned:
                self._warned.add(root_share)
                self.log('_alertOfflineShares, share offline: %s' % root_share, xbmc.LOGWARNING)
                notification('%s: %s' % (ADDON_NAME, root_share), header=LANGUAGE(32037), icon=xbmcgui.NOTIFICATION_WARNING, show=True)

    def _watchShares(self):
        # offline->online transition detection on configured remote sources -> auto-rescan
        if not REAL_SETTINGS.getSettingBool('Share_Watch_Enabled'): return
        now = time.time()
        if now - self._lastShareCheck < 60: return
        self._lastShareCheck = now
        for key, path in [('tv', REAL_SETTINGS.getSetting('Scraper_TV_Folder')), ('movie', REAL_SETTINGS.getSetting('Scraper_Movie_Folder'))]:
            root = self._shareRoot(path)
            if not root: continue
            up = xbmcvfs.exists(root)
            prev = self._shareState.get(root)
            self._shareState[root] = up
            if prev is False and up:
                self.log('_watchShares, share recovered: %s -> rescanning %s' % (root, path))
                notification(LANGUAGE(32078))
                self._que(self.scrapeDirectory, 2, path)

    def runBackup(self):
        folder = REAL_SETTINGS.getSetting('Backup_Folder')
        if not folder or not xbmcvfs.exists(folder):
            self.log('runBackup, invalid folder: %s' % folder, xbmc.LOGWARNING)
            return False
        sub = '%s/powertoys-%s' % (folder.rstrip('/\\'), time.strftime('%Y%m%d-%H%M'))
        xbmcvfs.mkdirs(sub)
        self.log('runBackup, exporting library to %s' % sub)
        resp = sendJSON({"method":"VideoLibrary.Export","params":{"path":sub,"playlists":False,"movies":{"enabled":True,"thumbnails":False},"tvshows":{"enabled":True,"episodes":True,"thumbnails":False}}})
        ok = resp.get('result') == 'OK'
        if ok:
            pruned = self._pruneBackups(folder)
            if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled'):
                if pruned: notification(LANGUAGE(32063))  # dry run never deletes
            else:
                notification(LANGUAGE(32036), show=True)
        return ok

    def _pruneBackups(self, folder):
        # ponytail: automatic prune after a successful export; consent = Backup_Keep_Count setting,
        # deletions still gated by Dry Run. No prompt possible on an unattended scheduled run.
        keep = REAL_SETTINGS.getSettingInt('Backup_Keep_Count')
        if keep <= 0: return 0
        try:
            dirs, _files = xbmcvfs.listdir(folder)
            ours = sorted([d for d in (dirs or []) if d.startswith('powertoys-')], reverse=True)  # timestamp names = chronological
            pruned = 0
            for d in ours[keep:]:
                target = '%s/%s' % (folder.rstrip('/\\'), d)
                if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled'):
                    self.log('_pruneBackups [DRY RUN] would remove: %s' % target)
                    pruned += 1
                    continue
                if xbmcvfs.rmdir(target, True):
                    self.log('_pruneBackups removed: %s' % target)
                    pruned += 1
            return pruned
        except Exception as e:
            self.log('_pruneBackups failed: %s' % e, xbmc.LOGWARNING)
            return 0

    def runCacheClean(self):
        # interactive system cache cleanup: always prompt, Dry Run gates the deletes
        try:
            tempdir  = xbmcvfs.translatePath('special://temp/')
            packdir  = xbmcvfs.translatePath('special://packages/')
            logdir   = xbmcvfs.translatePath('special://logpath/')
            def dirsize(path):
                total = 0
                try:
                    _dirs, files = xbmcvfs.listdir(path)
                    for f in (files or []):
                        try: total += xbmcvfs.Stat(path + f).st_size()
                        except Exception: pass
                    for d in (_dirs or []):
                        total += dirsize(path + d + '/')
                except Exception: pass
                return total
            old_logs = []
            logsize = 0
            try:
                _dirs, files = xbmcvfs.listdir(logdir)
                for f in (files or []):
                    if f == 'kodi.log': continue  # active log stays
                    try:
                        logsize += xbmcvfs.Stat(logdir + f).st_size()
                        old_logs.append(logdir + f)
                    except Exception: pass
            except Exception: pass
            t_size, p_size = dirsize(tempdir), dirsize(packdir)
            body = 'temp: %s\npackages: %s\nold logs: %s\n\nDelete these files?' % (format_size(t_size), format_size(p_size), format_size(logsize))
            if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled'): body = '[DRY RUN]\n%s' % body
            if not xbmcgui.Dialog().yesno(LANGUAGE(32070), body): return False
            if REAL_SETTINGS.getSettingBool('Dry_Run_Enabled'):
                notification(LANGUAGE(32063))
                return True
            freed, removed = 0, 0
            def wipe(path):
                nonlocal freed, removed
                try:
                    _dirs, files = xbmcvfs.listdir(path)
                    for f in (files or []):
                        try:
                            sz = xbmcvfs.Stat(path + f).st_size()
                            if xbmcvfs.delete(path + f): freed += sz; removed += 1
                        except Exception: pass
                    for d in (_dirs or []): wipe(path + d + '/')
                except Exception: pass
            wipe(tempdir)
            wipe(packdir)
            for f in old_logs:
                try:
                    if xbmcvfs.delete(f): removed += 1
                except Exception: pass
            notification('%s: %s (%d)' % (LANGUAGE(32071), format_size(freed), removed))
            return True
        except Exception as e:
            self.log('runCacheClean failed: %s' % e, xbmc.LOGERROR)
            return False

    def runRamFree(self):
        # cross-platform RAM free: Python gc + platform allocator trim + own cache drop
        try:
            def freeMB():
                try: return int(xbmc.getInfoLabel('System.Memory(free)') or 0) // 1048576
                except Exception: return -1
            before = freeMB()
            collected = gc.collect()
            trimmed = self._trimAllocator()
            self._cache.clear()  # addon's own in-memory query cache
            after = freeMB()
            self.log('runRamFree: gc=%d objects, trim=%s, free %dMB -> %dMB' % (collected, trimmed, before, after))
            notification(LANGUAGE(32082) % (max(before - after, 0) if before >= 0 and after >= 0 else 0, collected, after))
            return True
        except Exception as e:
            self.log('runRamFree failed: %s' % e, xbmc.LOGERROR)
            return False

    def _trimAllocator(self):
        # best-effort per-platform memory trim of Kodi's own process; unsupported platforms no-op.
        # cannot purge other apps - Kodi's sandbox has no API for that.
        try:
            if sys.platform.startswith('linux'):
                try:
                    ctypes.CDLL('libc.so.6').malloc_trim(0)  # glibc: return freed heap pages to OS
                    return 'malloc_trim'
                except Exception:
                    try:
                        ctypes.CDLL(None).mallopt(-100, 0)  # Android bionic M_PURGE; unknown tags no-op
                        return 'mallopt'
                    except Exception:
                        return None
            elif sys.platform == 'win32':
                k32 = ctypes.windll.kernel32
                k32.GetCurrentProcess.restype = ctypes.c_void_p
                k32.SetProcessWorkingSetSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
                # (SIZE_T)-1 trims own working set to minimum; brief page-in churn possible afterwards
                k32.SetProcessWorkingSetSize(k32.GetCurrentProcess(), ctypes.c_size_t(-1), ctypes.c_size_t(-1))
                return 'workingset'
        except Exception as e:
            self.log('_trimAllocator: %s' % e, xbmc.LOGDEBUG)
        return None

    def runTexture(self):
        try:
            dry = REAL_SETTINGS.getSettingBool('Dry_Run_Enabled')
            self.log('runTexture, dry_run = %s' % dry)
            stale = recache_missing(dry_run=dry)
            orphans = prune(dry_run=dry)
            self.log('runTexture, stale removed = %s, orphans removed = %s' % (stale, orphans))
            return True
        except Exception as e:
            self.log('runTexture failed: %s' % e, xbmc.LOGERROR)
            return False

    def runMusic(self):
        try:
            self.log('runMusic, scanning music library')
            sendJSON({"method":"AudioLibrary.Scan"})
            if self.monitor.waitForAbort(2.0): return False  # let the scan actually start
            while not self.monitor.abortRequested() and xbmc.getCondVisibility('Library.IsScanningMusic'):
                if self.monitor.waitForAbort(1.0): return False
            if REAL_SETTINGS.getSettingBool('Music_Clean'):
                self.log('runMusic, cleaning music library')
                sendJSON({"method":"AudioLibrary.Clean"})
                if self.monitor.waitForAbort(2.0): return False
                while not self.monitor.abortRequested() and xbmc.getCondVisibility('Library.IsScanningMusic'):
                    if self.monitor.waitForAbort(1.0): return False
            notification(LANGUAGE(32024))
            return True
        except Exception as e:
            self.log('runMusic failed: %s' % e, xbmc.LOGERROR)
            return False

    def healthReport(self):
        try:
            report = self._buildReport()
            self.log('healthReport:\n%s' % report)
            xbmcgui.Dialog().textviewer(LANGUAGE(32035), report)
            return True
        except Exception as e:
            self.log('healthReport failed: %s' % e, xbmc.LOGERROR)
            return False

    def _buildReport(self):
        tvshows = (self.getTVshows() or [])
        movies  = (self.getMovies() or [])
        episodes_total, missing, dupes = 0, [], []
        for show in tvshows:
            eps = (self.getEpisodes(show.get('tvshowid')) or [])
            episodes_total += len(eps)
            eps = [self._episodeKey(e) for e in eps]
            for e in eps:
                if e.get('file') and not xbmcvfs.exists(e.get('file')): missing.append(e.get('file'))
            for key, group in findDupes(eps, key='episode_key').items():
                dupes.append('TV %s: %d copies' % (key, len(group)))
        missing_movies = [m.get('file') for m in movies if m.get('file') and not xbmcvfs.exists(m.get('file'))]
        missing.extend(missing_movies)
        for group in self._movieDuplicateGroups(movies):
            dupes.append('Movie %s: %d copies' % (group[0].get('label'), len(group)))
        nxscraper = self.cache.get('runScraper') or 0
        nxrefresh = self.cache.get('runRefresh') or 0
        nxtbackup = self.cache.get('runBackup') or 0
        nxttexture = self.cache.get('runTexture') or 0
        tex_rows, tex_bytes = cache_stats()
        lines = [
            'TV Shows: %d' % len(tvshows),
            'Episodes: %d' % episodes_total,
            'Movies: %d' % len(movies),
            'Texture cache: %d rows, %s' % (tex_rows, format_size(tex_bytes)),
            '',
            'Missing files: %d' % len(missing),
        ]
        lines.extend('  %s' % m for m in missing[:25])
        if len(missing) > 25: lines.append('  ... and %d more' % (len(missing) - 25))
        lines.append('')
        lines.append('Duplicate groups: %d' % len(dupes))
        lines.extend('  %s' % d for d in dupes[:25])
        if len(dupes) > 25: lines.append('  ... and %d more' % (len(dupes) - 25))
        lines.append('')
        lines.append('Next scraper run:  %s' % (time.strftime('%Y-%m-%d %H:%M', time.localtime(nxscraper)) if nxscraper else 'n/a'))
        lines.append('Next refresh run:  %s' % (time.strftime('%Y-%m-%d %H:%M', time.localtime(nxrefresh)) if nxrefresh else 'n/a'))
        lines.append('Next backup run:   %s' % (time.strftime('%Y-%m-%d %H:%M', time.localtime(nxtbackup)) if nxtbackup else 'n/a'))
        lines.append('Next texture run:  %s' % (time.strftime('%Y-%m-%d %H:%M', time.localtime(nxttexture)) if nxttexture else 'n/a'))
        return '\n'.join(lines)

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


if __name__ == '__main__': Service()._start()
