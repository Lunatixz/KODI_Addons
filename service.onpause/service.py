#   Copyright (C) 2019 Lunatixz
#
#
# This file is part of OnPause
#
# OnPause is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OnPause is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OnPause.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-
import os, sys, time, datetime, re, traceback, json, urllib
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

# Plugin Info
ADDON_ID       = 'service.onpause'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString
DEBUG          = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def uni(string, encoding = 'utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode): string = unicode(string, encoding, errors='ignore')
        elif isinstance(string, unicode): string = string.encode('ascii', 'replace')
    return string

class Player(xbmc.Player):
    def __init__(self):
        self.playingTime = 0
        self.playingFile = ''
        
        
    def onPlayBackPaused(self):
        log('onPlayBackPaused')
        self.playingTime = self.getTime()
        self.playingFile = (self.getPlayingFile() or '')
        
        
    def onPlayBackResumed(self):
        log('onPlayBackResumed')


class Monitor(xbmc.Monitor):
    def __init__(self):
        self.pendingPlay = False
        
        
    def onScreensaverActivated(self):
        log('onScreensaverActivated')
        xbmc.sleep(1000)
        if not self.pendingPlay and xbmc.getCondVisibility("Player.HasVideo") and not self.myService.myPlayer.playingFile.startswith(('plugin://','pvr://','upnp://')): self.myService.startSaver()
            
        
    def onScreensaverDeactivated(self):
        log('onScreensaverDeactivated')
        xbmc.sleep(1000)
        if self.pendingPlay: self.myService.startPlayer(self.myService.myPlayer.playingFile, self.myService.myPlayer.playingTime)


class Service(object):
    def __init__(self):
        self.myMonitor   = Monitor()
        self.myMonitor.myService = self
        self.myPlayer    = Player()
        self.myPlayer.myService  = self
        
    
    def startSaver(self):
        log('startSaver')
        self.myPlayer.stop()
        xbmc.sleep(1000)
        self.myMonitor.pendingPlay = True
        xbmc.executebuiltin('ActivateScreensaver')
        
    
    def startPlayer(self, playingFile, playingTime):
        log('startPlayer, playingFile = %s, playingTime = %d'%(uni(playingFile),int(playingTime)))
        self.myPlayer.play(playingFile)
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(1): break
            elif self.myPlayer.isPlayingVideo() and xbmc.getCondVisibility("Player.HasVideo"):
                self.myPlayer.seekTime(int(playingTime))
                break
        if self.myPlayer.isPlayingVideo():
            self.myPlayer.pause()
            xbmc.sleep(5000)
        self.myMonitor.pendingPlay = False
           
           
    def startService(self):
        log('startService')
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(5): break
        
if __name__ == '__main__': Service().startService()

