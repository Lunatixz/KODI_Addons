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
QUALITY       = int(REAL_SETTINGS.getSetting('Quality'))
BASE_URL      = 'https://www.cbsnews.com'
LIVE_URL      = BASE_URL+'/live'
VID_URL       = BASE_URL+'/videos'
EPS_URL       = BASE_URL+'/%s/full-episodes'
PLS_URL       = 'http://cbsn.cbsnews.com/rundown/?device=desktop'
SHOW_LIST     = ['CBS Evening News','48 Hours','60 Minutes','Face the Nation']

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
  
socket.setdefaulttimeout(TIMEOUT)
class CBSN(object):
    def __init__(self, sysARG):
        log('__init__, sysARG = ' + str(sysARG))
        self.sysARG = sysARG
        self.cache  = SimpleCache()

            
    def openURL(self, url):
        log('openURL, url = ' + str(url))
        try:
            cacheResponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheResponse:
                request = urllib2.Request(url)
                request.add_header('User-Agent','Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)')
                cacheResponse = urllib2.urlopen(request, timeout=TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheResponse, expiration=datetime.timedelta(minutes=5))
            return cacheResponse
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return ''
             

    def buildMainMenu(self):
        self.buildLive()
        self.addDir(LANGUAGE(30004)    ,'',1)
        # self.addDir(LANGUAGE(30005)    ,'',2)
        self.addDir(LANGUAGE(30007)    ,'',3)
        self.addYoutube(LANGUAGE(30006), 'plugin://plugin.video.youtube/user/CBSNewsOnline/')
        
        
    def buildBrowse(self):
        items = json.loads(self.openURL(PLS_URL))['navigation']['data']
        for item in items:
            print(item)
            
            
    def buildShows(self):
        soup  = BeautifulSoup(self.openURL(BASE_URL), "html.parser")
        items = soup('a', {'class': 'site-nav__item-anchor site-nav__item-anchor--level-2 '})
        for item in items:
            print(item)
        # for item in VID_URL: self.addDir(item ,(EPSURL%(urllib.quote(item.replace(' ','-')))),4)
        
    
    def buildLive(self, play=False):
        items = json.loads('{'+re.compile("CBSNEWS.defaultPayload = {(.+?)};", re.DOTALL).search(self.openURL(LIVE_URL)).group(1).split("CBSNEWS.defaultLayout")[0])['items']
        for item in items:
            if item['type'] == 'live':
                url   = item['video']
                label = '%s - %s'%(LANGUAGE(30003),item['title'])
                if play == False: self.addLink(label,url,0)
                else:
                    thumb = (item['images']['hd'] or ICON)
                    plot  = item['fulltitle']
                    liz = xbmcgui.ListItem(label, path=url)
                    liz.setProperty('inputstreamaddon','inputstream.adaptive')
                    liz.setProperty('inputstream.adaptive.manifest_type','hls') 
                    liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":label,"title":label,"plot":plot,"genre":"News"})
                    liz.setArt({"thumb":thumb,"poster":thumb,"icon":ICON,"fanart":FANART})
                    xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)
                break
            
    
    def buildLatest(self):
        results = json.loads('{'+re.compile("CBSNEWS.defaultPayload = {(.+?)};", re.DOTALL).search(self.openURL(LIVE_URL)).group(1).split("CBSNEWS.defaultLayout")[0])
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
                # aired = datetime.datetime.fromtimestamp(float(str(item['timestamp']))).strftime('%Y-%m-%d') 
                infoLabel  = {"mediatype":"video","label":label,"title":label,"plot":plot,"genre":"News","duration":duration,"aired":aired}
                infoArt    = {"thumb":thumb,"poster":thumb,"icon":ICON,"fanart":FANART}
                self.addLink(label,path,9,infoLabel,infoArt,len(items))
            except Exception as e: log("buildLatest failed!" + str(e), xbmc.LOGERROR)
                    
                   
    def buildVideos(self, name, url):
        soup   = BeautifulSoup(self.openURL(url), "html.parser")
        items  = soup('li')
        for idx, item in enumerate(items):
            try: link = item.find('a').attrs["href"]
            except: continue
            if not link.startswith('/video/'): continue
            # print idx, item
            label  = item.find('h3').get_text()
            plot   = item.find('p').get_text().strip('\n\r\t')
            thumb  = (item.find('img').attrs["src"]).rstrip('#')
            aired  = ''#item('span', {'class': 'date'})[0].get_text()
            # aired  = (datetime.datetime.fromtimestamp(item['timestamp'].replace('L',''))).strftime('%Y-%m-%d') 
            
            infoLabel  = {"mediatype":"video","label":label,"title":label,"plot":plot,"genre":"News","aired":aired}
            infoArt    = {"thumb":thumb,"poster":thumb,"icon":ICON,"fanart":FANART}
            self.addLink(label,url+link,9,infoLabel,infoArt,len(items))
                    # <a class="social-icons__icon-anchor" href="https://www.youtube.com/user/60minutes" title="youtube">
                    
                    
    def playVideo(self, name, url):
        log('playVideo')
        info = getVideoInfo(url,QUALITY,True)
        print(info)
        if info is None: return
        info = info.streams()
        url  = info[0]['xbmc_url']
        liz  = xbmcgui.ListItem(name, path=url) 
        if 'subtitles' in info[0]['ytdl_format']: liz.setSubtitles([x['url'] for x in info[0]['ytdl_format']['subtitles'].get('en','') if 'url' in x])
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)

        
    def addYoutube(self, name, url):
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'false')
        liz.setInfo(type="Video", infoLabels={"label":name,"title":name} )
        liz.setArt({'thumb':ICON,'fanart':FANART})
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=url,listitem=liz,isFolder=True)

        
    def addLink(self, name, u, mode, infoList=False, infoArt=False, total=0):
        name = name.encode("utf-8")
        log('addLink, name = ' + name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'true')
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name,"genre":"News"})
        else: liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False: liz.setArt({'thumb':ICON,'fanart':FANART})
        else: liz.setArt(infoArt)
        u=self.sysARG[0]+"?url="+urllib.quote_plus(u)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,totalItems=total)


    def addDir(self, name, u, mode, infoList=False, infoArt=False):
        name = name.encode("utf-8")
        log('addDir, name = ' + name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'false')
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name,"genre":"News"})
        else: liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False: liz.setArt({'thumb':ICON,'fanart':FANART})
        else: liz.setArt(infoArt)
        u=self.sysARG[0]+"?url="+urllib.quote_plus(u)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,isFolder=True)
        
        
    def getParams(self):
        return dict(urlparse.parse_qsl(self.sysARG[2][1:]))

            
    def run(self):  
        params=self.getParams()
        try: url=urllib.unquote_plus(params["url"])
        except: url=None
        try: name=urllib.unquote_plus(params["name"])
        except: name=None
        try: mode=int(params["mode"])
        except: mode=None
        log("Mode: "+str(mode))
        log("URL : "+str(url))
        log("Name: "+str(name))

        if mode==None:  self.buildMainMenu()
        elif mode == 0: self.buildLive(play=True)
        elif mode == 1: self.buildLatest()
        elif mode == 2: self.buildBrowse()
        elif mode == 3: self.buildShows()
        elif mode == 4: self.buildVideos(name, url)
        elif mode == 9: self.playVideo(name, url)

        xbmcplugin.setContent(int(self.sysARG[1])    , CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), cacheToDisc=True)