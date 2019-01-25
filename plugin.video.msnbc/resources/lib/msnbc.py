#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of MSNBC.
#
# MSNBC is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MSNBC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MSNBC.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, re, traceback, calendar
import urlparse, urllib, urllib2, socket, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from bs4 import BeautifulSoup
from YDStreamExtractor import getVideoInfo
from simplecache import SimpleCache, use_cache

# Plugin Info
ADDON_ID      = 'plugin.video.msnbc'
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
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
QUALITY       = int(REAL_SETTINGS.getSetting('Quality'))
LATEST_LIMIT  = int(REAL_SETTINGS.getSetting('Latest'))
BASE_URL      = 'http://www.msnbc.com/%s'
SHOWS_URL     =  BASE_URL%'api/1.0/shows.json'
PLAYLST_URL   =  BASE_URL%'api/1.0/getplaylistcarousel/vertical/%s.json'
LATEST_URL    =  BASE_URL%'msnbc_googlevideos.xml?page=%s'
NOW_URL       =  BASE_URL%'now'
LIVE_URL      = 'http://tvemsnbc-lh.akamaihd.net/i/nbcmsnbc_1@122532/index_1896_av-p.m3u8?sd=10&amp;rebase=on'
MEDIA_URL     = 'http://feed.theplatform.com/f/7wvmTC/msnbc_video-p-test?form=json&pretty=true&range=-40'
GUIDE_URL     = 'http://feed.entertainment.tv.theplatform.com/f/HNK2IC/prod-msnbc-live-listing?byEndTime=%s-%s~%s-%s'
MAIN_MENU     = [(LANGUAGE(30009), '' , 5),
                 (LANGUAGE(30003), '' , 4),
                 (LANGUAGE(30007), '' , 1)]
             
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
socket.setdefaulttimeout(TIMEOUT)  
class MSNBC(object):
    def __init__(self, sysARG):
        log('__init__, sysARG = ' + str(sysARG))
        self.sysARG = sysARG
        self.cache  = SimpleCache()

           
    def openURL(self, url):
        try:
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
         
         
    def getNowPlaying(self):
        items = self.getGuideData()
        try:
            for item in items:
                now = datetime.datetime.utcnow()
                starttime = datetime.datetime.strptime(item.find('pllisting:starttime').get_text(),'%a, %d %b %Y %H:%M:%S GMT')
                endtime   = datetime.datetime.strptime(item.find('pllisting:endtime').get_text(),'%a, %d %b %Y %H:%M:%S GMT')
                if now >= starttime and now < endtime: break
            label = '%s - %s'%(LANGUAGE(30005),item.find('pl:title').get_text().strip())
            plot  = item.find('pl:description').get_text().strip()
            return (label, LIVE_URL, 8, {"mediatype":"episode","label":label ,"title":label,"genre":"News","plot":plot}, False)
        except: return (LANGUAGE(30005), LIVE_URL, 8)

        
    def getGuideData(self):
        t1  = datetime.datetime.now().strftime('%Y-%m-%dT%I:%M:00')
        h1  = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime('%I:00')
        t2  = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%I:%M:00')
        h2  = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime('%I:00')
        return BeautifulSoup(self.openURL(GUIDE_URL%(t1,h1,t2,h2)), "html.parser").findAll('item')
        
        
    def correctOffset(self, dateOBJ):
        return dateOBJ - (datetime.datetime.utcnow() - datetime.datetime.now())
        
        
    def buildGuideData(self):
        items = self.getGuideData()
        for item in items:
            now = datetime.datetime.utcnow()
            starttime  = self.correctOffset(datetime.datetime.strptime(item.find('pllisting:starttime').get_text(),'%a, %d %b %Y %H:%M:%S GMT'))
            endtime    = self.correctOffset(datetime.datetime.strptime(item.find('pllisting:endtime').get_text(),'%a, %d %b %Y %H:%M:%S GMT'))
            label      = item.find('pl:title').get_text().strip()
            label      = '%s - %s'%(starttime.strftime('%I:%M %p').lstrip('0'),label)
            plot       = item.find('pl:description').get_text().strip()
            genre      = item.find('plprogram:displaygenre').get_text().strip()
            duration   = item.find('plprogram:runtime').get_text().strip()
            aired      = starttime.strftime('%Y-%m-%d')
            dateadded  = starttime.strftime('%Y-%m-%d %H:%M:%S')
            infoLabels = {"mediatype":"episode","label":label ,"title":label,"dateadded":dateadded,"aired":aired,"genre":genre,"plot":plot,"duration":duration}
            self.addLink(label, LIVE_URL, 8, infoLabels, False)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_DATEADDED)
        
    
    def buildMenu(self, items):
        self.addLink(*self.getNowPlaying())
        for item in items: self.addDir(*item)
        self.addYoutube(LANGUAGE(30006), 'plugin://plugin.video.youtube/channel/UCaXkIU1QidjPwiAYu6GcHjg/')
        
        
    def browse(self, url):
        log('browse, url = ' + str(url))
        soup   = BeautifulSoup(self.openURL(url), "html.parser")
        videos = soup('li', {'class': 'article one-half no-action'})
        for video in videos:
            link  = video('div', {'class': 'image-wrapper'})[0].find('a').attrs['href']
            thumb = video('div', {'class': 'image-wrapper'})[0].find('img').attrs['src']
            genre = [cat.get_text() for cat in video('div', {'class': 'category-group'})[0].find_all('a')]
            label = video('h1', {'class': 'article-title'})[0].find('a').get_text()
            plot  = video('div', {'class': 'copy-wrapper'})[0].find('p').get_text()
            infoLabels = {"mediatype":"episode","label":label ,"title":label,"genre":genre,"plot":plot}
            infoArt    = {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":thumb,"logo":thumb}
            self.addLink(label, link, 9, infoLabels, infoArt, len(videos))
            
        next = soup('div', {'class': 'wrapper pagination-wrapper'})
        if len(next) == 0: return
        next_url   = next[0].find('a').attrs['href']
        next_label = next[0].find('a').get_text()
        self.addDir(next_label, next_url, 1)
        

    def browseShows(self):
        log('browseShows')
        shows = json.loads(self.openURL(SHOWS_URL))
        for show in shows['shows']:
            try:
                thumb  = ICON
                fanart = FANART 
                link = show['show']['slug'] 
                if show['show'] and link:
                  if show['show']['title']: label = show['show']['title']
                  if show['show']['assets']:
                    if show['show']['assets']['logo_small'] and show['show']['assets']['logo_small']['path']: thumb = show['show']['assets']['logo_small']['path']
                    elif show['show']['assets']['headshot_large'] and show['show']['assets']['headshot_large']['path']: thumb = show['show']['assets']['headshot_large']['path']
                    if show['show']['assets']['background_image'] and show['show']['assets']['background_image']['path']: fanart = show['show']['assets']['background_image']['path']
                    infoLabels = {"mediatype":"episode","label":label ,"title":label,"genre":"News","plot":label}
                    infoArt    = {"thumb":thumb,"poster":thumb,"fanart":fanart,"icon":thumb,"logo":thumb}
                    self.addDir(label, json.dumps({"slug":link,"thumb":thumb,"fanart":fanart}), 2, infoLabels, infoArt)
            except: pass
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
            

    def browseVideos(self, name, myurl):
        log('browseVideos')
        myurl   = json.loads(myurl)
        scripts = BeautifulSoup(re.sub(r"document\.write(.*);", "", self.openURL(BASE_URL%myurl["slug"])), 'html.parser').findAll("script")
        for script in scripts:
            data = script.get_text().strip()
            if data.startswith("jQuery.extend(Drupal.settings,"): 
                results = json.loads(data.replace("jQuery.extend(Drupal.settings,","").replace(");",""))
                if results['pub_news_show'] and results['pub_news_show']['playlists']:
                    for plist in results['pub_news_show']['playlists']: 
                        infoArt = {"thumb":myurl["thumb"],"poster":myurl["thumb"],"fanart":myurl["fanart"],"icon":myurl["thumb"],"logo":myurl["thumb"]}
                        self.addDir(plist['name'], plist['guid'], 3, False, infoArt)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
                
                
    def buildVideos(self, name, url):
        log('buildVideos')
        videojsondata = json.loads(self.openURL(PLAYLST_URL%url))
        if videojsondata['carousel']: 
            articles = BeautifulSoup(videojsondata['carousel'][0]['item'], 'html.parser').findAll("article")
            for article in articles:
                if article.find("div", attrs = {'class' : 'title'}).get_text() is not None:
                    label = article.find("div", attrs = {'class' : 'title'}).get_text()
                    thumb = article.find('img')['src']
                    aired = article.find("div", attrs = {'class' : 'datetime'}).get_text()
                    plot  = '%s - %s'%(aired,article.find("div", attrs = {'class' : 'description'}).get_text())
                    link  = article.find(lambda tag: tag.name == 'div' and 'data-address' in tag.attrs)['data-address']
                    guid  = article.find(lambda tag: tag.name == 'a' and 'data-ng-attr-guid' in tag.attrs)['data-ng-attr-guid']
                    duration = article.find("div", attrs = {'class' : 'duration'})
                    if duration is not None: duration = int(filter(str.isdigit, str(duration.get_text())))
                    else: duration = 0
                    infoLabels = {"mediatype":"video","label":label,"title":label,"plot":plot,"duration":duration}
                    infoArt    = {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":thumb,"logo":thumb}
                    print(link)
                    self.addLink(label, link, 9, infoLabels, infoArt, len(articles))


    def buildLatest(self, curPage='1'):
        log('buildLatest, page = ' + curPage)
        return (BeautifulSoup(self.openURL(LATEST_URL%curPage), "html.parser").findAll("url"))[:LATEST_LIMIT]

            
    def browseLatest(self, name, url):
        videos  = self.buildLatest()
        for video in videos:
            link  = video.find("video:player_loc").get_text()
            thumb = video.find("video:thumbnail_loc").get_text()
            label = video.find("video:title").get_text()
            dur   = int(video.find("video:duration").get_text())
            try: airdate = video.find("video:publication_date").get_text().split('T')[0]
            except: airdate = datetime.datetime.now().strftime('%Y-%m-%d')
            plot = video.find("video:description").get_text()
            try: plot = plot.split(':')[1]
            except: pass
            plot  = '%s - %s'%(airdate,plot)
            infoLabel  = {"mediatype":"episode","label":label,"title":label,"plot":plot,"plotoutline":plot,"genre":"News","duration":dur,"aired":airdate}                    
            infoArt    = {"thumb":thumb,"poster":thumb,"icon":ICON,"fanart":FANART}
            self.addLink(label,link,9,infoLabel,infoArt,len(videos))

        
    def playLive(self, name):
        log('playLive')
        liz  = xbmcgui.ListItem(name, path=LIVE_URL)
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)
    

    def playVideo(self, name, url):
        log('playVideo')
        info = getVideoInfo(url,QUALITY,True)
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

        if mode==None:  self.buildMenu(MAIN_MENU)
        elif mode == 1: self.browseShows()
        elif mode == 2: self.browseVideos(name, url)
        elif mode == 3: self.buildVideos(name, url)
        elif mode == 4: self.browseLatest(name, url)
        elif mode == 5: self.buildGuideData()
        elif mode == 8: self.playLive(name)
        elif mode == 9: self.playVideo(name, url)

        xbmcplugin.setContent(int(self.sysARG[1])    , CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), cacheToDisc=True)