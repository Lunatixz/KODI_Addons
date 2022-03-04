#   Copyright (C) 2022 Lunatixz
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
import time, traceback, json, os, platform, pathlib, re, datetime
from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs

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

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg = '%s, %s'%(msg,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,str(msg)),level)
    
def isDayOld(file):
    now = datetime.datetime.now()
    try:
        fname = pathlib.Path(xbmcvfs.translatePath(file))
        mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime)
    except:
        mtime = now
    return mtime < (now + datetime.timedelta(days=1))

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)

class Service(object):
    myMonitor = Monitor()
    
    def cleanBuffer(self):
        try:    items = xbmcvfs.listdir(PVR_USERDATA)[1]
        except: items = []
        for item in items:
            match = re.compile(r"^channelsdvr-buffer(.+?)\.mpg", re.IGNORECASE).search(item)
            file  = os.path.join(PVR_USERDATA,item)
            if match and isDayOld(file):
                try:    
                    xbmcvfs.delete(file)
                    log('cleanBuffer, cleaning file = %s'%(file))
                except: pass
    
        
    def startService(self):
        log('startService')
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(900): break
            self.cleanBuffer()
            
if __name__ == '__main__': Service().startService()