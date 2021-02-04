#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of Channels DVR.
#
# Channels DVR is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Channels DVR is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Channels DVR.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, _strptime, re, routing
import random, string, traceback
import socket, json, inputstreamhelper, requests

from six.moves     import urllib
from simplecache   import SimpleCache, use_cache
from itertools     import repeat, cycle, chain, zip_longest
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

try:
    from multiprocessing      import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
    CORES = cpu_count()
except: ENABLE_POOL = False

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY3: 
    basestring = str
    unicode = str
  
# Plugin Info
ADDON_ID      = 'plugin.video.channelsdvr'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
ROUTER        = routing.Plugin()

## GLOBALS ##
TIMEOUT       = 30
DEBUG         = REAL_SETTINGS.getSettingBool('Enable_Debugging')
PVR_SERVER    = '_channels_app._tcp'
REMOTE_URL    = 'http://my.channelsdvr.net'
BASE_URL      = 'http://%s:%s'%(REAL_SETTINGS.getSetting('User_IP'),REAL_SETTINGS.getSetting('User_Port')) #todo dns discovery?
TS            = '?format=ts' if REAL_SETTINGS.getSettingBool('Enable_TS') else ''
M3U_URL       = '%s/devices/ANY/channels.m3u%s'%(BASE_URL,TS)
GUIDE_URL     = '%s/devices/ANY/guide'%(BASE_URL)
UPNEXT_URL    = '%s/dvr/recordings/upnext'%(BASE_URL)
SEARCH_URL    = '%s/dvr/guide/search/groups?q={query}'%(BASE_URL)
SUMMARY_URL   = '%s/dvr/recordings/summary'%(BASE_URL)
GROUPS_URL    = '%s/dvr/groups'%(BASE_URL)
MOVIES_URL    = '%s/dvr/groups/movies/files'%(BASE_URL)
SOURCES_URL   = '%s/dvr/lineup'%(BASE_URL)
PROGRAMS_URL  = '%s/dvr/programs'%(BASE_URL)

CONTENT_TYPE  = 'episodes'
DISC_CACHE    = False
DTFORMAT      = '%Y-%m-%dT%H:%M:%S' #'YYYY-MM-DDTHH:MM:SS'

def notificationDialog(message, header=ADDON_NAME, sound=False, time=1000, icon=ICON):
    try:    return xbmcgui.Dialog().notification(header, message, icon, time, sound)
    except: return xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))

def strpTime(datestring, format='%Y-%m-%dT%H:%MZ'):
    try: return datetime.datetime.strptime(datestring, format)
    except TypeError: return datetime.datetime.fromtimestamp(time.mktime(time.strptime(datestring, format)))

def timezone():
    if time.localtime(time.time()).tm_isdst and time.daylight: return time.altzone / -(60*60) * 100
    else: return time.timezone / -(60*60) * 100
    
def getLocalTime():
    offset = (datetime.datetime.utcnow() - datetime.datetime.now())
    return time.time() + offset.total_seconds()
        
def log(msg, level=xbmc.LOGDEBUG):
    try:   msg = str(msg)
    except Exception as e: 'log str failed! %s'%(str(e))
    if not DEBUG and level != xbmc.LOGERROR: return
    try:   xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    except Exception as e: 'log failed! %s'%(e)

def getKeyboard(default='',header=ADDON_NAME):
    kb = xbmc.Keyboard(default,header)
    xbmc.sleep(1000)
    kb.doModal()
    if kb.isConfirmed(): return kb.getText()
    return False

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text
     
@ROUTER.route('/')
def buildMenu():
    Channels().buildMenu()
  
@ROUTER.route('/live')
def getLive():
    Channels().buildLive(favorites=False)
    
@ROUTER.route('/favorites')
def getLiveFavs():
    Channels().buildLive(favorites=True)
    
@ROUTER.route('/lineup')
def getLineup():
    Channels().buildLineup(chid=None)
    
@ROUTER.route('/channel/<chid>')
def getChannel(chid):
    Channels().buildLineup(chid)

@ROUTER.route('/play/pvr/<id>')
def playChannel(id):
    Channels().playLive(id,opt='pvr')

@ROUTER.route('/play/live/<id>')
def playChannel(id):
    Channels().playLive(id,opt='live')

@ROUTER.route('/iptv/channels')
def iptv_channels():
    """Return JSON-STREAMS formatted data for all live channels"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(ROUTER.args.get('port')[0])
    IPTVManager(port,Channels()).send_channels()

@ROUTER.route('/iptv/epg')
def iptv_epg():
    """Return JSON-EPG formatted data for all live channel EPG data"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(ROUTER.args.get('port')[0])
    IPTVManager(port,Channels()).send_epg()
    
class Channels(object):
    def __init__(self, sysARG=sys.argv):
        log('__init__, sysARG = %s'%(sysARG))
        self.sysARG     = sysARG
        self.cache      = SimpleCache()
        
        
    def openURL(self, url, life=datetime.timedelta(minutes=15)):
        log('openURL, url = %s'%(url))
        try:
            cacheName = '%s.%s.openURL.%s'%(ADDON_ID,ADDON_VERSION,url)
            cacheResponse = self.cache.get(cacheName)
            if not cacheResponse:
                req = requests.get(url, timeout=TIMEOUT)
                cacheResponse = req.text
                req.close()
                self.cache.set(cacheName, cacheResponse, checksum=len(cacheResponse), expiration=life)
            return cacheResponse
        except Exception as e: 
            log("openURL, Failed! %s"%(e), xbmc.LOGERROR)
            notificationDialog(LANGUAGE(30001))
            return ''
        

    def buildMenu(self):
        log('buildMenu')
        MENU = [(LANGUAGE(30002),(getLive,)),
                (LANGUAGE(30017),(getLiveFavs,)),
                (LANGUAGE(30003),(getLineup,))]
               #(LANGUAGE(30015), '', 2)]
               #(LANGUAGE(30013), '', 8)]
        for item in MENU: self.addDir(*item)


    def getChannels(self):
        log('getChannels')
        m3uListTMP = self.openURL(M3U_URL).split('\n')
        lines = ['%s\n%s'%(line,m3uListTMP[idx+1]) for idx, line in enumerate(m3uListTMP) if line.startswith('#EXTINF:')]
        items = []
        for line in lines:
            if line.startswith('#EXTINF:'):
                groups = re.compile('tvg-chno=\"(.*?)\" tvg-logo=\"(.*?)\" tvg-name=\"(.*?)\" group-title=\"(.*?)\",(.*)\\n(.*)', re.IGNORECASE).search(line)
                items.append({'number':groups.group(1),
                              'logo'  :groups.group(2),
                              'name'  :groups.group(3),
                              'groups':groups.group(4).split(';'),
                              'title' :groups.group(5),
                              'url'   :groups.group(6)})
        return sorted(items, key=lambda k: k['number'])


    def getGuidedata(self, version=ADDON_VERSION):
        log('getGuidedata')
        return json.loads(self.openURL(GUIDE_URL))


    def buildLive(self, favorites=False):
        log('buildLive')
        channels = self.getGuidedata()
        self.poolList(self.buildPlayItem, channels, ('live',favorites))
        
        
    def buildLineup(self, chid=None):
        log('buildLineup, chid = %s'%(chid))
        programmes = self.getGuidedata()
        if chid is None:
            self.poolList(self.buildLineupItem, programmes)
        else:
            data = [program for program in programmes if program['Channel']['Number'] == chid]
            self.poolList(self.buildPlayItem, data, ('lineup',False))

  
    def buildLineupItem(self, content):
        channel = content['Channel']
        label   = '%s| %s'%(channel['Number'],channel['Name'])
        art     = {"thumb" :channel.get('Image',ICON),
                   "poster":channel.get('Image',ICON),
                   "fanart":channel.get('Image',ICON),
                   "icon"  :channel.get('Image',ICON),
                   "logo"  :channel.get('Image',ICON)} 
        self.addDir(label, (getChannel,channel['Number']), infoArt=art)
        

    def buildPlayItem(self, data):
        content, opt   = data
        opt, favorites = opt
        channel    = content['Channel']
        programmes = content['Airings']
        liveMatch  = False
        if channel['Hidden'] == True: return
        elif favorites and not channel.get('Favorite',False): return
        tz  = (timezone()//100)*60*60
        now = (datetime.datetime.fromtimestamp(float(getLocalTime()))) + datetime.timedelta(seconds=tz)
        url = channel['Number']
        for program in programmes:
            try:
                label = program.get('Title','')
                path  = program.get('Path','')
                stop  = (strpTime(program['Raw']['endTime']))  + datetime.timedelta(seconds=tz)
                start = (strpTime(program['Raw']['startTime']))+ datetime.timedelta(seconds=tz)
                if now > stop: continue
                elif now >= start and now < stop:
                    if opt == 'live':
                        if label:
                            label = '%s| %s: [B]%s[/B]'%(channel['Number'],channel['Name'],program.get('Title',''))
                        else: 
                            label = '%s| %s'%(channel['Number'],channel['Name'])
                        liveMatch = True
                    elif opt == 'lineup':
                        label = '%s - [B]%s[/B]'%(start.strftime('%I:%M %p').lstrip('0'),program.get('Title',''))
                elif opt == 'live': continue
                elif opt == 'lineup':
                    url   = 'NEXT_SHOW'
                    label = '%s - %s'%(start.strftime('%I:%M %p').lstrip('0'),program.get('Title',''))
                icon  = channel.get('Image',ICON)
                thumb = program.get('Image',icon)
                info  = {'label':label,'title':label,'duration':program.get('Duration',0),'genre':program.get('Genres',[]),'plot':program.get('Summary',xbmc.getLocalizedString(161)),'aired':program.get('OriginalDate','')}
                art   = {'icon':icon, 'thumb':thumb}
                if opt == 'play': 
                    if start <= now and stop > now: info['duration'] = ((stop) - now).seconds
                    self.addPlaylist(label, url, info, art) 
                else: 
                    self.addLink(label, (playChannel,url), info, art, total=len(programmes))
                if liveMatch: break
            except: pass


    def resolveURL(self, id, opt):
        log('resolveURL, id = %s, opt = %s'%(id,opt))
        #todo if opt == live extra meta parse else pvr return link only
        self.listitems = []
        self.playlist  = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.playlist.clear()
        programmes = self.getGuidedata()
        data = [program for program in programmes if program['Channel']['Number'] == id]
        channel = list(filter(lambda channel:channel['number'] == id, self.getChannels()))[0]
        self.poolList(self.buildPlayItem, data, ('play',False))
        liz = xbmcgui.ListItem(channel['name'],path=channel['url'])
        liz.setProperty('IsPlayable','true')
        liz.setProperty('IsInternetStream','true')
        if opt != 'pvr':
            [self.playlist.add(channel['url'],lz,idx) for idx,lz in enumerate(self.listitems)]
            liz = self.listitems.pop(0)
            liz.setPath(path=channel['url'])
        return liz
        
 
    def playLive(self, id, opt='live'):
        log('playLive, id = %s, opt = %s'%(id,opt))
        if id == 'NEXT_SHOW': 
            found = False
            liz   = xbmcgui.ListItem(LANGUAGE(30029))
            notificationDialog(LANGUAGE(30012), time=4000)
        else:
            found = True
            liz   = self.resolveURL(id, opt)
            if 'm3u8' in liz.getPath().lower() and inputstreamhelper.Helper('hls').check_inputstream():
                if REAL_SETTINGS.getSettingBool('Enable_Timeshift'):
                    log('playLive, timeshift enabled')
                    liz.setProperty('inputstream','inputstream.ffmpegdirect')
                    liz.setProperty('inputstream.ffmpegdirect.stream_mode','timeshift')
                else:
                    liz.setProperty('inputstream','inputstream.adaptive')
                    liz.setProperty('inputstream.adaptive.manifest_type','hls')
                    liz.setProperty('inputstream.adaptive.mime_type','application/vnd.apple.mpegurl')
            if REAL_SETTINGS.getSettingBool('Enable_TS'): 
                log('playLive, TS-MPEG enabled')
                liz.setProperty('inputstream.adaptive.mime_type','video/mp2t')
        xbmcplugin.setResolvedUrl(ROUTER.handle, found, liz)

   
    def addPlaylist(self, name, path='', infoList={}, infoArt={}, infoVideo={}, infoAudio={}, infoType='video'):
        log('addPlaylist, name = %s'%name)
        liz = xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable','true')
        liz.setProperty('IsInternetStream','true')
        if infoList:  liz.setInfo(type=infoType, infoLabels=infoList)
        else:         liz.setInfo(type=infoType, infoLabels={"mediatype":infoType,"label":name,"title":name})
        if infoArt:   liz.setArt(infoArt)
        else:         liz.setArt({'thumb':ICON,'fanart':FANART})
        if infoVideo: liz.addStreamInfo('video', infoVideo)
        if infoAudio: liz.addStreamInfo('audio', infoAudio)
        self.listitems.append(liz)
    
    
    def addLink(self, name, uri=(''), infoList={}, infoArt={}, infoVideo={}, infoAudio={}, infoType='video', total=0):
        log('addLink, name = %s'%name)
        liz = xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable','true')
        liz.setProperty('IsInternetStream','true')
        if infoList:  liz.setInfo(type=infoType, infoLabels=infoList)
        else:         liz.setInfo(type=infoType, infoLabels={"mediatype":infoType,"label":name,"title":name})
        if infoArt:   liz.setArt(infoArt)
        else:         liz.setArt({'thumb':ICON,'fanart':FANART})
        if infoVideo: liz.addStreamInfo('video', infoVideo)
        if infoAudio: liz.addStreamInfo('audio', infoAudio)
        if infoList.get('favorite',None) is not None: liz = self.addContextMenu(liz, infoList)
        xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(*uri), liz, isFolder=False, totalItems=total)
                

    def addDir(self, name, uri=(''), infoList={}, infoArt={}, infoType='video'):
        log('addDir, name = %s'%name)
        liz = xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable','false')
        if infoList: liz.setInfo(type=infoType, infoLabels=infoList)
        else:        liz.setInfo(type=infoType, infoLabels={"mediatype":infoType,"label":name,"title":name})
        if infoArt:  liz.setArt(infoArt)
        else:        liz.setArt({'thumb':ICON,'fanart':FANART})
        if infoList.get('favorite',None) is not None: liz = self.addContextMenu(liz, infoList)
        xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(*uri), liz, isFolder=True)
        
        
    def addContextMenu(self, liz, infoList={}):
        log('addContextMenu')
        return liz
        
        
    def poolList(self, method, items=None, args=None, chunk=25):
        log("poolList")
        results = []
        if ENABLE_POOL:
            pool = ThreadPool(CORES)
            if args is not None: 
                results = pool.map(method, zip(items,repeat(args)))
            elif items: 
                results = pool.map(method, items)#, chunksize=chunk)
            pool.close()   
            pool.join()
        else:
            if args is not None: 
                results = [method((item, args)) for item in items]
            elif items: 
                results = [method(item) for item in items]
        return filter(None, results)


    def buildChannels(self):
        log('buildChannels')
        # https://github.com/add-ons/service.iptv.manager/wiki/JSON-STREAMS-format
        channels  = self.getChannels()
        guidedata = self.getGuidedata()
        return list(self.poolList(self.buildStation, guidedata, (channels,'channel')))


    def buildGuide(self):
        log('getGuide')
        # https://github.com/add-ons/service.iptv.manager/wiki/JSON-EPG-format
        channels  = self.getChannels()
        guidedata = self.getGuidedata()
        return {k:v for x in self.poolList(self.buildStation, guidedata,(channels,'programmes')) for k,v in x.items()}
        

    def buildStation(self, data):
        content, data = data
        channels, opt = data
        station  = content['Channel']
        cdata    = list(filter(lambda c:c['number'] == station['Number'], channels))[0]
        favorite = 'Favorites' in cdata['groups']
        cdata['groups'].append(ADDON_NAME)
        channel  = {"name"  :station['Name'],
                    "stream":"plugin://%s/play/pvr/%s"%(ADDON_ID,station['Number']), 
                    "id"    :"%s.%s@%s"%(station['Number'],slugify(station['Name']),slugify(ADDON_NAME)), 
                    "logo"  :(station.get('Image','') or ICON), 
                    "preset":station['Number'],
                    "group" :';'.join(cdata['groups']),
                    "radio" :False}
        if REAL_SETTINGS.getSettingBool('Build_Favorites') and not favorite: return None
        elif opt == 'channel': return channel
        else:
            programmes = {channel['id']:[]}
            listings   = content.get('Airings',[])
            for listing in listings:
                try: starttime = strpTime(listing['Raw']['startTime'])
                except: continue
                try:    aired = strpTime(listing['OriginalDate'], '%Y-%m-%d')
                except: aired = starttime
                program = {"start"      :starttime.strftime(DTFORMAT),
                           "stop"       :(starttime + datetime.timedelta(seconds=listing.get('Duration',0))).strftime(DTFORMAT),
                           "title"      :listing.get('Title',channel['name']),
                           "description":(listing.get('Summary','') or xbmc.getLocalizedString(161)),
                           "subtitle"   :listing.get('EpisodeTitle',''),
                           "episode"    :"S%sE%s"%(str(listing.get('SeasonNumber',0)).zfill(2),str(listing.get('EpisodeNumber',0)).zfill(2)),
                           "genre"      :listing.get('Categories',[]),
                           "image"      :(listing.get('Image','') or channel['logo']),
                           "date"       :aired.strftime('%Y-%m-%d'),
                           "credits"    :"",
                           "stream"     :""}
                programmes[channel['id']].append(program)
            return programmes


    # def buildRecordingItem(self, item):
        # item['Airings'] = [item['Airing'].copy()]
        # item['Channel'] = {'Hidden':False,'Number':0,'Name':'','Image':''}
        # self.buildPlayItem((item,'recordings'))
        
            
    # def buildRecordings(self):
        # self.poolList(self.buildRecordingItem, json.loads(self.openURL(UPNEXT_URL)))
            
        
    # def search(self, term=None):
        # #todo match id with programmes
        # if term is None: term = getKeyboard(header=LANGUAGE(30014))
        # if term:
            # log('search, term = %s'%(term))
            # query = json.loads(self.openURL(SEARCH_URL.format(query=term)))


    def run(self): 
        ROUTER.run()
        xbmcplugin.setContent(ROUTER.handle     ,CONTENT_TYPE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(ROUTER.handle ,cacheToDisc=DISC_CACHE)