#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of Channels PVR Cleaner
#
# Channels PVR Cleaner is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Channels PVR Cleaner is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Channels PVR Cleaner.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-
import time, traceback, json, os, platform
import xbmc, xbmcgui, xbmcvfs, xbmcaddon

# Plugin Info
ADDON_ID            = 'service.pvr.channels.cleaner'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE            = REAL_SETTINGS.getLocalizedString
DEBUG               = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'

PVR_ID              = 'pvr.channelsdvr'
PVR_USERDATA        = os.path.join('special://profile','addon_data',PVR_ID,'')
PVR_ATTRIBUTE       = 'channelsdvr-buffer'
PVR_EXTENSTION      = '.mpg'

try:
  basestring      #py2
except NameError: #py3
  basestring = str
  unicode = str
  
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg = '%s, %s'%(uni(msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,uni(msg)),level)
    
def uni(string, encoding='utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode): string = unicode(string, encoding)
        else: string = string.encode('ascii', 'ignore')
    return string

def creationTime(path):
    if platform.system() == 'Windows': return os.path.getctime(path)
    else:
        stat = os.stat(path)
        try: return stat.st_birthtime
        except AttributeError: return stat.st_mtime
            
class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)


class Service(object):
    def __init__(self):
        self.myMonitor = Monitor()
        self.myPlayer  = Player()
        self.myMonitor.myService = self
        self.myPlayer.myService  = self
        
        
    def cleanBuffer(self):
        log('cleanBuffer')
        try: items = xbmcvfs.listdir(PVR_USERDATA)
        except: items = [],[]
        for item in items[1]:
            #todo delete old files, for now clean all files except for file in-use.
            try: xbmcvfs.delete(os.path.join(PVR_USERDATA,item))
            except: pass
            # if item.startswith(PVR_ATTRIBUTE) and item.endswith(PVR_EXTENSTION): # replace with regex?
                # print creationTime(os.path.join(xbmc.translatePath(PVR_USERDATA),item))
        
        
    def startService(self):
        log('startService')
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(60): break
            self.cleanBuffer()
            # if not self.myPlayer.isPlaying(): continue #ignore when not playing
if __name__ == '__main__': Service().startService()