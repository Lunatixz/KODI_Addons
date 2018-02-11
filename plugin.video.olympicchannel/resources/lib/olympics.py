#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of Olympic Channel.
#
# Olympic Channel is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Olympic Channel is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Olympic Channel.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, datetime, re, traceback
import urlparse, urllib, socket, json, urllib2, collections
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

from bs4 import BeautifulSoup
from simplecache import SimpleCache, use_cache
from YDStreamExtractor import getVideoInfo

# Plugin Info
ADDON_ID      = 'plugin.video.olympicchannel'
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
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
QUALITY       = int(REAL_SETTINGS.getSetting('Quality'))
USER_REGION   = (xbmc.getLanguage(xbmc.ISO_639_1) or 'en')
USER_LANG     = '/%s'%USER_REGION
BASE_URL      = 'https://www.olympicchannel.com'
HOME_URL      = BASE_URL+USER_LANG+'/#'
CHAN_URL      = BASE_URL+'/channel/olympic-channel/'

LIVE_URLS     = ['https://live.olympicchannel.com/ocs/channel01b/master.m3u8',
                 'https://live.olympicchannel.com/ocs/channel02b/master.m3u8',
                 'https://live.olympicchannel.com/ocs/channel03b/master.m3u8',
                 'https://live.olympicchannel.com/ocs/channel04b/master.m3u8',
                 'https://live.olympicchannel.com/ocs/channel05b/master.m3u8']

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def getParams():
    return dict(urlparse.parse_qsl(sys.argv[2][1:]))
               
socket.setdefaulttimeout(TIMEOUT)
class Olympic:
    def __init__(self):
        log('__init__')
        self.cache = SimpleCache()
        
        
    def openURL(self, url):
        log('openURL, url = ' + str(url))
        try:
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                request = urllib2.Request(url)
                request.add_header('User-Agent','Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0)')
                response = urllib2.urlopen(request, timeout = TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, response, expiration=datetime.timedelta(hours=1))
            return self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return ''
         

    def main(self):
        log('main')
        self.addDir('Live'  , '', 0)
        self.addDir('Latest', '', 1)
        self.addYoutube("Browse Youtube" , 'plugin://plugin.video.youtube/channel/UCTl3QQTvqHFjurroKxexy2Q/')
        
        
        # soup  = BeautifulSoup(self.openURL(HOME_URL))
        # items = soup('li' , {'class': 'global-nav__item'})
        # items = collections.Counter(items)
        # for idx, item in enumerate(items):
            # catItem = item('a' , {'class': 'global-nav__link'})
            # self.addDir(catItem[0].get('title'), BASE_URL+catItem[0].get('href'), idx + 1)
        
        
    # def pagination(self, seq, rowlen):
        # for start in xrange(0, len(seq), rowlen):
            # yield seq[start:start+rowlen]

            
    def browseLive(self):
        for idx, link in enumerate(LIVE_URLS): self.addLink('Olympic Channel %s'%(idx+1), link, 9)
            
            
    def browseLatest(self):
        soup  = BeautifulSoup(self.openURL(HOME_URL), "html.parser")
        items = soup('div' , {'class': 'module__player-container'})
        for item in items:
            item = (item('a', {'class': 'module__player-container-link'})[0])
            title = item.attrs['title']
            if '/en/playback/' not in item.attrs['href']: continue
            url   = BASE_URL + item.attrs['href']
            plot  = item.find('img').attrs['alt']
            thumb = item.find('img').attrs['data-srcset'].split('1x, ')[1].split(' 2x')[0]
            infoLabels = {"mediatype":"video","label":title ,"title":title,"plot":plot}
            infoArt    = {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
            self.addLink(title, url, 9, infoLabels, infoArt)
            
            
    # def BrowseHome(self, name, url, parseLinks=False):
        # log('BrowseHome, url = ' + url)
        # soup = BeautifulSoup(self.openURL(url))
        # explore    = soup('section' , {'class': 'montage '})
        # if explore is not None:#todo add explore to home page.
            # print explore
            # # infoLabels ={"mediatype":"video","label":label,"title":label,"plot":artPlot}
            # # infoArt    ={"thumb":ICON,"poster":ICON,"fanart":FANART,"icon":ICON,"logo":ICON}
            # # self.addDir(label, url, 3, infoLabels, infoArt)
            
        # categories = soup('section' , {'class': 'cluster transparent-section transparent-section--cluster'})
        # for category in categories:
            # artTitle = category.find("h2", "cluster__title").get_text()
            # artPlot  = (category.find("h3", "textblock__title") or category.find("p", "textblock__description") or None)
            # if artPlot is not None:
                # artPlot = artPlot.get_text()
            # else:
                # artPlot = ''
            # try:
                # artDesc = category.find("p" , "cluster__intro").get_text()
            # except:
                # artDesc = ''
            # label = '%s - %s'%(artTitle,artDesc) if len(artDesc) > 0 else artTitle
            # if parseLinks == False:
                # infoLabels ={"mediatype":"video","label":label,"title":label,"plot":artPlot}
                # infoArt    ={"thumb":ICON,"poster":ICON,"fanart":FANART,"icon":ICON,"logo":ICON}
                # self.addDir(label, url, 30, infoLabels, infoArt)                
            # elif label == name:
                # articles = category('div' , {'class': 'module__player-container'})
                # for article in articles:
                    # media = article('a' , {'class': 'module__player-container-link'})
                    # for items in media:
                        # linkSoup = BeautifulSoup(self.openURL(BASE_URL+items.get('href')))
                        # link = linkSoup('div' , {'class': 'player js-player'})
                        # for item in link:
                            # path  = json.loads(item.get('data-widget-data'))
                            # title = path['title']
                            # genre = (path['footer']['type'] or '').title()
                            # thumb = (path['images']['main']['url'] or ICON)
                            # dur   = int(path['items'][0]['duration_in_seconds'] or filter(str.isdigit, str(path['duration']))  or 0)
                            # url   = path['items'][0]['ovps'][0]['streaming_url']
                            # infoLabels ={"mediatype":"video","label":title ,"title":title,"genre":genre,"plot":path['synopsis'],"duration":dur}
                            # infoArt    ={"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
                            # self.addLink(title, url, 9, infoLabels, infoArt)
         
                           
    # def BrowseTV(self, url): 
        # log('BrowseTV')
        # channelList = [CHAN_URL]
        # for i in range(2,6):
            # channelList.append(url+'livestream-%d/'%i)
        # log('BrowseTV, channelList =' + str(channelList))
        # for channel in channelList:
            # soup  = BeautifulSoup(self.openURL(channel))
            # meta = json.loads(soup('div' , {'class': 'player js-player'})[0]['data-widget-data'])
            # if meta and 'content' in meta['channel']:
                # #Channel Info
                # if meta and 'channel' in meta and 'content' in meta['channel']:
                    # chName = meta['channel']['content']['name']
                    # url    = meta['channel']['content']['ovps'][0].get('stream_url','channel_url')#'http://ocs-live.hls.adaptive.level3.net/ocs/channel01/NBC_OCS1_VIDEO_5_2264000.m3u8'#
                    # print chName, url

                # #Content Info, try 'current' broadcast, else parse 'next' metadata.
                # for liveStatus in ['current','next']:
                    # try:
                        # StartTime = meta[liveStatus]['content']['announced_start']
                        # EndTime   = meta[liveStatus]['content']['announced_end']
                        # live      = meta[liveStatus]['content']['live'] == True
                        # print liveStatus, StartTime, EndTime, live
                        # thumb    = (meta[liveStatus]['content']['programme']['images']['main']['url'] or ICON)
                        # fanart   = (meta[liveStatus]['content']['programme']['images']['background']['url'] or FANART)
                        # plot     = (meta[liveStatus]['content']['programme']['long_description'] or meta[liveStatus]['content']['programme']['synopsis'] or '').replace('\n','')
                        # title    = meta[liveStatus]['content']['programme']['title']
                        # genre    = (meta[liveStatus]['content']['programme']['genre'] or 'Sports')
                        # duration = (meta[liveStatus]['content']['programme']['duration'] or 0)
                        # print meta[liveStatus]['content']['programme']['live']
                        # print meta[liveStatus]['content']['programme']['time']
                        # print meta[liveStatus]['content']['programme']['episode_number']
                        # print meta[liveStatus]['content']['programme']['language']
                        # print meta[liveStatus]['content']['programme']['created']
                        
                        # infoLabels ={"mediatype":"video","label":title ,"title":title,"genre":genre,"plot":plot,"duration":duration}
                        # infoArt    ={"thumb":thumb,"poster":thumb,"fanart":fanart,"icon":ICON,"logo":ICON}
                        # self.addLink(title, url, 9, infoLabels, infoArt)
                        # break
                    # except:
                        # pass
                        
    def resolveURL(self, url):
        try:
            soup  = BeautifulSoup(self.openURL(url), "html.parser")
            items = json.loads(soup('div' , {'class': 'player js-player'})[0].attrs['data-widget-data'])['items'][0]
            try: return items['ovps'][0]['streaming_url']
            except: return items['ovps'][0]['stream_url']
        except Exception as e: 
            log('resolveURL, failed! ' + str(e), xbmc.LOGERROR)
            log(str(items))
            log(str(soup))
            
    def playVideo(self, name, url, liz=None):
        log('playVideo')
        subs = []
        info = getVideoInfo(url,QUALITY,True)
        if info is None and not url.endswith('m3u8'): url = self.resolveURL(url)
        else:
            info = info.streams()
            url  = info[0]['xbmc_url']
            if 'subtitles' in info[0]['ytdl_format']: subs =([x['url'] for x in info[0]['ytdl_format']['subtitles'].get('en','') if 'url' in x])
        liz  = xbmcgui.ListItem(name, path=url)
        liz.setSubtitles(subs)
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

if mode==None:  Olympic().main()
elif mode == 0: Olympic().browseLive()
elif mode == 1: Olympic().browseLatest()
# elif mode == 4: Olympic().BrowseHome(name,url)
# elif mode == 5: Olympic().BrowseTV(url)
# elif mode == 2: Olympic().browse(name, url)
# elif mode == 8: Olympic().playContent(name, url)
elif mode == 9: Olympic().playVideo(name, url)
# elif mode == 30: Olympic().BrowseHome(name,url,True)

xbmcplugin.setContent(int(sys.argv[1])    , 'files')
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_NONE)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_LABEL)
xbmcplugin.addSortMethod(int(sys.argv[1]) , xbmcplugin.SORT_METHOD_TITLE)
xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)