#   Copyright (C) 2016 Lunatixz
#
#
# This file is part of Smart Mirror.
#
# Smart Mirror is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smart Mirror is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Mirror.  If not, see <http://www.gnu.org/licenses/>.

import threading, random, datetime, time
import re, os, sys
import json, urllib, requests, feedparser
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

# Plugin Info
ADDON_ID = 'script.smart.mirror'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON = os.path.join(ADDON_PATH, 'icon.png')
FANART = os.path.join(ADDON_PATH, 'fanart.jpg')
KODI_MONITOR = xbmc.Monitor()

class MIRROR(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.clockMode = 0
        self.isExiting = False
        self.updateTimer = threading.Timer(1.0, self.update)
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
        
        
    def onInit(self):
        self.log('onInit')
        if self.updateTimer.isAlive() == False:
            self.updateTimer.start()
          
          
    def update(self):
        while not KODI_MONITOR.abortRequested():
            self.log('update')
            if self.isExiting == True:
                return
            time.sleep(1)
            #todo news fill every 15mins
            self.fillGreeting()
            self.setTimeLabels()
            self.fillNews()
            time.sleep(60)
            
          
    def onAction(self, act):
        action = act.getId()
        self.log('onAction ' + str(action))
        if action in [9, 10, 92, 247, 257, 275, 61467, 61448]:
            self.isExiting = True
            self.close()

            
    def getProperty(self, str):
        return xbmcgui.Window(10000).getProperty(str)
              
              
    def setProperty(self, str1, str2):
        xbmcgui.Window(10000).setProperty(str1, str2)
            
            
    def clearProperty(self, str):
        xbmcgui.Window(10000).clearProperty(str)

        
    def fillGreeting(self):
        # todo get user name
        name = 'Kevin'
        currentTime = datetime.datetime.now()
        if currentTime.hour < 12:
            string = 'Good morning.'
        elif 12 <= currentTime.hour < 18:
            string = 'Good afternoon.'
        else:
            string = 'Good evening.'
        self.setProperty('Mirror.GREETING',string)
        self.setProperty('Mirror.NAME',name)

        
    # set the time labels 24/12 hr
    def setTimeLabels(self):
        self.log('setTimeLabels')
        now = datetime.datetime.now()
        self.setProperty('Mirror.DAY',now.strftime('%A'))
        self.setProperty('Mirror.DATE',now.strftime('%B %d'))
        
        if self.clockMode == 0:
            self.setProperty('Mirror.TIME',now.strftime('%I:%M'))
        else:
            self.setProperty('Mirror.TIME',now.strftime('%H:%M'))

       
    def fillNews(self):
        #todo custom user rss feeds
        self.setProperty('Mirror.NEWS_1',self.feedparse('http://hosted2.ap.org/atom/APDEFAULT/3d281c11a96b4ad082fe88aa0db04305'))
        self.setProperty('Mirror.NEWS_2',self.feedparse('http://hosted2.ap.org/atom/APDEFAULT/cae69a7523db45408eeb2b3a98c0c9c5'))
        self.setProperty('Mirror.NEWS_3',self.feedparse('http://hosted2.ap.org/atom/APDEFAULT/495d344a0d10421e9baa8ee77029cfbd'))
        self.setProperty('Mirror.NEWS_4',self.feedparse('http://hosted2.ap.org/atom/APDEFAULT/b2f0ca3a594644ee9e50a8ec4ce2d6de'))
        
        
    def feedparse(self, url):
        d = feedparser.parse(url)
        header = (d['feed']['title'])
        post = d['entries'][0]['title']
        for post in d.entries:
            try:
                return post.title
            except:
                pass
        
        
myMIRROR = MIRROR("mirror_horizontal.xml", ADDON_PATH, 'default')
myMIRROR.doModal()
del myMIRROR
# http://hosted2.ap.org/APDEFAULT/APNewsFeeds feedparser
# https://api.darksky.net/forecast/17cca51f6418410bec179f6faf8604b8/37.8267,-122.4233 #enhanced weather api or kodi weather?
# https://pythonhosted.org/python-geoip/ loc by ip
# custom fonts todo
# custom icons todo
# user settings, rss feeds, weather source?, user name, 24/12 clock
# todo user select horizontal and vertical
# 720 skin
# media labels, ie playing title, poster, progress?
# other Kodi stats? recently added?
# trakt, sonarr, sickbeard, sabnzbd, couchpotato, headphone intergration ?