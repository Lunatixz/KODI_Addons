#   Copyright (C) 2019 Lunatixz
#
#
# This file is part of NASA - Images of the Day ScreenSaver.
#
# NASA - Images of the Day ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NASA - Images of the Day ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NASA - Images of the Day ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import sys, json, urllib, urllib2, socket, random
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

from simplecache import SimpleCache, use_cache

# Plugin Info
ADDON_ID       = 'screensaver.nasa'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
ENABLE_KEYS    = REAL_SETTINGS.getSetting("Enable_Keys") == 'true'
IMG_URL        = 'https://www.nasa.gov/sites/default/files/styles/full_width_feature/public/'
POTD_URL       = 'https://www.nasa.gov/api/2/ubernode/_search?size=24&from=0&sort=promo-date-time%3Adesc&q=((ubernode-type%3Aimage)%20AND%20(routes%3A1446))&_source_include=promo-date-time%2Cmaster-image%2Cnid%2Ctitle%2Ctopics%2Cmissions%2Ccollections%2Cother-tags%2Cubernode-type%2Cprimary-tag%2Csecondary-tag%2Ccardfeed-title%2Ctype%2Ccollection-asset-link%2Clink-or-attachment%2Cpr-leader-sentence%2Cimage-feature-caption%2Cattachments%2Curi'
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
RANDOM         = REAL_SETTINGS.getSetting("Randomize") == 'true'
ANIMATION      = 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope'
KODI_MONITOR   = xbmc.Monitor()

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.cache = SimpleCache()
        self.isExiting = False
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
        
        
    def onInit( self ):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('nasa_animation', ANIMATION)
        self.PanelItems = self.getControl(101)
        results = self.openURL(POTD_URL)
        if 'hits' not in results: return False
        for image in [result.get('_source','') for result in results['hits'].get('hits',[])]: self.PanelItems.addItem(xbmcgui.ListItem(self.ascii((image.get('cardfeed-title','') or image.get('title','')).strip('\n\t\r')),self.ascii((image.get('image-feature-caption','') or image.get('','')).strip('\n\t\r')),thumbnailImage=(image['master-image']['uri']).replace('public://',IMG_URL)))
        self.startRotation()
        
        
    def startRotation(self):
        while not KODI_MONITOR.abortRequested():
            xbmc.executebuiltin('SetFocus(101)')
            if KODI_MONITOR.waitForAbort(TIMER) == True or self.isExiting == True: break
            seek = str(random.randint(1,27)) if RANDOM == True else '1'
            xbmc.executebuiltin("Control.Move(101,%s)"%seek)
        
        
    def onFocus( self, controlId ):
        pass
    
   
    def onClick( self, controlId ):
        pass

        
    def onAction( self, action ):
        self.isExiting = True
        self.close()
        

    def uni(self, string, encoding='utf-8'):
        if isinstance(string, basestring):
            if not isinstance(string, unicode):
               string = unicode(string, encoding)
        return string

        
    def ascii(self, string):
        if isinstance(string, basestring):
            if isinstance(string, unicode):
               string = string.encode('ascii', 'ignore')
        return string
                
              
    def loadJson(self, string):
        try: return json.loads(self.uni(string))
        except: return {}
          

    @use_cache(1)
    def openURL(self, url):
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11')
            page = urllib2.urlopen(request, timeout = 15)
            return self.loadJson(page.read())
        except Exception as e: return {}