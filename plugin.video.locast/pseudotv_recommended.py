#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of Locast.
#
# Locast is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Locast is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Locast.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
"""PseudoTV Live / IPTV Manager Integration module"""
import os, re, json, time
import traceback
from kodi_six      import xbmc, xbmcaddon, xbmcgui
from six.moves     import urllib

# Plugin Info
ADDON_ID      = 'plugin.video.locast'
PROP_KEY      = 'PseudoTV_Recommended.%s'%(ADDON_ID)
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
MONITOR       = xbmc.Monitor()
PLAYER        = xbmc.Player()
WINDOW        = xbmcgui.Window(10000)

## GLOBALS ##
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
  
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg), level)

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text    
    
class Locast_service(object):
    def __init__(self, sysARG=sys.argv):
        log('__init__ Locast_service, sysARG = %s'%(sysARG))
        self.pseudoTV_ok = True
        self.pseudoTV_nextruntime = 0
        WINDOW.setProperty("locast-last-id-played","")
        self.REFRESH_TIME  = int(REAL_SETTINGS.getSetting('Free_RefreshRate'))

    def regPseudoTV(self):
        log("regPseudoTV")
        if not self.pseudoTV_ok: return self.REFRESH_TIME
        now = int(time.time())
        if self.pseudoTV_nextruntime > now: return self.pseudoTV_nextruntime - now
        WAIT_TIME = 60
        if (xbmc.getCondVisibility('System.HasAddon(service.iptv.manager)') and xbmc.getCondVisibility('System.HasAddon(plugin.video.pseudotv.live)')):
            try:
                # Manager Info
                IPTV_MANAGER = xbmcaddon.Addon(id='service.iptv.manager')
                IPTV_PATH    = IPTV_MANAGER.getAddonInfo('profile')
                IPTV_M3U     = os.path.join(IPTV_PATH,'playlist.m3u8')
                IPTV_XMLTV   = os.path.join(IPTV_PATH,'epg.xml')
            except Exception as e:
                log('regPseudoTV failed! %s'%(e),level=xbmc.LOGERROR)
                self.pseudoTV_ok = False
            
            if REAL_SETTINGS.getSettingBool('iptv.enabled'):
                asset = {'iptv':{'type':'iptv','name':ADDON_NAME,'icon':ICON.replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID)).replace('\\','/'),'m3u':{'path':IPTV_M3U,'slug':'@%s'%(slugify(ADDON_NAME))},'xmltv':{'path':IPTV_XMLTV},'id':ADDON_ID}}
                WINDOW.setProperty(PROP_KEY, json.dumps(asset))
                WAIT_TIME = 900
            else:
                WINDOW.clearProperty(PROP_KEY)
                WAIT_TIME = 300
        self.pseudoTV_nextruntime = now + WAIT_TIME
        return WAIT_TIME

            
    def refreshStream(self):
        self.REFRESH_TIME  = int(REAL_SETTINGS.getSetting('Free_RefreshRate'))
        log("refreshStream, REFRESH_TIME=%s, type=%s"%(self.REFRESH_TIME,str(type(self.REFRESH_TIME))))
        newwaittime = self.REFRESH_TIME
        id = WINDOW.getProperty("locast-last-id-played")
        if REAL_SETTINGS.getSetting('User_Donate').lower() == 'false' and id != "":
            last_netloc = WINDOW.getProperty("locast-last-netloc")
            try:
                playingfile = PLAYER.getPlayingFile()
            except:
                playingfile = ""
            log("refreshStream last_netloc=%s, playingfile=%s"%(last_netloc,playingfile))
            if WINDOW.getProperty("locast-last-netloc").lower() in playingfile:
                starttime = int(WINDOW.getProperty("locast-last-startime"))
                now = int(time.time())
                newwaittime = starttime + self.REFRESH_TIME - now
                if newwaittime <= 0:
                    opt = WINDOW.getProperty("locast-last-opt-played")
                    # Note: I use a different plugin path each time otherwise Kodi gets confused
                    # after being asked to replay previous plugin that is still currently playing
                    url = 'plugin://%s/refresh/%s/%s/%s'%(ADDON_ID,opt,id,str(now))
                    newwaittime = self.REFRESH_TIME
                    log("refreshStream, id=%s, opt=%s, url=%s"%(id,opt,url))
                    PLAYER.play(url)
        return newwaittime
        
    def main_loop(self):
        log('Locast_service main_loop - starting')
        while not MONITOR.abortRequested():
            if MONITOR.waitForAbort(min(self.regPseudoTV(),self.refreshStream())):
                # Abort was requested while waiting. We should exit
                break
        log('Locast_service main_loop - ending')
        
if __name__ == '__main__': Locast_service(sys.argv).main_loop()
