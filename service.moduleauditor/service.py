#   Copyright (C) 2019 Team-Kodi
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

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.pendingChange = False
        self.optOut = REAL_SETTINGS.getSetting('Disable_Service') == "true"
        
        
    def onSettingsChanged(self):
        log("onSettingsChanged")
        self.pendingChange = True
        REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
        self.optOut = REAL_SETTINGS.getSetting('Disable_Service') == "true"
         
        
class Service(object):
    def __init__(self):
        self.myMonitor = Monitor()
        self.myScanner = SCAN()
        if not self.myMonitor.optOut:
            self.myMonitor.waitForAbort(30) # startup delay
            self.myScanner.preliminary()    # initial scan
        self.startService()

         
    def startService(self):
        schedule.clear()
        self.myMonitor.pendingChange = False
        if not self.myMonitor.optOut: schedule.every(int(REAL_SETTINGS.getSetting('Scan_Wait'))).days.do(self.myScanner.preliminary) # run every x days
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(30) or self.myMonitor.pendingChange: break
            if xbmc.getGlobalIdleTime() >= 900: continue # do not notify when idle
            if not self.myMonitor.optOut and not xbmc.Player().isPlaying(): schedule.run_pending()
        if self.myMonitor.pendingChange: self.startService()
        
if __name__ == '__main__': Service()