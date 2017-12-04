#   Copyright (C) 2016 Lunatixz
#
#
# This file is part of PseudoCinema Poster.
#
# PseudoCinema Poster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoCinema Poster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoCinema Poster.  If not, see <http://www.gnu.org/licenses/>.


#setting options
#trakt, imdb, rot tomato support, change image rotation, change marquee/sign image, enter marquee text, enable pseudo "onnow" banners

#todo
#autostart, detect kodi res, add trailers, custom marquee, event triggers, pseudotv onnow, random posters, random trailers, next airing, transition anim.
import threading, random
import re, os, sys
import json, urllib, requests
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

# Plugin Info
ADDON_ID = 'script.pseudocinema.poster'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON = os.path.join(ADDON_PATH, 'icon.png')
FANART = os.path.join(ADDON_PATH, 'fanart.jpg')

class MOVIEPOSTER(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log('init')  
        self.kodiPlayer = -1
        self.setProperty('MOVIEPOSTER.Background','Splash.png')
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        
        #settings
        self.refresh_timer = float(REAL_SETTINGS.getSetting("refresh_timer"))
        self.enable_animated = REAL_SETTINGS.getSetting("enable_animated") == "true"
        self.ignore_playing = REAL_SETTINGS.getSetting("ignore_playing") == "true"
        self.include_kodidb = REAL_SETTINGS.getSetting("include_kodidb") == "true"
        self.KODI = REAL_SETTINGS.getSetting("IPPORT").split(':')[0]
        self.PORT = int(REAL_SETTINGS.getSetting("IPPORT").split(':')[1])
        self.USER = REAL_SETTINGS.getSetting("USERPASS").split(':')[0]
        self.PASS = REAL_SETTINGS.getSetting("USERPASS").split(':')[1]
        
        self.refreshPosterTimer = threading.Timer(self.refresh_timer, self.refreshPoster) 
        
        
    def onInit(self):
        self.log('onInit')
        self.setProperty('MOVIEPOSTER.Background','Background.png')
        self.refreshPoster()
            
    def onAction(self, act):
        action = act.getId()
        self.log('onAction ' + str(action))
        if action in [1,2,3,4]:
            self.fillMeta(self.getRandomPoster(),'moviedetails')
        elif action in [9, 10, 92, 247, 257, 275, 61467, 61448]:
            self.close()

    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)

    def getProperty(self, str):
        try:
            return xbmcgui.Window(10000).getProperty(str)
        except Exception,e:
            return ''
              
    def setProperty(self, str1, str2):
        try:
            xbmcgui.Window(10000).setProperty(str1, str2)
        except Exception,e:
            pass
            
    def clearProperty(self, str):
        xbmcgui.Window(10000).clearProperty(str)
        
    def refreshPoster(self):
        self.log('refreshPoster')
        if self.refreshPosterTimer.isAlive():
            self.refreshPosterTimer.cancel()
            
        self.kodiPlayer = self.isKodiPlaying()
        if self.kodiPlayer >= 0 and self.ignore_playing == False:
            self.fillMeta(self.getKodiPlaying(self.kodiPlayer),'item')
        else:
            self.fillMeta(self.getRandomPoster(),'moviedetails')
            
        self.refreshPosterTimer = threading.Timer(self.refresh_timer, self.refreshPoster)
        self.refreshPosterTimer.name = "refreshPosterTimer"
        self.refreshPosterTimer.start()
        
    def fillMeta(self, data, type):
        self.log('fillMeta')
        try:
            poster = (data['result'][type]['art']['poster']).rstrip('/')
        except:
            try:
                poster = (data['result'][type]['art']['tvshow.poster']).rstrip('/')
            except:
                poster = (data['result'][type]['thumbnail']).rstrip('/')
        
        #setprops
        if self.enable_animated:
            self.setProperty('SkinHelper.EnableAnimatedPosters','true')
            self.setProperty('MOVIEPOSTER.Poster',('http://localhost:52307/getanimatedposter&amp;imdbid=%s&amp;fallback=%s' %poster))
        else:
            self.setProperty('MOVIEPOSTER.Poster',poster)     
        try:
            self.setProperty('MOVIEPOSTER.Title',((data['result'][type]['title'])) or ((data['result'][type]['label'])))
            self.setProperty('MOVIEPOSTER.Year',((data['result'][type]['year'])))
            self.setProperty('MOVIEPOSTER.MPAA',((data['result'][type]['mpaa'])))
            self.setProperty('MOVIEPOSTER.Rating',((data['result'][type]['rating'])))
            self.setProperty('MOVIEPOSTER.IMDBID',((data['result'][type]['imdbnumber'])))
            self.setProperty('MOVIEPOSTER.Genre',((data['result'][type]['genre']))[0])
            self.setProperty('MOVIEPOSTER.Trailer',((data['result'][type]['trailer'])))
            self.setProperty('MOVIEPOSTER.Tagline',((data['result'][type]['tagline'])) or ((data['result'][type]['plotoutline'])) or ((data['result'][type]['plot']).split('.'))[0])
            self.setProperty('MOVIEPOSTER.Video.Steromode',((data['result'][type]['streamdetails']))['video'][0]['stereomode'])
            self.setProperty('MOVIEPOSTER.Video.Width',((data['result'][type]['streamdetails']))['video'][0]['width'])
            self.setProperty('MOVIEPOSTER.Video.Codec',((data['result'][type]['streamdetails']))['video'][0]['codec'])
            self.setProperty('MOVIEPOSTER.Video.Aspect',((data['result'][type]['streamdetails']))['video'][0]['aspect'])
            self.setProperty('MOVIEPOSTER.Audio.Channels',((data['result'][type]['streamdetails']))['audio'][0]['channels'])
            self.setProperty('MOVIEPOSTER.Audio.Codec',((data['result'][type]['streamdetails']))['audio'][0]['codec'])
            self.setProperty('MOVIEPOSTER.Audio.Language',((data['result'][type]['streamdetails']))['audio'][0]['language'])
        except:
            pass
            
    # These two methods construct the JSON-RPC message and send it to the Kodi player
    def SendCommand(self, command):
        command = json.dumps(command)
        self.log("SendCommand, command = " + command)
        # Change this to the IP address of your Kodi server or always pass in an address

        url = "http://%s:%d/jsonrpc" % (self.KODI, self.PORT)
        try:
            r = requests.post(url, data=command, auth=(self.USER, self.PASS))
        except:
            return {}
        return json.loads(r.text)

    def isKodiPlaying(self):
        result = self.SendCommand({"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1})
        try:
            r = result['result'][0]['playerid']
        except:
            r = -1
        self.log("isKodiPlaying = " + str(r))
        return r

    def getKodiPlaying(self, playerid):
        self.log('getKodiPlaying')
        self.setProperty('MOVIEPOSTER.Marquee','Now Playing.png')
        return self.SendCommand({"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":playerid,"properties":["title","genre","year","rating","trailer","tagline","plotoutline","plot","studio","mpaa","country","imdbnumber","runtime","streamdetails","top250","votes","season","episode","showtitle","art","thumbnail","file"]},"id":1})

    def getMaxDBID(self):
        result = self.SendCommand({"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{},"id":1})
        try:
            r = int(result['result']['limits']['total'])
        except:
            r = 0
        self.log("getMaxDBID = " + str(r))
        return r

    def getMovieDetails(self, dbid):
        self.log('getMovieDetails, dbid = ' + str(dbid))
        return self.SendCommand({"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails","params":{"movieid":dbid,"properties":["title","genre","year","rating","trailer","tagline","plotoutline","plot","studio","mpaa","country","imdbnumber","runtime","streamdetails","top250","votes","art","thumbnail","file"]},"id":1})

    def fillKodiMovies(self):
        self.log('fillKodiMovies')
        return self.SendCommand({"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":["title","genre","year","rating","trailer","tagline","plotoutline","plot","studio","mpaa","country","imdbnumber","runtime","streamdetails","top250","votes","art","thumbnail","file"]},"id":1})

    def getRandomKodiMovie(self):
        self.log('getRandomKodiMovie')
        result = self.getMovieDetails(random.randrange(self.getMaxDBID()))
        try:
            result = (result['error']['message'])
            result = self.getRandomKodiMovie()
            return result
        except:
            return result

    def fillRandomPoster(self):
        self.log('fillRandomPoster')
        items = []
        if self.include_kodidb:
            items.append(self.getRandomKodiMovie())
            #todo imdb,trakt popular, coming soon, etc
        return items

    def getRandomPoster(self):
        self.log('getRandomPoster')
        self.setProperty('MOVIEPOSTER.Marquee','Coming Soon.png')
        items = self.fillRandomPoster()
        return items[0]
     
myMOVIEPOSTER = MOVIEPOSTER("script.pseudocinema.poster.xml", ADDON_PATH, 'default')
myMOVIEPOSTER.doModal()
del myMOVIEPOSTER