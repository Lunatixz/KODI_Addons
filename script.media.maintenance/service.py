#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of Media Maintenance.
#
# Media Maintenance is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Media Maintenance is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Media Maintenance.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, re, traceback
import urlparse, urllib, urllib2, socket, json, schedule
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, default
from simplecache import SimpleCache, use_cache

# Plugin Info
ADDON_ID      = 'script.media.maintenance'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
PTVL_RUNNING  = xbmcgui.Window(10000).getProperty("PseudoTVRunning") == "True"

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)

class Player(xbmc.Player):
    def __init__(self):
        self.resetMeta()
        
        
    def resetMeta(self):
        self.playingTime     = 0
        self.playingPercent  = 0
        self.playingTotTime  = 0
        self.playingItem     = {}
        
        
    def onPlayBackStarted(self):
        xbmc.sleep(1000)
        if not self.isPlaying(): return
        self.resetMeta()
        self.playingTotTime  = self.getTotalTime()
        self.playingItem     = self.myService.myUtils.requestItem()
        log('onPlayBackStarted, playingItem = ' + json.dumps(self.playingItem))

         
    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        self.chkContent()
        
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        self.chkContent()
        

    def chkContent(self):
        log('chkContent')
        if PTVL_RUNNING or len(self.playingItem) == 0: return
        if self.playingItem.get["file"].startswith(('plugin://','upnp://','pvr://')): return
        if (self.playingTime * 100 / self.playingTotTime) >= float(REAL_SETTINGS.getSetting('Play_Percentage')):
            if self.playingItem["type"] == "episode" and REAL_SETTINGS.getSetting('Wait_4_Season') == "true": self.myService.myUtils.removeSeason(self.playingItem)
            else:self.myService.myUtils.removeContent(self.playingItem)
        self.resetMeta()
        
        
class Monitor(xbmc.Monitor):
    def __init__(self):
        self.pendingChange = False
        
        
    def onScanFinished(self, library):
        log('onScanFinished')
        
        
    def onCleanFinished(self, library):
        log('onCleanFinished')
        
        
    def onDatabaseUpdated(self, database):
        log('onDatabaseUpdated')
                
    
    def onSettingsChanged(self):
        log('onSettingsChanged')
        if self.pendingChange == True: return
        self.pendingChange = True
        self.onChange()
        
        
    def onChange(self):
        log('onChange')
        if self.myService.loadMySchedule(): self.pendingChange = False
        
        
class Service(object):
    def __init__(self):
        self.running   = False
        self.myUtils   = default.MM()
        self.myMonitor = Monitor()
        self.myMonitor.myService = self
        self.myPlayer  = Player()
        self.myPlayer.myService = self
        self.startService()
    
    
    def scanLibrary(self):
        log('scanLibrary')
        xbmc.executebuiltin('UpdateLibrary("video")')
        
        
    def cleanLibrary(self):
        log('cleanLibrary')
        xbmc.executebuiltin('CleanLibrary("video")')
        
        
    def loadMySchedule(self):
        log('loadMySchedule')
        schedule.clear()
        scanTime  = [0,1,6,24][int(REAL_SETTINGS.getSetting('Enable_Scan'))]
        cleanTime = [0,1,6,24,168][int(REAL_SETTINGS.getSetting('Enable_Clean'))]
        if scanTime  > 0: schedule.every(scanTime).hour.do(self.scanLibrary)
        if cleanTime > 0: schedule.every(cleanTime).hour.do(self.cleanLibrary)
        return True
        
        
    # def chkSettings(self):
        # self.myMonitor.pendingChange = False
        
        
    def startService(self):
        log('startService')
        self.myMonitor.waitForAbort(5)
        self.loadMySchedule()
        while not self.myMonitor.abortRequested():
            # if self.myMonitor.pendingChange and xbmcgui.getCurrentWindowDialogId() != 10140: self.chkSettings()
            if self.myMonitor.waitForAbort(5): break
            elif self.myPlayer.isPlaying(): 
                if len(self.myPlayer.playingItem) == 0: self.myPlayer.onPlayBackStarted()
                self.myPlayer.playingTime = self.myPlayer.getTime()
            else: schedule.run_pending() #run scan/clean when idle

if __name__ == '__main__': Service()