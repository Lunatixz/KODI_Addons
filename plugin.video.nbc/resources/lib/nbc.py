#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of NBC.
#
# NBC is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NBC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NBC.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import sys, time, datetime, re, traceback
import urllib, urllib2, socket, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from youtube_dl import YoutubeDL
from simplecache import SimpleCache

# Plugin Info
ADDON_ID      = 'plugin.video.nbc'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
TIMEOUT       = 15
CONTENT_TYPE  = 'files'
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
BASE_URL      = 'http://www.nbc.com'
SHOW_URL      = 'https://api.nbc.com/v3.14/aggregatesShowProperties/%s'
SHOWS_URL     = 'https://api.nbc.com/v3.14/shows?filter[active]=1&include=image&page[size]=30&sort=sortTitle'
VIDEO_URL     = 'https://api.nbc.com/v3.14/videos?filter[entitlement]=free&filter[published]=1&include=image&page[size]=30&sort=-airdate'
FILTER        = '&filter[%s]=%s'

MAIN_MENU = [("Latest Episodes", "", 1),
             ("Browse Shows", "", 2)]

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def getParams():
    param=[]
    if len(sys.argv[2])>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]
    return param
                 
socket.setdefaulttimeout(TIMEOUT)
class NBC(object):
    def __init__(self):
        log('__init__')
        self.cache = SimpleCache()
        self.ydl   = YoutubeDL()
           
           
    def openURL(self, url):
        log('openURL, url = ' + str(url))
        try:
            cacheResponce = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheResponce:
                request = urllib2.Request(url)
                responce = urllib2.urlopen(request, timeout = TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, responce, expiration=datetime.timedelta(hours=1))
            return self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
        except urllib2.URLError, e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
        except socket.timeout, e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
        except Exception, e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return ''
         
         
    def buildMenu(self, items):
        for item in items:
            self.addDir(*item)
        self.addYoutube("Browse Youtube" , 'plugin://plugin.video.youtube/user/NBC/')

            
    def browseEpisodes(self, url=None):
        log('browseEpisodes')
        if url is None:
            url = VIDEO_URL+FILTER%('type','Full%20Episode')
        items = json.loads(self.openURL(url))
        if items and 'data' in items:
            for item in items['data']:
                path      = item['attributes']['fullUrl']
                aired     = str(item['attributes']['airdate']).split('T')[0]
                duration  = int(item['attributes']['runTime'])
                plot      = item['attributes']['description']
                title     = item['attributes']['title']
                
                showTitle = '' 
                for show in item['attributes']['categories']: 
                    if show.startswith('Series'):
                        showTitle = show.split('Series/')[1]
                        break

                try: episodeNumber = int(item['attributes']['episodeNumber'])
                except: episodeNumber = 0
                try: seasonNumber = int(item['attributes']['seasonNumber'])
                except: seasonNumber  = 0
                
                try: 
                    thumb = ICON
                    for image in items['included']:
                        if image['id'] == item['relationships']['image']['data']['id']:
                            thumb = BASE_URL+image['attributes']['path']
                            break
                except: thumb = ICON
                
                seinfo = ('S' + ('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'E' + ('0' if episodeNumber < 10 else '') + str(episodeNumber))
                label  = '%s - %s'%(showTitle, title) if seasonNumber + episodeNumber == 0 else '%s - %s - %s'%(showTitle, seinfo, title)
                infoLabels ={"mediatype":"episodes","label":label ,"title":label,"TVShowTitle":showTitle,"plot":plot,"aired":aired,"duration":duration,"season":seasonNumber,"episode":episodeNumber}
                infoArt    ={"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
                self.addLink(label, path, 9, infoLabels, infoArt, len(items['data']))
                
            try: next_page = items['links']['next']
            except: next_page = None
            if next_page:
                 self.addDir('>> Next',next_page, 1)

                 
    def browseShows(self, url=None):
        log('browseShows')
        if url is None:
            url = SHOWS_URL
        items = json.loads(self.openURL(url))
        if items and 'data' in items:
            for item in items['data']:
                showTitle = item['attributes']['shortTitle']
                plot      = (item['attributes']['shortDescription'] or showTitle).replace('<p>','').replace('</p>','')
                path      = VIDEO_URL+FILTER%('show',item['id'])
                vidID     = item['relationships']['aggregates']['data']['id']

                try: 
                    thumb = ICON
                    for image in items['included']:
                        if image['id'] == item['relationships']['image']['data']['id']:
                            thumb = BASE_URL + image['attributes']['path']
                            break
                except: thumb = ICON
                
                myURL      = json.dumps({"url":path,"vidID":vidID})
                infoLabels ={"mediatype":"tvshows","label":showTitle ,"title":showTitle,"TVShowTitle":showTitle,"plot":plot}
                infoArt    ={"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
                self.addDir(showTitle,myURL,0,infoLabels,infoArt)

            try: next_page = items['links']['next']
            except: next_page = None
            if next_page:
                 self.addDir('>> Next',next_page, 2)
 

    def resolveURL(self, url):
        log('resolveURL')
        myURL = json.loads(url)
        items = json.loads(self.openURL(SHOW_URL%myURL['vidID']))
        if items and 'data' in items:
            for item in items['data']['attributes']['videoTypes']:
                self.browseEpisodes(myURL['url']+FILTER%('type',urllib2.quote(item)))
                
                
    def playVideo(self, name, url, liz=None):
        log('playVideo')
        self.ydl.add_default_info_extractors()
        with self.ydl:
            result = self.ydl.extract_info(url, download=False)
            url = result['manifest_url']
            liz = xbmcgui.ListItem(name, path=url)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)

            
    def addYoutube(self, name, url):
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'false')
        liz.setInfo(type="Video", infoLabels={"label":name,"title":name} )
        liz.setArt({'thumb':ICON,'fanart':FANART})
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz,isFolder=True)
        
           
    def addLink(self, name, u, mode, infoList=False, infoArt=False, total=0):
        name = name.encode("utf-8")
        log('addLink, name = ' + name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'true')
        if infoList == False:
            liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name,"genre":"News"})
        else:
            liz.setInfo(type="Video", infoLabels=infoList)
            
        if infoArt == False:
            liz.setArt({'thumb':ICON,'fanart':FANART})
        else:
            liz.setArt(infoArt)
        u=sys.argv[0]+"?url="+urllib.quote_plus(u)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,totalItems=total)


    def addDir(self, name, u, mode, infoList=False, infoArt=False):
        name = name.encode("utf-8")
        log('addDir, name = ' + name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'false')
        if infoList == False:
            liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name,"genre":"News"})
        else:
            liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False:
            liz.setArt({'thumb':ICON,'fanart':FANART})
        else:
            liz.setArt(infoArt)
        u=sys.argv[0]+"?url="+urllib.quote_plus(u)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)

params=getParams()
try:
    url=urllib.unquote_plus(params["url"])
except:
    url=None
try:
    name=urllib.unquote_plus(params["name"])
except:
    name=None
try:
    mode=int(params["mode"])
except:
    mode=None
    
log("Mode: "+str(mode))
log("URL : "+str(url))
log("Name: "+str(name))

if mode==None:  NBC().buildMenu(MAIN_MENU)
elif mode == 0: NBC().resolveURL(url)
elif mode == 1: NBC().browseEpisodes(url)
elif mode == 2: NBC().browseShows(url)
elif mode == 9: NBC().playVideo(name, url)

xbmcplugin.setContent(int(sys.argv[1])    , CONTENT_TYPE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_NONE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_LABEL)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_TITLE)
xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)