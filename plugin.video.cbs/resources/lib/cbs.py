#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of CBS.
#
# CBS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CBS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CBS.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import sys, time, datetime, re, traceback
import urlparse, urllib, urllib2, socket, json, HTMLParser
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from bs4 import BeautifulSoup
from YDStreamExtractor import getVideoInfo
from simplecache import SimpleCache

# Plugin Info
ADDON_ID      = 'plugin.video.cbs'
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
BASE_URL      = 'http://www.cbs.com'
WATCH_URL     = BASE_URL+'/watch'
SHOW_URL      = BASE_URL+'/carousels/videosBySection/%s/offset/0/limit/40/xs/0'
SHOWS_URL     = BASE_URL+'/shows/all'

MAIN_MENU = [("Latest", "", 1),
             ("Shows" , "", 2)]

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
             
def uni(string, encoding = 'utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode): string = unicode(string, encoding)
        elif isinstance(string, unicode): string = string.encode('ascii', 'replace')
    return string
   
def unescape(string):
    try:
        parser = HTMLParser.HTMLParser()
        return (parser.unescape(string))
    except: return string
   
def getParams():
    return dict(urlparse.parse_qsl(sys.argv[2][1:]))
                  
socket.setdefaulttimeout(TIMEOUT)
class CBS(object):
    def __init__(self):
        log('__init__')
        self.cache = SimpleCache()
           
           
    def openURL(self, url):
        log('openURL, url = ' + str(url))
        try:
            cacheResponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheResponse:
                request = urllib2.Request(url)
                cacheResponse = urllib2.urlopen(request, timeout = TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheResponse, expiration=datetime.timedelta(hours=1))
            return cacheResponse
        except Exception as e:log("openURL Failed! " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
        return ''
         
         
    def buildMenu(self, items):
        for item in items: self.addDir(*item)
        self.addYoutube("Youtube" , 'plugin://plugin.video.youtube/user/CBS/')
            
                
    def browseLatest(self, url=None):
        if url is None: url = WATCH_URL
        soup = BeautifulSoup(self.openURL(url), "html.parser")
        items = soup('li', {'class': 'episode'})
        for item in items:
            seasonNumber  = 0
            episodeNumber = 0
            metas         = re.findall(r'<meta content="(.*?)>', str(item), re.DOTALL)
            metas.extend(re.findall(r'<span content="(.*?)>', str(item), re.DOTALL))
            metaTYPES     = ["name","description","thumbnailUrl","uploadDate","url","seasonNumber","episodeNumber"]
            metaLST       = {}
            metaKeys      = []
            for type in metaTYPES:
                for meta in metas:
                    if 'itemprop="%s"'%type in meta:
                        if type == "description" and 'description' in metaKeys: metaLST["plot"] = meta.split('" itemprop="%s"'%type)[0]
                        else:
                            if type not in metaKeys: 
                                metaKeys.append(type)
                                metaLST[type] = meta.split('" itemprop="%s"'%type)[0]
            label = unescape(uni((metaLST.get('description') or metaLST['name']).decode("utf-8")))
            plot  = unescape(uni((metaLST.get('plot','')     or label)))
            try: aired = metaLST['uploadDate'].split('T')[0]
            except: aired = datetime.datetime.now().strftime('%Y-%m-%d')
            thumb = metaLST['thumbnailUrl']
            url   = metaLST['url']
            if not url.startswith('http://'): url = (BASE_URL + '%s'%url).lstrip('/')        
            seasonNumber = (int(filter(str.isdigit, str(metaLST.get('seasonNumber',seasonNumber)))))
            episodeNumber = (int(filter(str.isdigit, str(metaLST.get('episodeNumber',episodeNumber)))))
            seinfo = ('S' + ('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'E' + ('0' if episodeNumber < 10 else '') + str(episodeNumber))
            label  = '%s'%(label) if seasonNumber + episodeNumber == 0 else '%s - %s'%(label, seinfo)
            infoLabels ={"mediatype":"episode","label":label ,"title":label,"TVShowTitle":label,"plot":plot,"aired":aired}
            infoArt    ={"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
            self.addLink(label, url, 9, infoLabels, infoArt, len(items))
            
            
    def browseEpisodes(self, url):
        log('browseEpisodes')
        items = json.loads(self.openURL(url))['result']['data']
        for item in items:
            if 'status' in item and item['status'].lower() != 'available': continue
            title     = uni(item.get('title','') or item.get('label','') or item.get('episode_title',''))
            vidType   = item['type']
            thumb     = (item['thumb'].get('large','') or item['thumb'].get('small','') or ICON)
            aired     = str(item['airdate_iso']).split('T')[0]#str(item['airdate'])
            showTitle = uni(item['series_title'])
            runtime   = item['duration'].split(':')
            if len(runtime) == 3:
                h, m, s = runtime
                duration  = int(h) * 3600 + int(m) * 60 + int(s)
            else:
                m, s = runtime   
                duration  = int(m) * 60 + int(s)
            seasonNumber  = int(item.get('season_number','0')   or '0')
            episodeNumber = int(item.get('episode_number','0')  or '0')
            url = item['url']
            if not url.startswith('http://'): url = (BASE_URL + '%s'%url).lstrip('/')
            seinfo = ('S' + ('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'E' + ('0' if episodeNumber < 10 else '') + str(episodeNumber))
            label  = '%s - %s'%(showTitle, title) if seasonNumber + episodeNumber == 0 else '%s - %s - %s'%(showTitle, seinfo, title)
            plot   = uni(item.get('description',label))
            infoLabels ={"mediatype":"episode","label":label ,"title":label,"TVShowTitle":showTitle,"plot":plot,"aired":aired,"duration":duration,"season":seasonNumber,"episode":episodeNumber}
            infoArt    ={"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
            self.addLink(label, url, 9, infoLabels, infoArt, len(items))

            
    def browseCategory(self, url):
        log('browseCategory')
        items     = json.loads(url)
        url       = items['url']
        thumb     = items['thumb']
        response  = self.openURL(url).replace('\n','').replace('\r','').replace('\t','')
        items     = re.search('(?:video\.section_ids = |"section_ids"\:)\[([^\]]+)\]',response)
        if items:
            items = items.group(1).split(',')
            metas = json.loads(re.search('(?:video\.section_metadata = |"section_metadata"\:)({.+?}})',response).group(1))
            CONTENT_TYPE  = 'tvshows'
            for item in items:
                try:
                    url     = SHOW_URL%item
                    seasons = (metas.get(item,'').get('display_seasons','') or False)
                    
                    if seasons:
                        title = uni(metas[item]['title'])
                        try: seasonLST  = json.loads(re.search('video\.seasons = (.+?);',response).group(1).replace('filter','"filter"').replace('current','"current"'))
                        except: continue
                        for season in seasonLST['filter']:
                            if season['total_count'] == season['premiumCount']: continue
                            title = season['title']
                            seasonURL   = '%s/%s/' %(url,season["season"])
                            try: episodes = json.loads(self.openURL(seasonURL))
                            except: episodes = ''
                            if 'success' in episodes:
                                infoLabels ={"mediatype":"tvshow",
                                             "label":title,
                                             "title":title,
                                             "TVShowTitle":title
                                            }
                                infoArt    ={"thumb":thumb,
                                             "poster":thumb,
                                             "fanart":FANART,
                                             "icon":ICON,
                                             "logo":ICON
                                            }
                                self.addDir(title,seasonURL,5,infoLabels,infoArt)
                    else:
                        item  = json.loads(self.openURL(url))
                        if item and 'success' in item:
                            title = uni(item['result']['title'])
                            infoLabels = {"mediatype":"tvshow","label":title ,"title":title,"TVShowTitle":title}
                            infoArt    = {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
                            self.addDir(title,url,5,infoLabels,infoArt)
                except: continue
                
                        
    def browseShows(self, url=None):
        log('browseShows')
        soup  = BeautifulSoup(self.openURL(SHOWS_URL), "html.parser")
        shows = soup('article', {'class': 'show-browse-item'})
        for idx, show in enumerate(shows):
            title  = uni(show.get_text()).replace("\n", "")
            if 'previews' in title.lower() or 'premieres' in title.lower(): continue
            url    = shows[idx].a['href']
            if not url.startswith('http://'): url = (BASE_URL + url).lstrip('/')
            if not url.endswith('/video/'): url = '%s/video/'%url.rstrip('/')
            thumb  = shows[idx].img['data-src']
            url    = json.dumps({'url':url,'thumb':thumb})
            infoLabels ={"mediatype":"episode","label":title ,"title":title,"TVShowTitle":title}
            infoArt    ={"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
            self.addDir(title,url,3,infoLabels,infoArt)
            
            
    def playVideo(self, name, url, liz=None):
        log('playVideo')
        info = getVideoInfo(url,QUALITY,True)
        if info is None: return
        info = info.streams()
        url  = info[0]['xbmc_url']
        liz  = xbmcgui.ListItem(name, path=url)
        if 'subtitles' in info[0]['ytdl_format']: liz.setSubtitles([x['url'] for x in info[0]['ytdl_format']['subtitles'].get('en','') if 'url' in x])
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
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
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
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
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

if mode==None:  CBS().buildMenu(MAIN_MENU)
elif mode == 1: CBS().browseLatest(url)
elif mode == 2: CBS().browseShows(url)
elif mode == 3: CBS().browseCategory(url)
elif mode == 4: CBS().browseSeasons(url)
elif mode == 5: CBS().browseEpisodes(url)
elif mode == 9: CBS().playVideo(name, url)

xbmcplugin.setContent(int(sys.argv[1])    , CONTENT_TYPE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_NONE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_LABEL)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_TITLE)
xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)
