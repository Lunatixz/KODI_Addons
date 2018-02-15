#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of CBS News.
#
# CBS News is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CBS News is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CBS News.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import sys, time, datetime, re, traceback
import urlparse, urllib, urllib2, socket, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from simplecache import SimpleCache
from bs4 import BeautifulSoup
from YDStreamExtractor import getVideoInfo

# Plugin Info
ADDON_ID      = 'plugin.video.cbsn'
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
LIVEURL       = 'https://cbsn1.cbsistatic.com/live/'
VIDURL        = 'https://www.cbsnews.com/videos'
EPSURL        = 'https://www.cbsnews.com/%s/full-episodes/'
VIDMENU       = ['This Morning','48 Hours','60 Minutes','Sunday Morning','Face the Nation','Originals','Assignment']

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def getParams():
    return dict(urlparse.parse_qsl(sys.argv[2][1:]))
               
socket.setdefaulttimeout(TIMEOUT)
class CBSN(object):
    def __init__(self):
        log('__init__')
        self.cache = SimpleCache()

            
    def openURL(self, url):
        log('openURL, url = ' + str(url))
        try:
            cacheResponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheResponse:
                request = urllib2.Request(url)
                request.add_header('User-Agent','Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)')
                response = urllib2.urlopen(request, timeout=TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, response, expiration=datetime.timedelta(hours=6))
            return self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
        except urllib2.URLError, e: log("openURL Failed! " + str(e), xbmc.LOGERROR)
        except socket.timeout, e: log("openURL Failed! " + str(e), xbmc.LOGERROR)
        except Exception, e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return ''
             

    def buildMainMenu(self):
        self.addLink('Live'  ,'',0)
        self.addDir('Latest' ,'',1)
        self.addDir('Browse' ,'',2)
        self.addYoutube("Browse Youtube" , 'plugin://plugin.video.youtube/user/CBSNewsOnline/')
        
        
    def buildBrowse(self):
        for item in VIDMENU: self.addDir(item ,(EPSURL%urllib.quote_plus(item)),3)
        
    
    def buildLiveLink(self):
        urlbase = re.compile('contentUrl":"(.+?)"', re.DOTALL).search(self.openURL(LIVEURL)).group(1).replace('\/','/')
        self.playVideo('CBS News Live',urlbase)
            
    
    def buildLatest(self):
        results = json.loads('{'+re.compile("CBSNEWS.defaultPayload = {(.+?)};", re.DOTALL).search(self.openURL(LIVEURL)).group(1).split("CBSNEWS.defaultLayout")[0])
        if 'items' not in results: return
        items = results['items']
        for item in items:
            try:
                thumb = item['images']['hd']
                label = item['title']      
                try:
                    if item['durationLabel'] == '59:59': continue
                    runtime = item['durationLabel'].split(':')
                    if len(runtime) == 3:
                        h, m, s = runtime
                        duration = int(h) * 3600 + int(m) * 60 + int(s)
                    else:
                        m, s = runtime   
                        duration = int(m) * 60 + int(s)
                except: duration = item['duration']
                plot  = item['fulltitle']
                path  = item['video']
                aired = ''
                # aired = (datetime.datetime.fromtimestamp(item['timestamp'].replace('L',''))).strftime('%Y-%m-%d') 
                infoLabel  = {"mediatype":"video","label":label,"title":label,"plot":plot,"genre":"News","duration":duration,"aired":aired}
                infoArt    = {"thumb":thumb,"poster":thumb,"icon":ICON,"fanart":FANART}
                self.addLink(label,path,9,infoLabel,infoArt,len(items))
            except: log("buildLatest, no video media found")
                    
                    
    def buildVideos(self, name, url):
        soup  = BeautifulSoup(self.openURL(url), "html.parser")
        print soup
        # items = soup('a', {'class': 'site-nav__item-anchor site-nav__item-anchor--level-2 '})

        
        
                    
                    
                    
    def playVideo(self, name, url):
        log('playVideo')
        liz = xbmcgui.ListItem(name, path=url)
        if 'm3u8' in url: 
            liz.setProperty('inputstreamaddon','inputstream.adaptive')
            liz.setProperty('inputstream.adaptive.manifest_type','hls') 
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
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name,"genre":"News"})
        else: liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False: liz.setArt({'thumb':ICON,'fanart':FANART})
        else: liz.setArt(infoArt)
        u=sys.argv[0]+"?url="+urllib.quote_plus(u)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,totalItems=total)


    def addDir(self, name, u, mode, infoList=False, infoArt=False):
        name = name.encode("utf-8")
        log('addDir, name = ' + name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'false')
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name,"genre":"News"})
        else: liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False: liz.setArt({'thumb':ICON,'fanart':FANART})
        else: liz.setArt(infoArt)
        u=sys.argv[0]+"?url="+urllib.quote_plus(u)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        
params=getParams()
try: url=urllib.unquote_plus(params["url"])
except: url=None
try: name=urllib.unquote_plus(params["name"])
except: name=None
try: mode=int(params["mode"])
except: mode=None
    
log("Mode: "+str(mode))
log("URL : "+str(url))
log("Name: "+str(name))

if mode==None:  CBSN().buildMainMenu()
elif mode == 0: CBSN().buildLiveLink()
elif mode == 1: CBSN().buildLatest()
elif mode == 2: CBSN().buildBrowse()
elif mode == 3: CBSN().buildVideos(name, url)
elif mode == 9: CBSN().playVideo(name, url)

xbmcplugin.setContent(int(sys.argv[1])    , CONTENT_TYPE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_NONE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_LABEL)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_TITLE)
xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)