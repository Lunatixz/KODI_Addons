#   Copyright (C) 2018 Team-Kodi
#
#
# This file is part of Kodi Module Auditor
#
# Kodi Module Auditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Kodi Module Auditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kodi Module Auditor.  If not, see <http://www.gnu.org/licenses/>.

import schedule
import xbmc

from scan import *

#todo scan modules
class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.Player())
        
        
    def onPlayBackStarted(self):
        log('onPlayBackStarted')
        
        
    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        
        
class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self, xbmc.Monitor())
        
        
    def onSettingsChanged(self):
        log("onSettingsChanged")
        
        
class Service(object):
    def __init__(self):
        self.myPlayer  = Player()
        self.myMonitor = Monitor()
        self.myScanner = SCAN()
        self.startService()

         
    def startService(self):
        schedule.clear()
        schedule.every(WAIT).days.do(self.myScanner.preliminary)
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(15): break
            schedule.run_pending()
if __name__ == '__main__': Service()