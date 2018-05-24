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
import urlparse, urllib, urllib2, socket, json
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

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)

class Player(xbmc.Player):
    def __init__(self):
        self.playingTime  = 0
        self.playingTTime = 0
        self.playingItem  = {}
        
        
    def onPlayBackStarted(self):
        self.playingTime  = 0
        self.playingTTime = self.getTotalTime()
        self.playingItem  = self.service.myUtils.requestItem()
        log('onPlayBackStarted, playingItem = ' + json.dumps(self.playingItem))

        
    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        try: self.service.myUtils.removeContent(self.playingItem)
        except: pass
        
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        try: 
            if (self.playingTime * 100 / self.playingTTime) >= float(REAL_SETTINGS.getSetting('Play_Percentage')): 
                self.service.myUtils.removeContent(self.playingItem)
        except: pass


class Monitor(xbmc.Monitor):
    def __init__(self):
        self.pendingChange = False
        
        
    def onSettingsChanged(self):
        log('onSettingsChanged')
        self.pendingChange = True
        
        
class Service(object):
    def __init__(self):
        self.myUtils   = default.MM() 
        self.myMonitor = Monitor()
        self.myPlayer  = Player()
        self.myPlayer.service = self
        self.startService()
        
        
    def chkSettings(self):
        self.TVShowList = self.myUtils.getUserList()
        self.myMonitor.pendingChange = False
        
        
    def startService(self):
        log('startService')
        while not self.myMonitor.abortRequested():
            if self.myMonitor.pendingChange: self.chkSettings()
            if self.myMonitor.waitForAbort(5): break
            if self.myPlayer.isPlaying(): 
                if len(self.myPlayer.playingItem) == 0: self.myPlayer.onPlayBackStarted()
                self.myPlayer.playingTime = self.myPlayer.getTime()

if __name__ == '__main__': Service()