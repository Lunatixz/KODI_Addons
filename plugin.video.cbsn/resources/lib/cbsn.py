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
import urllib, urllib2, socket, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from simplecache import SimpleCache

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
LIVEURL       = 'https://cbsn1.cbsistatic.com/scripts/Video.js?v=00bfcbe9781bd47659f8000ff016c50212e26dee'
VIDURL        = 'https://www.cbsnews.com/videos'

def log(msg, level=xbmc.LOGDEBUG):
    if not DEBUG and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg), level)
   
def getParams():
    param=[]
    if len(sys.argv[2])>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'): params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2: param[splitparams[0]]=splitparams[1]
    return param
                 
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
        self.addLink('Live'              ,'',0)
        self.addDir('Browse'             ,'',1)
        self.addYoutube("Browse Youtube" , 'plugin://plugin.video.youtube/user/CBSNewsOnline/')
        
        
    def buildLiveLink(self):
        urlbase = 'http:'+re.compile('vidThis.hlsurl = "(.+?)"', re.DOTALL).search(self.openURL(LIVEURL)).group(1)
        self.playVideo('CBS News Live',urlbase)
            
            
    def buildBrowse(self):
        results = json.loads(re.compile("data-cbsvideoui-options='{(.+?)}'", re.DOTALL).search(self.openURL(VIDURL)).group(1).replace('"state":',''))
        if results and 'playlist' in results:
            for item in results['playlist']:
                try:
                    thumb = results['playlist'][item]['promoImage']['path']
                    label = results['playlist'][item]['title']
                    plotoutline  = results['playlist'][item]['headline']
                    plot = results['playlist'][item]['dek']
                    tags  = results['playlist'][item].get('keywords','')
                    duration = results['playlist'][item]['duration']
                    path  = results['playlist'][item]['medias']['tablet']['url']
                    date  = results['playlist'][item]['airDate']['date']
                    aired = (datetime.datetime.strptime(date[0:9], '%Y-%m-%d')).strftime('%Y-%m-%d') 
                    plot  = '%s - %s'%(date, plot)
                    infoLabel  = {"mediatype":"video","label":label,"title":label,"plot":plot,"plotoutline":plotoutline,"genre":"News","duration":duration,"aired":aired,"tag":tags}
                    infoArt    = {"thumb":thumb,"poster":thumb,"icon":ICON,"fanart":FANART}
                    self.addLink(label,path,9,infoLabel,infoArt,len(results['playlist']))
                except: log("buildBrowse, no video media found")
                    
                    
    def playVideo(self, name, url, liz=None):
        log('playVideo')
        if not liz: liz = xbmcgui.ListItem(name, path=url)
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
elif mode == 1: CBSN().buildBrowse()
elif mode == 9: CBSN().playVideo(name, url)

xbmcplugin.setContent(int(sys.argv[1])    , CONTENT_TYPE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_NONE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_LABEL)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_TITLE)
xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)