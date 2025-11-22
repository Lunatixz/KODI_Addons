#   Copyright (C) 2025 Lunatixz, embql
#
#
# This file is part of Unsplash Photo ScreenSaver.
#
# Unsplash Photo ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Unsplash Photo ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Unsplash Photo ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import json, os, random, datetime, itertools, requests, logging

from six.moves     import urllib # type: ignore
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode # type: ignore

# Plugin Info
ADDON_ID       = 'screensaver.unsplash'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString
KODI_MONITOR   = xbmc.Monitor()

API_KEY        = REAL_SETTINGS.getSetting("APIKey")
ENABLE_KEYS    = REAL_SETTINGS.getSetting("Enable_Keys") == 'true'
KEYWORDS       = "" if not ENABLE_KEYS else urllib.parse.quote(REAL_SETTINGS.getSetting("Keywords"))
USER           = REAL_SETTINGS.getSetting("User").replace('@','')
COLLECTION     = REAL_SETTINGS.getSetting("Collection")
CATEGORY       = urllib.parse.quote(REAL_SETTINGS.getSetting("Category"))

BASE_URL       = 'https://api.unsplash.com'
RES            = ['1280x720','1920x1080','3840x2160'][int(REAL_SETTINGS.getSetting("Resolution"))]
RES_PARAMS     = ['w=1280&h=720','w=1920&h=1080','w=3840&h=2160'][int(REAL_SETTINGS.getSetting("Resolution"))]

TYPE_PARAMS    = ['photos?{resp}', 
                'collections/{cid}/photos?{resp}', 
                'photos/random?{keyword}{resp}', 
                'photos/random?featured&{keyword}{resp}', 
                'users/{user}/photos?{resp}', 
                'users/{user}/likes?{resp}', 
                'collections/{cid}/photos?{resp}', 
                'search/photos?query={cat}&{resp}'][int(REAL_SETTINGS.getSetting("PhotoType"))]

URL_PARAMS     = ('%s/%s' % (BASE_URL, TYPE_PARAMS)).format(
                    res=RES,
                    keyword=KEYWORDS,
                    user=USER,
                    cid=COLLECTION,
                    cat=CATEGORY,
                    resp=RES_PARAMS
                )

IMAGE_URL      = f'{URL_PARAMS}&client_id={API_KEY}'
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
IMG_CONTROLS   = [30000,30001]
CYC_CONTROL    = itertools.cycle(IMG_CONTROLS).__next__ #py3

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.isExiting = False
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
            
                        
    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
        try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception as e:
            self.log("notificationDialog Failed! " + str(e), xbmc.LOGERROR)
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
         
         
    def onInit(self):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('unsplash_animation', 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope')
        self.winid.setProperty('unsplash_time', 'okay' if REAL_SETTINGS.getSetting("Time") == 'true' else 'nope')
        self.winid.setProperty('unsplash_overlay', 'okay' if REAL_SETTINGS.getSetting("Overlay") == 'true' else 'nope')
        # Initialize pagination
        self.page   = 1
        self.images = self.openURL(IMAGE_URL, self.page)
        self.startRotation()

         
    def setImage(self, id, images):
        if images:
            current_image = random.choice(images)  # Pick a random image
            if current_image and current_image.startswith("http"):
                self.log(f"Setting image: {current_image}")  # Log the valid URL of the image being set
                self.getControl(id).setImage(current_image)
            else:
                self.log(f"Invalid image URL: {current_image}", xbmc.LOGERROR)
        else:
            self.log("No images available", xbmc.LOGERROR)


    def startRotation(self):
        self.currentID = IMG_CONTROLS[0]
        self.nextID = IMG_CONTROLS[1]

        if not self.images:
            self.log("No images available to display.", xbmc.LOGERROR)
            return

        while not KODI_MONITOR.abortRequested():
            # Set the current image if available
            if self.images:
                self.setImage(self.currentID, self.images)  # Passing all the images

            self.getControl(self.nextID).setVisible(False)
            self.getControl(self.currentID).setVisible(True)
            self.nextID = self.currentID
            self.currentID = CYC_CONTROL()

            if KODI_MONITOR.waitForAbort(TIMER) or self.isExiting:
                break


    def onAction(self, action):
        self.log("onAction")
        self.isExiting = True
        self.close()

    
    def openURL(self, url, page=1):
    try:
        # Detect random endpoint
        if "photos/random" in url:
            # Use count instead of per_page
            paginated_url = f'{url}&count=20'
        else:
            # Normal list endpoints still use page + per_page
            paginated_url = f'{url}&page={page}&per_page=20'

        self.log(f"Fetching URL: {paginated_url}")
        request = urllib.request.Request(paginated_url)
        request.add_header('Authorization', f'Client-ID {API_KEY}')
        request.add_header('User-Agent', 'Mozilla/5.0')

        response = urllib.request.urlopen(request, timeout=15)
        data = json.load(response)

        # Handle different response shapes
        if isinstance(data, dict) and 'urls' in data:
            # Single photo object
            image_urls = [data['urls']['full']]
        elif isinstance(data, list):
            # Array of photo objects (random with count, or list endpoints)
            image_urls = [item['urls']['full'] for item in data if 'urls' in item]
        elif 'results' in data:
            # Search endpoint
            image_urls = [item['urls']['full'] for item in data['results'] if 'urls' in item]
        else:
            image_urls = []

        self.log(f"Retrieved {len(image_urls)} images")
        return image_urls

    except Exception as e:
        self.log(f"openURL Failed on page {page}! Error: {str(e)}", xbmc.LOGERROR)
        return []











