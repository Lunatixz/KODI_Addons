#   Copyright (C) 2021 Lunatixz
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
from default import *

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.playingItem = {}
        
        
    def resetPlayingItem(self):
        self.playingItem = {}
        
        
    def assertPlaying(self):
        if self.isPlayingVideo() and not isPseudoTV(): return True
        return False
        
        
    def updatePlayingItem(self):
        if self.playingItem: self.playingItem['Time'] = self.getPlayerTime()
        else:  self.onPlayBackStarted()
        

    def getPlayerItem(self):
        log('getPlayerItem')
        return self.myService.myUtils.getPlayerItem()
        
        
    def getPlayerTotalTime(self):
        try:    return self.getTotalTime()
        except: return 0
        
        
    def getPlayerTime(self):
        try:    return self.getTime()
        except: return 0
        
        
    def onAVStarted(self):
        log('onAVStarted')
        self.resetPlayingItem()
        

    def onPlayBackStarted(self):
        if self.isPlayingVideo():
            self.playingItem = self.getPlayerItem()
            self.playingItem['TotalTime'] = self.getPlayerTotalTime()
            log('onPlayBackStarted, playingItem = %s'%(self.playingItem))
        

    def onPlayBackError(self):
        log('onPlayBackError')
        self.resetPlayingItem()
        
        
    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        self.chkContent(self.playingItem)
        
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        self.chkContent(self.playingItem)
        

    def chkContent(self, playingItem={}):
        log('chkContent, playingItem = %s'%(self.playingItem))
        conditions = [isPseudoTV(),
                      not self.playingItem,
                      self.playingItem.get('TotalTime',-1) <= 0,
                      self.playingItem.get("file","").startswith(('plugin://','upnp://','pvr://'))]
                      
        if True in conditions: return
        if ((self.playingItem['Time'] * 100) / self.playingItem['TotalTime']) >= float(REAL_SETTINGS.getSetting('Play_Percentage')):
            if self.playingItem["type"] == "episode" and REAL_SETTINGS.getSetting('Wait_4_Season') == "true": 
                self.myService.myUtils.chkSeason(self.playingItem)
            else:
                self.myService.myUtils.removeContent(self.playingItem)
        self.resetPlayingItem()
        
        
class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
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
        if self.myService.loadMySchedule(): 
            self.pendingChange = False
                
        
    def onNotification(self, sender, method, data):
        log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
                
 
class Service(object):
    def __init__(self):
        self.myUtils   = MM()
        self.myMonitor = Monitor()
        self.myPlayer  = Player()
        self.myPlayer.myService  = self
        self.myMonitor.myService = self
    
    
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
        if scanTime  > 0: schedule.every(scanTime).hours.do(self.scanLibrary)
        if cleanTime > 0: schedule.every(cleanTime).hours.do(self.cleanLibrary)
        return True
        
        
    def getIdleTime(self):
        try:    return (int(xbmc.getGlobalIdleTime()) or 0)
        except: return 0 #Kodi raises error after sleep.
        
            
    def startService(self):
        log('startService')
        self.myMonitor.waitForAbort(5)
        self.loadMySchedule()
        while not self.myMonitor.abortRequested():
            if   self.myMonitor.waitForAbort(2): break
            elif self.myPlayer.assertPlaying():  self.myPlayer.updatePlayingItem() #update playingItem
            elif self.getIdleTime() > 900:       schedule.run_pending()            #run scan/clean when 15mins idle


if __name__ == '__main__': Service().startService()