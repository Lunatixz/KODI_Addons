#   Copyright (C) 2024 Lunatixz
#
#
# This file is part of iSpot.tv.
#
# iSpot.tv is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# iSpot.tv is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with iSpot.tv.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

import os, re, sys, routing, traceback, datetime
import json, requests, base64

from six.moves           import urllib
from youtube_dl          import YoutubeDL
from bs4                 import BeautifulSoup
from simplecache         import SimpleCache, use_cache
from kodi_six            import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode
from infotagger.listitem import ListItemInfoTag

# Plugin Info
ADDON_ID      = 'plugin.video.ispot.tv'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
LOGO          = os.path.join('special://home/addons/%s/'%(ADDON_ID),'resources','images','logo.png')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
ROUTER        = routing.Plugin()
CONTENT_TYPE  = 'episodes'
DISC_CACHE    = False
DEBUG_ENABLED = REAL_SETTINGS.getSetting('Enable_Debugging').lower() == 'true'
ENABLE_DOWNLOAD = REAL_SETTINGS.getSetting('Enable_Download').lower() == 'true'
DOWNLOAD_PATH = os.path.join(REAL_SETTINGS.getSetting('Download_Folder'),'resources').replace('/resources/resources','/resources')
DEFAULT_ENCODING = "utf-8"
ENABLE_SAP    = False
HEADER        = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"}

MENU = {"Apparel, Footwear & Accessories"     :"https://www.ispot.tv/browse/k/apparel-footwear-and-accessories",
        "Business & Legal"                    :"https://www.ispot.tv/browse/Y/business-and-legal",
        "Education"                           :"https://www.ispot.tv/browse/7/education",
        "Electronics & Communication"         :"https://www.ispot.tv/browse/A/electronics-and-communication",
        "Food & Beverage"                     :"https://www.ispot.tv/browse/d/food-and-beverage",
        "Health & Beauty"                     :"https://www.ispot.tv/browse/I/health-and-beauty",
        "Home & Real Estate"                  :"https://www.ispot.tv/browse/o/home-and-real-estate",
        "Insurance"                           :"https://www.ispot.tv/browse/Z/insurance",
        "Life & Entertainment"                :"https://www.ispot.tv/browse/w/life-and-entertainment",
        "Pharmaceutical & Medical"            :"https://www.ispot.tv/browse/7k/pharmaceutical-and-medical",
        "Politics, Government & Organizations":"https://www.ispot.tv/browse/q/politics-government-and-organizations",
        "Restaurants"                         :"https://www.ispot.tv/browse/b/restaurants",
        "Retail Stores"                       :"https://www.ispot.tv/browse/2/retail-stores",
        "Travel"                              :"https://www.ispot.tv/browse/5/travel",
        "Vehicles"                            :"https://www.ispot.tv/browse/L/vehicles"}

#https://www.ispot.tv/events
#todo user prompt when pesudotv detected and download about to start.
def log(msg, level=xbmc.LOGDEBUG):
    if not DEBUG_ENABLED and level != xbmc.LOGERROR: return
    try:   xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    except Exception as e: 'log failed! %s'%(e)
    
def chunkLst(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
 
def slugify(s, lowercase=False):
  if lowercase: s = s.lower()
  s = s.strip()
  s = re.sub(r'[^\w\s-]', '', s)
  s = re.sub(r'[\s_-]+', '_', s)
  s = re.sub(r'^-+|-+$', '', s)
  return s
        
def unquoteString(text):
    return urllib.parse.unquote(text)
    
def quoteString(text):
    return urllib.parse.quote(text)

def encodeString(text):
    base64_bytes = base64.b64encode(text.encode(DEFAULT_ENCODING))
    return base64_bytes.decode(DEFAULT_ENCODING)

def decodeString(base64_bytes):
    try:
        message_bytes = base64.b64decode(base64_bytes.encode(DEFAULT_ENCODING))
        return message_bytes.decode(DEFAULT_ENCODING)
    except: pass

@ROUTER.route('/')
def buildMenu():
    iSpotTV().buildMenu()

@ROUTER.route('/menu/<category>')
def getCategory(category):
    iSpotTV().buildCategory(category)
    
@ROUTER.route('/play/<meta>')
def playVideo(meta):
    iSpotTV().playVideo(meta.split('|')[0],decodeString(meta.split('|')[1]))
    
class iSpotTV(object):
    def __init__(self, sysARG=sys.argv):
        log('__init__, sysARG = %s'%(sysARG))
        self.sysARG    = sysARG
        self.cache     = SimpleCache()
        self.myMonitor = xbmc.Monitor()
        
        
    @use_cache(3)
    def getURL(self, url):
        log('getURL, url = %s'%(url))
        try:    return requests.get(url, headers=HEADER).content
        except Exception as e: log('getURL Failed! %s'%(e))
    
    
    def getSoup(self, url):
        log('getSoup, url = %s'%(url))
        return BeautifulSoup(self.getURL(url), 'html.parser')
        

    def buildMenu(self):
        log('buildMenu')
        for name, url in list(MENU.items()): self.addDir(name,uri=(getCategory,name))
    
    
    def buildCategory(self, category=None):
        """ < div
        class ="mb-0" >
        < a adname = "FootJoy Pro/SLX TV Spot, 'Joy Ride' Featuring Max Homa, Danielle Kang, Song by 10cc - 16 airings" href = "/ad/6K6T/footjoy-pro-slx-joy-ride" >
        < img alt = "FootJoy Pro/SLX TV Spot, 'Joy Ride' Featuring Max Homa, Danielle Kang, Song by 10cc" class ="img-16x9" loading="lazy" src="https://images-cdn.ispot.tv/ad/6K6T/default-large.jpg" width="100%" / >< / a >
        < / div >"""
        try:
            log('buildCategory, category = %s'%(category))
            for row in self.getSoup(MENU.get(category)).find_all('div', {'class': 'mb-0'}):
                label, label2 = row.a['adname'].split(' - ')
                if label.lower().endswith('[spanish]') and not ENABLE_SAP: continue
                if ENABLE_DOWNLOAD: self.queDownload(row.a['href'])
                self.addLink(label,(playVideo,'%s|%s'%(row.a['adname'],encodeString(row.a['href']))),info={'label':label,'label2':label2,'title':label},art={"thumb":row.img['src'],"poster":row.img['src'],"fanart":FANART,"icon":LOGO,"logo":LOGO})
        except Exception as e: log('buildCategory Failed! %s'%(e))


    def addLink(self, name, uri=(''), info={}, art={}, media='video', total=0):
        log('addLink, name = %s'%name)
        try:
            if not info: info = {"label":name,"label2":"","title":name}
            if not art:   art = {"thumb":ICON,"poster":ICON,"fanart":FANART,"icon":LOGO,"logo":LOGO}
            info["mediatype"] = media
            liz = self.getListItem(info.pop('label'), info.pop('label2'), ROUTER.url_for(*uri))
            liz.setArt(art)
            liz.setProperty('IsPlayable','true')
            infoTag = ListItemInfoTag(liz, media) 
            infoTag.set_info(info)
            xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(*uri), liz, isFolder=False, totalItems=total)
        except Exception as e: log('addLink Failed! %s'%(e))
        

    def addDir(self, name, uri=(''), info={}, art={}, media='video'):
        log('addDir, name = %s'%name)
        if not info: info = {"label":name,"label2":"","title":name}
        if not art:   art = {"thumb":ICON,"poster":ICON,"fanart":FANART,"icon":LOGO,"logo":LOGO}
        info["mediatype"] = media
        liz = self.getListItem(info.pop('label'), info.pop('label2'), ROUTER.url_for(*uri))
        liz.setArt(art)
        liz.setProperty('IsPlayable','false')
        infoTag = ListItemInfoTag(liz, media)
        infoTag.set_info(info)
        xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(*uri), liz, isFolder=True)
        
        
    def getListItem(self, label='', label2='', path='', offscreen=False):
        return xbmcgui.ListItem(label,label2,path,offscreen)
        
        
    @use_cache(1)
    def getVideo(self, url):
          # {'id': '5Gwt-video-sm', 'title': '5Gwt-video-sm', 'timestamp': 1697567715.0, 'direct': True, 
          # 'formats': [{'format_id': 'mp4', 'url': 'https://videos-cdn.ispot.tv/ad/d0c1/5Gwt-video-sm.mp4',
          # 'vcodec': None, 'ext': 'mp4', 'format': 'mp4 - unknown', 'protocol': 'https', 
          # 'http_headers':{}}], 'extractor': 'generic', 'webpage_url': 'https://videos-cdn.ispot.tv/ad/d0c1/5Gwt-video-sm.mp4', 
          # 'webpage_url_basename': '5Gwt-video-sm.mp4', 'extractor_key': 'Generic', 'playlist': None, 'playlist_index': None, 
          # 'display_id': '5Gwt-video-sm', 'upload_date': '20231017', 'requested_subtitles': None, 'format_id': 'mp4', 
          # 'url': 'https://videos-cdn.ispot.tv/ad/d0c1/5Gwt-video-sm.mp4', 'vcodec': None, 'ext': 'mp4', 'format': 'mp4 - unknown', 
          # 'protocol': 'https', 'http_headers': {}}
        log('getVideo, url = %s'%url)
        ydl = YoutubeDL({'no_color': True, 'format': 'best', 'outtmpl': '%(id)s.%(ext)s', 'add-header': HEADER})
        with ydl:
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                return result['entries'][0] #playlist
            else:
                return result

        
    def playVideo(self, name, uri):
        found = True
        file = os.path.join(DOWNLOAD_PATH,'%s.mp4'%(slugify(uri)))
        if not xbmcvfs.exists(file):
            if ENABLE_DOWNLOAD: self.queDownload(uri)
            video = self.getVideo('https://www.ispot.tv%s'%(uri))
            if not video: found = False
            else: file = video['url']
        log('playVideo, file = %s, found = %s'%(file,found))
        xbmcplugin.setResolvedUrl(ROUTER.handle, found, self.getListItem(name, path=file))
        

    def queDownload(self, uri):
        log('queDownload, uri = %s'%(uri))
        queuePool = (self.cache.get('queuePool', json_data=True) or {})
        queuePool.setdefault('uri',[]).append(uri)
        if len(queuePool['uri']) > 0: queuePool['uri'] = list(set(queuePool['uri']))
        self.cache.set('queuePool', queuePool, json_data=True, expiration=datetime.timedelta(days=28))
        

    def getDownloads(self):
        if not ENABLE_DOWNLOAD: return
        queuePool = (self.cache.get('queuePool', json_data=True) or {})
        uris      = queuePool.get('uri',[])
        dia       = self.progressBGDialog(message='Preparing to download %s'%(ADDON_NAME))
        dluris    = (list(chunkLst(uris,5)) or [[]])[0]
        for idx, uri in enumerate(dluris):
            try: 
                diact = int(idx*100//len(dluris))
                dia   = self.progressBGDialog(diact, dia, message='Downloading Adverts (%s%%)'%(diact))
                video = self.getVideo('https://www.ispot.tv%s'%(uri))
                if not video: continue
                url  = video['url']
                if not xbmcvfs.exists(DOWNLOAD_PATH): xbmcvfs.mkdir(DOWNLOAD_PATH)
                dest = xbmcvfs.translatePath(os.path.join(DOWNLOAD_PATH,'%s.mp4'%(slugify(uri))))
                if not xbmcvfs.exists(dest):
                    urllib.request.urlretrieve(url, dest)
                    log('getDownloads, url = %s, dest = %s'%(url,dest))
                uris.pop(uris.index(uri))
                if self.myMonitor.waitForAbort(5): break
            except Exception as e:
                log('getDownloads Failed! %s'%(e))
                self.progressBGDialog(100, dia, message='Downloading (Canceled!)')
        self.progressBGDialog(100, dia, message='Downloading (Finished!)')
        queuePool['uri'] = uris
        log('getDownloads, remaining urls = %s'%(len(uris)))
        self.cache.set('queuePool', queuePool, json_data=True, expiration=datetime.timedelta(days=28))
        
        
    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME, silent=None, wait=None):
        if control is None and int(percent) == 0:
            control = xbmcgui.DialogProgressBG()
            control.create(header, message)
        elif control:
            if int(percent) == 100 or control.isFinished(): 
                if hasattr(control, 'close'):
                    control.close()
                    return None
            elif hasattr(control, 'update'):  control.update(int(percent), header, message)
            if wait: self.myMonitor.waitForAbort(wait/1000)
        return control
        

    def run(self): 
        ROUTER.run()
        xbmcplugin.setContent(ROUTER.handle     ,CONTENT_TYPE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(ROUTER.handle ,cacheToDisc=DISC_CACHE)