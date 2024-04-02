#   Copyright (C) 2024 Lunatixz
#
#
# This file is part of System 47 Live in HD Screensaver.
#
# System 47 Live in HD Screensaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# System 47 Live in HD Screensaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with System 47 Live in HD Screensaver.  If not, see <http://www.gnu.org/licenses/>.

import os, random, traceback, json, base64, datetime
# import youtube_registration # https://github.com/jdf76/plugin.video.youtube/issues/184

from kodi_six    import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs

# youtube_registration.register_api_keys(addon_id=ADDON_ID,
                                       # api_key=base64.urlsafe_b64decode(REAL_SETTINGS.getSetting('AKEY')),
                                       # client_id= base64.urlsafe_b64decode(REAL_SETTINGS.getSetting('CKEY')),
                                       # client_secret=base64.urlsafe_b64decode(REAL_SETTINGS.getSetting('SKEY')))
            
# Plugin Info
ADDON_ID      = 'screensaver.system47'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
ACTION_STOP   = 13
MUTE          = REAL_SETTINGS.getSetting('Enable_Mute') == 'true'
RANDOM        = REAL_SETTINGS.getSetting('Enable_Random') == 'true'
FILENAME      = 'screensaver.system47.v.2.5.01.mp4'

# https://www.youtube.com/@system47
YTID_LST      = ['N9Sxyvz4lW4','TepWfVIaWv8','6mTleQJn1Cc','qiIuv9RXq2c','X3tKtrqsSBg','Kxrj7PYJMQY','l8Jzp_JaL0E',
                 'MptItr7LfS4','yL4D7rIJAc0','NjFjB1Ibuow','LGg6j0LbelM','LEQ9m5IgfIc','9nJlJQ5_o5E','9XtYJmSu5oY']

def log(msg, level = xbmc.LOGDEBUG):
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg), xbmc.LOGERROR)
     
def getDate():
    return datetime.datetime.now().strftime('%m-%d')

def getURL():
    YTID = random.choice({'11-23':['XY7qveGGSh0'],'12-25':['7h5n7IjR08M']}.get(getDate(),YTID_LST))
    log('getURL, YTID = ' + str(YTID))
    if xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube)') and xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.youtube)'):
        return 'plugin://plugin.video.youtube/play/?video_id=%s&suggested=false&incognito=true'%(YTID)
    elif xbmc.getCondVisibility('System.HasAddon(plugin.video.tubed)') and xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.tubed)'):
        return 'plugin://plugin.video.tubed/?mode=play&video_id=%s'%(YTID)
    elif xbmc.getCondVisibility('System.HasAddon(plugin.video.invidious)') and xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.invidious)'):
        return 'plugin://plugin.video.invidious/?mode=play_video&video_id=%s'%(YTID)
    elif xbmc.getCondVisibility('System.HasAddon(plugin.video.invidious)') and xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.invidious)'):
        return 'plugin://plugin.video.invidious/?mode=play_video&video_id=%s'%(YTID)
    else:
        xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30004), ICON, 4000)
       
def isMute():
    state = False
    json_query = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["muted"]},"id":1}'
    json_response = json.loads(xbmc.executeJSONRPC(json_query))
    if json_response and 'result' in json_response: state = json_response['result']['muted']
    log('isMute, state = ' + str(state))
    return state
    
def setMute(state):
    log('setMute, state = ' + str(state))
    if isMute() == state: return
    json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":%s},"id":1}'%str(state).lower()
    json_response = json.loads(xbmc.executeJSONRPC(json_query))
    
    
class Player(xbmc.Player):
    def onAVStarted(self):
        log('onAVStarted')
        xbmc.Monitor().waitForAbort(5.0)
        totalTime = self.getTotalTime()
        seekValue = int(totalTime//(random.randint(5,(totalTime//4)))) if RANDOM else 0
        if seekValue > 5: xbmc.executebuiltin('Seek(%s)'%seekValue)

        
class BackgroundWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.myPlayer = Player()
        self.myPlayer.Background = self
        if MUTE: setMute(True)
    
    
    def playFile(self):
        if REAL_SETTINGS.getSetting('Playlist') == '0':
            return getURL()
        elif xbmcvfs.exists(os.path.join(SETTINGS_LOC,FILENAME)):
            return os.path.join(SETTINGS_LOC,FILENAME)
        else:
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30009), ICON, 4000)
        
        
    def onInit(self):
        xbmc.executebuiltin("PlayerControl(repeatone)")
        # xbmcgui.Window(10000).setProperty('plugin.video.youtube-configs', CONFIGS)
        self.myPlayer.play(self.playFile())
    
        
    def onAction(self, act):
        self.closeBackground()
        
        
    def closeBackground(self):
        log('closeBackground')
        self.myPlayer.stop()
        # xbmcgui.Window(10000).clearProperty('plugin.video.youtube-configs')
        xbmc.executebuiltin("PlayerControl(repeatoff)")
        if MUTE: setMute(False)
        self.close()
        
      
class Start(object):
    def __init__(self):
        self.background = BackgroundWindow('%s.background.xml'%ADDON_ID, ADDON_PATH, "Default", windowed=True)
        self.background.doModal()
        
if __name__ == '__main__': Start()

#todo save state settings, and play queue

        # {
            # "control": {
                # "delayed": false,
                # "format": "boolean",
                # "type": "toggle"
            # },
            # "default": true,
            # "enabled": false,
            # "help": "If music is being played, the screensaver will never be activated",
            # "id": "screensaver.disableforaudio",
            # "label": "Disable screensaver when playing audio",
            # "level": "basic",
            # "parent": "",
            # "type": "boolean",
            # "value": true
        # },
        # {
            # "control": {
                # "delayed": false,
                # "format": "boolean",
                # "type": "toggle"
            # },
            # "default": true,
            # "enabled": false,
            # "help": "Dim the display when media is paused. Not valid for the \"Dim\" screensaver mode.",
            # "id": "screensaver.usedimonpause",
            # "label": "Use dim if paused during video playback",
            # "level": "standard",
            # "parent": "",
            # "type": "boolean",
            # "value": true
        # },