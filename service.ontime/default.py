#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of OnTime
#
# OnTime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OnTime is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OnTime.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, re, config
import xbmc, xbmcplugin, xbmcaddon, xbmcgui, xbmcvfs

from utils import *

class Default(object):
    def __init__(self, sysARG):
        log('__init__, sysARG = ' + str(sysARG))
        self.sysARG = sysARG
    
    def getParams(self):
        return dict(urllib.parse.parse_qsl(self.sysARG[2][1:]))

                
    def run(self):  
        params=self.getParams()
        try: mode=int(params["mode"])
        except: mode=None
        try: tag=int(params["tag"])
        except: tag=None
        log("Mode: "+str(mode))
        log("Tag: " +str(tag))
        
        if mode==None:  config.OnTime()
        elif mode == 'removeEvent': removeEventTag()
        
if __name__ == '__main__': Default(sys.argv).run()