#   Copyright (C) 2024 Lunatixz
#
#
# This file is part of Smartplaylist Generator.
#
# Smartplaylist Generator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smartplaylist Generator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-
from globals    import *

class Service():
    def __init__(self):
        self.log('__init__')
        self.monitor = MONITOR()
        
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def _start(self):
        self.log('_start')
        while not self.monitor.abortRequested():
            if    self.monitor.waitForAbort(300): break
            else: self._run()
        
        
    def _run(self):
        run_every = int(REAL_SETTINGS.getSetting('Run_Every').replace(LANGUAGE(32013),'0'))
        if run_every > 0:
            last_update = strpTime(REAL_SETTINGS.getSetting('Last_Update'))
            run_seconds = ((run_every * 3600) + 1800) #service run time in seconds with 30min padding to allow cache time to clear before run
            now_time    = datetime.datetime.now()
            run_time    = (last_update + datetime.timedelta(seconds=run_seconds))
            if now_time >= run_time:
                self.log('_run, now = %s, run = %s, running = %s'%(now_time,run_time,now_time >= run_time))
                self.kodi.executebuiltin('RunScript(special://home/addons/%s/resources/lib/default.py, Run_All)'%(ADDON_ID))
        
if __name__ == '__main__': Service()._start()
