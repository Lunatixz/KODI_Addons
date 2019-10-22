#   Copyright (C) 2019 Lunatixz
#
#
# This file is part of TV Themes
#
# TV Themes is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# TV Themes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TV Themes.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, traceback, urllib, urllib2, threading, time, json
import xbmc, xbmcvfs, xbmcaddon, xbmcgui
   
from pydub import AudioSegment 

REAL_SETTINGS = xbmcaddon.Addon(id='service.tvthemes')
ADDON_ID      = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile').decode("utf-8")
DEBUG         = REAL_SETTINGS.getSetting("Enable_Debugging") == 'true'
BIN_FOLDER    = os.path.join(ADDON_PATH,'resources','bin')
DL_FOLDER     = (REAL_SETTINGS.getSetting("dl_folder") or SETTINGS_LOC)
FFMPEG_PATH   = REAL_SETTINGS.getSetting("FFMPEG_PATH")
URL           = 'http://tvthemes.plexapp.com/%s.mp3'
    
try:
    from multiprocessing import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
    CORES = cpu_count()
except: ENABLE_POOL = False
        
def notificationDialog(message, header=ADDON_NAME, show=True, sound=False, time=1000, icon=ICON):
    try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
    except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
     
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' , ' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self, xbmc.Monitor())
         
         
    def onSettingsChanged(self):
        log('onSettingsChanged')
        
        
class Service(object):
    def __init__(self):
        self.tvdb = ''
        self.waitTime  = 0.5
        self.lastCheck = 0
        self.myMonitor = Monitor()
        self.myMonitor.myService = self
        self.DLpath = os.path.join(DL_FOLDER,'%s.%s')
        self.binPath, self.exe = self.getBinPath()
        log('Download Path = %s'%self.DLpath)
        if not xbmcvfs.exists(DL_FOLDER): xbmcvfs.mkdir(DL_FOLDER) 
        self.downloadThread = threading.Timer(self.waitTime, self.getTheme)
        self.queueThread = threading.Timer(self.waitTime, self.chkShows)
        self.startService()


    def playTheme(self, file):
        log('playTheme, file = %s'%file)
        xbmc.playSFX(file)
        
    
    def stopTheme(self):
        log('stopTheme')
        xbmc.stopSFX()

         
    def getTheme(self, tvdb):
        log('getTheme, tvdb = %s'%tvdb)
        MP3 = xbmc.translatePath(self.DLpath%(tvdb,'mp3'))
        WAV = xbmc.translatePath(self.DLpath%(tvdb,'wav'))
        if self.downloadMP3(URL%(tvdb), MP3):
            if self.convertTheme(tvdb): 
                self.deleteMP3(MP3)
                self.fetchTheme(tvdb)
        
        
    def deleteMP3(self, file):
        log('deleteMP3, file = %s'%file)
        try: return xbmcvfs.delete(file)
        except: return False
        
        
    def downloadMP3(self, url, file):
        finished = False
        try:
            u = urllib2.urlopen(url)
        except Exception as e: 
            log('downloadMP3, no theme found')
            return finished
        h = u.info()
        totalSize = int(h["Content-Length"])
        log('downloadMP3, url = %s, %s bytes'%(url, totalSize))
        fp = open(file, 'wb')
        blockSize = 8192 #100000 # urllib.urlretrieve uses 8192
        count = 0
        while not self.myMonitor.abortRequested():
            chunk = u.read(blockSize)
            if not chunk: break
            fp.write(chunk)
            count += 1
            if totalSize > 0:
                percent = int(count * blockSize * 100 / totalSize)
                if percent > 100: percent = 100
                if percent < 100: log('downloadMP3, url = %s, %2d%%'%(url, percent))
                else: finished = True
        fp.flush()
        fp.close()
        log('downloadMP3, url = %s, Finished = %s'%(url,finished))
        return finished
        
        
    def convertTheme(self, tvdb):
        try:
            MP3 = xbmc.translatePath(self.DLpath%(tvdb,'mp3'))
            WAV = xbmc.translatePath(self.DLpath%(tvdb,'wav'))
            binPath = xbmc.translatePath(self.binPath) 
            log('convertTheme, TVDB = %s, binPath = %s, exe = %s'%(tvdb, binPath, self.exe))
            sound = AudioSegment.from_mp3(MP3)
            sound.converter = r"%s"%(binPath)
            sound.ffmpeg = os.path.join(binPath,'ffmpeg%s'%self.exe)
            sound.ffprobe = os.path.join(binPath,'ffprobe%s'%self.exe)
            sound.export(WAV, format="wav")
            if self.myMonitor.waitForAbort(1): return False
            self.tvdb = ''
            return True
        except Exception as e: 
            log('convertTheme, failed! ' + str(e), xbmc.LOGERROR)
            return False
         
         
    def downloadQueue(self, tvdb):
        log('downloadQueue, TVDB = %s'%tvdb)
        if self.downloadThread.isAlive(): self.downloadThread.join()
        self.downloadThread = threading.Timer(self.waitTime, self.getTheme, [tvdb])
        self.downloadThread.name = "downloadThread"
        self.downloadThread.start()
        
        
    def hasTV(self):
        return bool(xbmc.getCondVisibility('Library.HasContent(TVShows)'))
    
    
    def getTVShows(self):
        if not self.hasTV(): return []
        json_query    = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"properties":["imdbnumber","uniqueid"]},"id":2}')
        json_response =  json.loads(xbmc.executeJSONRPC(json_query))
        if not 'result' in json_response: return []
        items = json_response['result']['tvshows']
        log('getTVShows, found %s'%(len(items)))
        return [(item.get("uniqueid",{}).get("tvdb","") or item.get('imdbnumber','')) for item in items if len((item.get("uniqueid",{}).get("tvdb","") or item.get('imdbnumber',''))) > 0]
        
        
    def queueTheme(self, tvdb):
        log('queueTheme, TVDB = %s'%tvdb)
        if self.myMonitor.waitForAbort(1): return None
        self.waitTime = 5.0
        MP3 = (self.DLpath%(tvdb,'mp3'))
        WAV = (self.DLpath%(tvdb,'wav'))
        if xbmcvfs.exists(WAV): return None
        elif xbmcvfs.exists(MP3): self.convertTheme(tvdb)
        else: self.downloadQueue(tvdb)
        
        
    def queueThemes(self):
        log('queueThemes')
        tvdbLST = self.getTVShows()
        if False in self.poolList(self.queueTheme,tvdbLST): return False
        return True
        

    def chkShows(self):
        log('chkShows')
        if self.queueThemes(): self.lastCheck = time.time()
        
         
    def startCHK(self):
        if self.queueThread.isAlive(): return
        self.queueThread = threading.Timer(self.waitTime, self.chkShows)
        self.queueThread.name = "queueThread"
        self.queueThread.start()


    def poolList(self, method, items):
        results = []
        if ENABLE_POOL and not DEBUG:
            pool = ThreadPool(CORES)
            results = pool.imap_unordered(method, items, chunksize=25)
            pool.close()
            pool.join()
        else: results = [method(item) for item in items]
        results = filter(None, results)
        return results
        
        
    def fetchTheme(self, tvdb):
        self.waitTime = 5.0
        if self.tvdb == tvdb: return
        log('fetchTheme, TVDB = %s'%tvdb)
        self.tvdb = tvdb
        self.stopTheme()
        MP3 = (self.DLpath%(tvdb,'mp3'))
        WAV = (self.DLpath%(tvdb,'wav'))
        if xbmcvfs.exists(WAV): self.playTheme(WAV)
        elif xbmcvfs.exists(MP3): self.convertTheme(tvdb)
        else: self.downloadQueue(tvdb)
         
         
    def getFocus(self):
        if xbmc.getInfoLabel('ListItem.DBTYPE') == 'tvshow': 
            try: tvdb = sys.listitem.getVideoInfoTag().getUniqueID('tvdb')#todo debug
            except: tvdb = xbmc.getInfoLabel('ListItem.IMDBNumber')#requires tvdb scraper, not ideal.
            self.fetchTheme(tvdb)
        else: self.stopTheme()


    def getBinPath(self):
        if FFMPEG_PATH: return os.path.splitext(FFMPEG_PATH)
        elif bool(xbmc.getCondVisibility('system.platform.windows')): return os.path.join(BIN_FOLDER,'windows'), '.exe'
        elif bool(xbmc.getCondVisibility('system.platform.osx')): return os.path.join(BIN_FOLDER,'osx'), ''
        elif bool(xbmc.getCondVisibility('system.platform.linux')):return os.path.join(BIN_FOLDER,'linux'), ''
        elif 'android' in platform.lower(): return os.path.join(BIN_FOLDER,'android'), ''
        log('getBinPath, failed')
        notificationDialog('Unable to set FFMPEG Path')
        sys.exit()
        
        
    def startService(self):
        log('startService')
        notificationDialog('Service Started')
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(1): break
            elif xbmc.Player().isPlaying(): continue #ignore while playing
            # elif time.time() > self.lastCheck + (24*60*60): self.startCHK()
            self.getFocus() # check focus item for tvdb
            
if __name__ == '__main__': Service()