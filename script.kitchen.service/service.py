#   Copyright (C) 2016 Lunatixz
#
#
# This file is part of Kitchen Service.
#
# Kitchen Service is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Kitchen Service is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitchen Service.  If not, see <http://www.gnu.org/licenses/>.

import os, xbmc, xbmcgui, xbmcaddon, xbmcvfs, string, re
from datetime import datetime, time

# Plugin Info
ADDON_ID = 'script.kitchen.service'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC = REAL_SETTINGS.getAddonInfo('profile')
THUMB = (xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'images')) + '/' + 'icon.png')
NIGHTTIME = False
MUTE = False

def log(msg, level = xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + uni(msg), level)
  
def uni(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('utf-8', 'ignore' )
    return string

def sendJSON(command):
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))
    return uni(data)
    
def isMute():
    json_query = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["muted"]},"id":1}'
    details = sendJSON(json_query)
    state = (re.search('"muted":(.*)',re.compile( "{(.*?)}", re.DOTALL ).findall(details)[0])).group(1) == 'true'
    log("isMute = " + str(state))
    return state
      
def toggleMute():
    log("toggleMute")
    json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":"toggle"},"id":1}'
    sendJSON(json_query)

def setMute(state):
    while isMute() != bool(state):
        log("setMute = " + str(state))
        json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":%s},"id":1}' %str(state).lower()
        sendJSON(json_query)
        xbmc.sleep(10)

def setVolume(val):
    log("setMute = " + str(val))
    json_query = '{"jsonrpc":"2.0","method":"Application.SetVolume","params":{"volume":%s},"id":1}' %str(val)
    sendJSON(json_query)
   
def pingHost(hostname):   
    hostname_alive = os.system("ping -c 1 " + hostname) == 0
    log("pingHost, hostname_alive = " + str(hostname_alive))
    return hostname_alive
            
def pingKodi(hostname):
    log("pingKodi")
            
def isNight():
    now = datetime.now()
    now_time = now.time()
    if now_time >= time(22,00) or now_time <= time(9,00):
        return True
    return False
    
monitor = xbmc.Monitor()
while not monitor.abortRequested():
    # Sleep/wait for abort for 1 seconds
    if monitor.waitForAbort(int(REAL_SETTINGS.getSetting("Poll_TIME"))):
        # Abort was requested while waiting. We should exit
        break
        
    if isNight() == True and NIGHTTIME == False:
        NIGHTTIME = True
        setVolume(int(REAL_SETTINGS.getSetting("Night_VOL")))
    elif isNight() == False and NIGHTTIME == True:
        NIGHTTIME = False
        setVolume(int(REAL_SETTINGS.getSetting("Day_VOL")))
        
    if REAL_SETTINGS.getSetting("Toggle_MUTE") == 'true':
        if pingHost(REAL_SETTINGS.getSetting("IP")) == False:
            setMute(False)
        else:
            setMute(True)