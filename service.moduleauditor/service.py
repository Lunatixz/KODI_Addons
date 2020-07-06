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

from scan import *

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.pendingChange = False
        self.optOut = REAL_SETTINGS.getSetting('Disable_Service') == "true"
        
        
    def onSettingsChanged(self):
        log("onSettingsChanged")
        if self.pendingChange: return
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
        setProperty('Running','False')
        self.myMonitor.pendingChange = False
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(30)   or self.myMonitor.pendingChange: break 
            elif xbmc.getGlobalIdleTime() >= 900 or xbmc.Player().isPlaying(): continue # do not notify when idle or playback, wait for user attention.
            elif not self.myMonitor.optOut:
                now       = time.time()
                lastCheck = float(REAL_SETTINGS.getSetting('Last_Scan') or now)
                scanWait  = (int(REAL_SETTINGS.getSetting('Scan_Wait')) * 86400)
                if now >= (lastCheck + scanWait):
                    REAL_SETTINGS.setSetting('Last_Scan',str(now))
                    self.myScanner.preliminary()
        if self.myMonitor.pendingChange: self.startService()
        
if __name__ == '__main__': Service()