#   Copyright (C) 2020 Lunatixz
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
        
        
    def reset(self):
        log('reset')
        self.__init__()
        
        
    def getPlayerTotalTime(self):
        try:    return self.getTotalTime()
        except: return 0
        
        
    def getPlayerTime(self):
        try:    return self.getTime()
        except: return 0
        
        
    def onPlayBackStarted(self):
        if self.isPlayingVideo():
            self.playingItem = self.myService.myUtils.requestItem()
            self.playingItem['TotalTime'] = self.getPlayerTotalTime()
            log('onPlayBackStarted, playingItem = %s'%(self.playingItem))
            #todo add wait for playlist option, save playing playlist, monitor position and watched status; on stop prompt to delete watched items if match.
        

    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        self.chkContent(self.playingItem)
        
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        self.chkContent(self.playingItem)
        

    def chkContent(self, playingItem={}):
        log('chkContent, playingItem = %s'%(json.dumps(self.playingItem)))
        conditions = [xbmcgui.Window(10000).getProperty("PseudoTVRunning") == "True",
                      not self.playingItem,
                      self.playingItem.get('TotalTime',-1) <= 0,
                      self.playingItem.get("file","").startswith(('plugin://','upnp://','pvr://'))]
        if True in conditions: return
        elif (self.playingItem['Time'] * 100 / self.playingItem['TotalTime']) >= float(REAL_SETTINGS.getSetting('Play_Percentage')):
            if self.playingItem["type"] == "episode" and REAL_SETTINGS.getSetting('Wait_4_Season') == "true": 
                self.myService.myUtils.chkSeason(self.playingItem)
            else:
                self.myService.myUtils.removeContent(self.playingItem)
        self.reset()
        
        
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
        self.running   = False
        self.myUtils   = MM()
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
        if scanTime  > 0: schedule.every(scanTime).hours.do(self.scanLibrary)
        if cleanTime > 0: schedule.every(cleanTime).hours.do(self.cleanLibrary)
        return True
        
        
    def startService(self):
        log('startService')
        self.myMonitor.waitForAbort(5)
        self.loadMySchedule()
        while not self.myMonitor.abortRequested():
            # if xbmcgui.getCurrentWindowDialogId() == 10140 and not self.myMonitor.pendingChange: self.myMonitor.pendingChange = True
            if self.myMonitor.waitForAbort(5): break
            if self.myPlayer.isPlaying(): 
                if xbmcgui.Window(10000).getProperty("PseudoTVRunning") == "True": self.myPlayer.playingItem = {}
                if self.myPlayer.playingItem:
                    self.myPlayer.playingItem['Time'] = self.myPlayer.getPlayerTime()
                else: self.myPlayer.onPlayBackStarted()
            else: schedule.run_pending() #run scan/clean when idle

if __name__ == '__main__': Service()