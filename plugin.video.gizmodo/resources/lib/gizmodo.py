#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of Gizmodo.
#
# Gizmodo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Gizmodo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gizmodo.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, re, traceback
import urlparse, urllib, urllib2, socket, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from bs4 import BeautifulSoup
from simplecache import SimpleCache, use_cache

# Plugin Info
ADDON_ID      = 'plugin.video.gizmodo'
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
CONTENT_TYPE  = 'episodes'
QUALITY       = int(REAL_SETTINGS.getSetting('Quality'))
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
BASE_URL      = 'https://gizmodo.com/video'
LOGO_URL      = 'https://logo.clearbit.com/%s?size=512'
           
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
socket.setdefaulttimeout(TIMEOUT)  
class Gizmodo(object):
    def __init__(self, sysARG):
        log('__init__, sysARG = ' + str(sysARG))
        self.sysARG  = sysARG
        self.cache   = SimpleCache()
           
           
    def openURL(self, url):
        try:
            url = url.replace('/splinter.com/','/splinternews.com/')
            log('openURL, url = ' + str(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                cacheresponse = urllib2.urlopen(urllib2.Request(url), timeout=TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheresponse, expiration=datetime.timedelta(minutes=15))
            return cacheresponse
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return ''
            
         
    def buildMenu(self):
        soup  = BeautifulSoup(self.openURL(BASE_URL), "html.parser")
        sites = soup('li', {'class': 'js_hovernav__trigger'})
        for site in sites:
            label = site.get_text()
            if 'the inventory' in label.lower(): continue
            link  = 'http:%s/video'%site.attrs['data-blog-domain']
            thumb = LOGO_URL%(re.findall('http[s]?://(.*?)/', link)[0])
            if 'gizmodo' in link: thumb = ICON
            self.addDir(label, link, 1, infoArt= {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":thumb,"logo":thumb})
        self.addYoutube(LANGUAGE(30007), 'plugin://plugin.video.youtube/channel/UCxFmw3IUMDUC1Hh7qDjtjZQ/')


    def browse(self, label, url):
        log('browse, url = ' + str(url))
        soup   = BeautifulSoup(self.openURL(url), "html.parser")
        pageType, blogGroup, blogID = [meta.attrs['content'] for meta in soup.find_all('meta')[-3:]]
        link   = 'http://%s.com/api/core/video/views/videoPage?blogId=%s&network=%s&resolvePosts=true&startIndex=0&maxReturned=25'%(blogGroup, blogID, label)
        thumb  = LOGO_URL%('%s.com'%blogGroup)
        videos = json.loads(self.openURL(link))['data']
        if len(videos) == 0: self.addDir(LANGUAGE(30009), '', '')
        for video in videos:
            try: link = re.findall("u'permalink': u'(.+?)'",str(video['posts'][0]),flags=re.DOTALL)[0]
            except: print(video)
            try: thumb = video['externalThumbnail']
            except: thumb = 'https://i.kinja-img.com/gawker-media/image/upload/%s'%video['thumbnail']['id']
            label = video['title']
            plot  = video['description']
            genre = video['tags']
            try: aired = (datetime.datetime.strptime(video['publishTime'].split('T')[0], '%Y-%m-%d'))
            except: aired = datetime.datetime.now()
            aired = aired.strftime("%Y-%m-%d")
            duration   = video['length']
            infoLabels = {"mediatype":"episodes","label":label,"title":label,"plot":plot,"genre":genre,"aired":aired,"duration":duration}
            infoArt    = {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":thumb,"logo":thumb}
            self.addLink(label, link, 9, infoLabels, infoArt, len(videos))
        # next = soup('a', {'class': 'js-cne-ajax cne-more-button cne-more-videos cne-light-button'})
        # if len(next) == 0: return
        # next_url   = '%s?%s'%(url.split('?')[0],next[0].attrs['data-ajaxurl'].split('?')[1])
        # next_label = LANGUAGE(30008)%(next_url.split('=')[1])
        # self.addDir(next_label, next_url, 1)  
        
        
    def playVideo(self, name, url):
        log('playVideo')
        from YDStreamExtractor import getVideoInfo
        info = getVideoInfo(url,QUALITY,True)
        if info is None: return
        info = info.streams()
        plst = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        plst.clear()
        for videos in info:
            vidIDX = videos['idx']
            url = videos['xbmc_url']
            liz = xbmcgui.ListItem(videos['title'], path=url)
            if 'm3u8' in url.lower():
                liz.setProperty('inputstreamaddon','inputstream.adaptive')
                liz.setProperty('inputstream.adaptive.manifest_type','hls')
            if 'subtitles' in videos['ytdl_format']: liz.setSubtitles([x['url'] for x in videos['ytdl_format']['subtitles'].get('en','') if 'url' in x])
            plst.add(url, liz, vidIDX)
            if vidIDX == 0: xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz) 
        plst.unshuffle()
        
        
    def addYoutube(self, name, url):
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'false')
        liz.setInfo(type="Video", infoLabels={"label":name,"title":name} )
        thumb = LOGO_URL%('youtube.com')
        liz.setArt({'thumb':thumb,'fanart':FANART})
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=url,listitem=liz,isFolder=True)
        
           
    def addLink(self, name, u, mode, infoList=False, infoArt=False, total=0):
        name = name.encode("utf-8")
        log('addLink, name = ' + name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'true')
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
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
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
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

        if mode==None:  self.buildMenu()
        elif mode == 1: self.browse(name, url)
        elif mode == 9: self.playVideo(name, url)

        xbmcplugin.setContent(int(self.sysARG[1])    , CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), cacheToDisc=True)