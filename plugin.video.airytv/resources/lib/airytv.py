#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of AiryTV.
#
# AiryTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# AiryTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AiryTV.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, _strptime, datetime, re, traceback, uuid, routing
import socket, json, inputstreamhelper, requests, collections

from six.moves     import urllib
from simplecache   import SimpleCache, use_cache
from itertools     import repeat, cycle, chain, zip_longest
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode
from favorites     import *

try:
    from multiprocessing import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
    CORES = cpu_count()
except: ENABLE_POOL = False

try:
  basestring #py2
except NameError: #py3
  basestring = str
  unicode = str
  
# Plugin Info
ADDON_ID      = 'plugin.video.airytv'
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
LOGO          = os.path.join('special://home/addons/%s/'%(ADDON_ID),'resources','images','logo.png')
DEBUG         = REAL_SETTINGS.getSettingBool('Enable_Debugging')
BASE_API      = 'https://api.airy.tv/api/v2.1.0/channels?isIos=false&type=desktop&device=website&version=1.0&timezone={tz}'
LOGO_URL      = 'https://dummyimage.com/512x512/035e8b/FFFFFF.png&text=%s'
FAN_URL       = 'https://dummyimage.com/1280x720/035e8b/FFFFFF.png&text=%s'

CONTENT_TYPE  = 'episodes'
DISC_CACHE    = False
DTFORMAT      = '%Y-%m-%dT%H:%M:%S' #'YYYY-MM-DDTHH:MM:SS'
UTC_OFFSET    = datetime.datetime.utcnow() - datetime.datetime.now()

@ROUTER.route('/')
def buildMenu():
    AIRYTV().buildMenu()

@ROUTER.route('/live')
def getLive():
    AIRYTV().buildChannels(opt='live')
    
@ROUTER.route('/favorites')
def getLiveFavs():
    AIRYTV().buildChannels(opt='favorites')

@ROUTER.route('/lineup')
def getLineups():
    AIRYTV().buildLineups()
       
@ROUTER.route('/lineup/<id>')
def getLineup(id):
    AIRYTV().buildChannel((AIRYTV().getChannel(id),'lineup'))

@ROUTER.route('/categories')
def getCats():
    AIRYTV().buildCategories()
         
@ROUTER.route('/categories/<cat>')
def getCat(cat):
    AIRYTV().buildLineups(cat=cat)

@ROUTER.route('/play/vod')#unknown bug causing this route to be called during /ondemand parse. todo find issue.
def dummy():
    pass

@ROUTER.route('/play/vod/<id>/<epid>')
def playOD(id,epid):
    AIRYTV().playVOD(id,epid)
    
@ROUTER.route('/play/pvr/<id>')
def playChannel(id):
    AIRYTV().playLive(id,opt='pvr')

@ROUTER.route('/play/live/<id>')
def playChannel(id):
    AIRYTV().playLive(id,opt='live')

@ROUTER.route('/iptv/channels')
def iptv_channels():
    """Return JSON-STREAMS formatted data for all live channels"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(ROUTER.args.get('port')[0])
    IPTVManager(port,AIRYTV()).send_channels()

@ROUTER.route('/iptv/epg')
def iptv_epg():
    """Return JSON-EPG formatted data for all live channel EPG data"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(ROUTER.args.get('port')[0])
    IPTVManager(port,AIRYTV()).send_epg()
     
def strpTime(datestring):
    try: return datetime.datetime.fromisoformat(datestring)
    except TypeError: return datetime.datetime.fromisoformat(datestring)

def getTZ():
    if time.localtime(time.time()).tm_isdst and time.daylight: return int(time.altzone / -(60*60))
    else: return int(time.timezone / -(60*60))
    
def getLocalTime():
    offset = (datetime.datetime.utcnow() - datetime.datetime.now())
    return time.time() + offset.total_seconds()

def getOffsetTime():
    try:    return (sum(x*y for x, y in zip(map(float, str(UTC_OFFSET).split(':')[::-1]), (1, 60, 3600, 86400))))
    except: return 0   
        
def log(msg, level=xbmc.LOGDEBUG):
    try:   msg = str(msg)
    except Exception as e: 'log str failed! %s'%(str(e))
    if not DEBUG and level != xbmc.LOGERROR: return
    try:   xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    except Exception as e: 'log failed! %s'%(e)
     
def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

class AIRYTV(object):
    def __init__(self, sysARG=sys.argv):
        log('__init__, sysARG = %s'%(sysARG))
        self.sysARG    = sysARG
        self.cache     = SimpleCache()
        self.channels  = self.getChanneldata()
        
            
    def getURL(self, url, param={}, header={'User-agent': 'Mozilla/5.0 (Windows NT 6.2; rv:24.0) Gecko/20100101 Firefox/24.0'}, life=datetime.timedelta(minutes=15)):
        log('getURL, url = %s, header = %s'%(url, header))
        cacheresponse = self.cache.get('%s.getURL, url = %s.%s.%s'%(ADDON_ID,url,param,header))
        if not cacheresponse:
            try:
                req = requests.get(url, param, headers=header)
                cacheresponse = req.json()
                req.close()
            except Exception as e: 
                log("getURL, Failed! %s"%(e), xbmc.LOGERROR)
                notificationDialog(LANGUAGE(30001))
                return {}
            self.cache.set('%s.getURL, url = %s.%s.%s'%(ADDON_ID,url,param,header), json.dumps(cacheresponse), expiration=life)
            return cacheresponse
        return json.loads(cacheresponse)


    def buildMenu(self):
        log('buildMenu')
        AIRY_MENU = [(LANGUAGE(30011),(getLive    ,)),
                     (LANGUAGE(30040),(getLiveFavs,)),
                     (LANGUAGE(30018),(getLineups ,)),
                     (LANGUAGE(30017),(getCats    ,))]
        for item in AIRY_MENU: self.addDir(*item)


    def getChanneldata(self):
        log('getChanneldata')
        collect    = {}
        echannels  = []
        categories = self.getURL(BASE_API.format(tz=getTZ()), life=datetime.timedelta(hours=1)).get('response',{}).get('categories',[])
        for category in categories:
            genre    = self.cleanString(category.get('name'))
            channels = (category.get('banners',[]) + category.get('stream_channels',[]) + category.get('channels',[]))
            for channel in channels:
                channel['category'] = genre
                channel['name']     = self.cleanString(channel.get('name'))
                if channel['name'] not in echannels: #catch dups; lazy fix
                    echannels.append(channel['name'])
                    collect.setdefault(genre,[]).append(channel)
        return collect


    def getCategories(self):
        log('getCategories')
        return self.channels.keys()
    
    
    def getChannels(self):
        log('getChannels')
        categories = self.getCategories()
        for category in categories:
            channels = self.channels.get(category,[])
            for channel in channels: 
                yield channel
        
    
    def getChannel(self, id):
        log('getChannel, id = %s'%(id))
        channels = self.getChannels()
        for channel in channels:
            if channel.get('id') == int(id): return channel
        return {}
        
        
    def getBroadcast(self, id, epid):
        log('getBroadcast, id = %s, epid = %s'%(id, epid))
        channel = self.getChannel(id)
        broadcasts = channel.get('broadcasts',[])
        for broadcast in broadcasts:
            if broadcast.get('id') == int(epid): return channel, broadcast
        return {},{}
        
        
    def buildCategories(self, cat=None):
        log('buildCategories, cat = %s'%(cat))
        for category in self.getCategories():
            if cat and cat != category: continue 
            self.addDir(category, uri=(getCat,category),infoArt={'thumb':LOGO_URL%(category),'fanart':FANART})
            
                
    def buildLineups(self, id=None, cat=None):
        log('buildLineups, id = %s, cat = %s'%(id,cat))
        for channel in self.getChannels():
            if id  and channel.get('id') != int(id): continue 
            if cat and channel.get('category') != cat: continue 
            self.addDir(channel.get('name'), uri=(getLineup,channel.get('id')), infoArt={'thumb':LOGO_URL%(channel.get('name')),'fanart':FANART})
            
        
    def buildChannels(self, opt='live'):
        log('buildChannels, opt=%s'%(opt))
        return list(self.poolList(self.buildChannel,self.getChannels(),opt))


    def buildChannel(self, data):
        channel, opt = data
        log('buildChannel, channel = %s, opt=%s'%(channel.get('id'),opt))
        stname     = channel.get('name')
        stnum      = channel.get('number')
        broadcasts = channel.get('broadcasts',[])
        favorite   = isFavorite(stnum)
        if opt == 'iptv_channel':
            channel  = {"name"  :stname,
                        "stream":"plugin://%s/play/pvr/%s"%(ADDON_ID,channel.get('id')), 
                        "id"    :"%s.%s@%s"%(stnum,slugify(stname),slugify(ADDON_NAME)), 
                        "logo"  :LOGO,
                        "preset":stnum,
                        "group" :[channel.get('category'),ADDON_NAME],
                        "radio" :False}
            if favorite: channel['group'].append(LANGUAGE(49012))
            channel['group'] = ';'.join(channel['group'])
            if REAL_SETTINGS.getSettingBool('Build_Favorites') and not favorite: return None
            return channel
        else:
            return self.buildBroadcasts(channel, broadcasts, opt)
            
                
    def buildBroadcasts(self, channel, broadcasts, opt=''):
        log('buildBroadcasts, channel = %s, opt = %s'%(channel.get('id'),opt))
        id         = channel.get('id')
        hls        = channel.get('hls',False)
        name       = channel.get('name')
        number     = channel.get('number')
        category   = channel.get('category')
        favorite   = isFavorite(number)
        programmes = {id:[]}
        now        = datetime.datetime.now().astimezone().replace(microsecond=0)
        for idx, broadcast in enumerate(broadcasts):            
            """{
                'id': 3092301,
                'title': 'Mankind From Space',
                'parts': [{
                    'duration': 2617,
                    'source_url': 'https://ia801605.us.archive.org/12/items/National.GeographicAlien.Earths2009.720p.AC3_201702/National.Geographic%20-%20Mankind.From.Space%20-%202015.720p.AAC.mp4',
                    'start_at_iso': '2021-03-18T14:35:24-04:00'
                }],
                'description': "Trace humankind's long journey from hunter-gatherer to dominant global species. From the perspective of space, this two-hour special uses mind-boggling data and CGI to disclose the breathtaking extent of humanity's influence, revealing how we've transformed our planet and produced an interconnected world of extraordinary complexity. A trip through 12,000 years of development, the documentary shows how seemingly small flashes of innovation - innovations that touch all of us in ways unimaginable to our ancestors - have changed the course of civilization. As our global population soars, the program considers the challenges humanity will face in order to survive.",
                'view_duration': 1141,
                'stream_duration': 2617,
                'view_start_at_iso': '2021-03-18T15:00:00-04:00',
                'stream_start_at_iso': '2021-03-18T14:35:24-04:00'
                }"""
            """{
                'id': 3121442,
                'title': 'Fishing Offshore',
                'description': 'Fishing Offshore',
                'view_duration': 1391,
                'stream_duration': 2700,
                'view_start_at_iso': '2021-03-24T18:00:00-04:00',
                'stream_start_at_iso': '2021-03-24T17:38:11-04:00'
                }"""
            try: starttime  = strpTime(broadcast['stream_start_at_iso'])
            except: continue
                
            offsettime = strpTime(broadcast.get('view_start_at_iso'))
            remaining  = (broadcast.get('view_duration',0))
            duration   = (broadcast.get('stream_duration','') or remaining)
            stoptime   = (starttime + datetime.timedelta(seconds=duration))
            epid       = (broadcast.get('id'))
            title      = (broadcast.get('title')       or name)
            plot       = (broadcast.get('description') or xbmc.getLocalizedString(161))
            
            parts      = (broadcast.get('parts',[]))
            for part in  parts:
                runtime = (part.get('duration',0))
                stream  = (part.get('source_url'))
                start   = strpTime(part.get('start_at_iso'))
                
            if hls: uri=(playChannel,id)
            else:   uri=(playOD,id,epid)
                
            if opt == 'iptv_broadcasts':
                program = {"start"      :starttime.strftime(DTFORMAT),
                           "stop"       :stoptime.strftime(DTFORMAT),
                           "title"      :title,
                           "description":plot,
                           "subtitle"   :"",
                           "episode"    :"",
                           "genre"      :category,
                           "image"      :FANART,
                           "date"       :starttime.strftime('%Y-%m-%d'),
                           "credits"    :"",
                           "stream"     :"plugin://%s/play/vod/%s"%(ADDON_ID,epid)}
                programmes[id].append(program)
            
            elif opt in ['live','favorites','broadcast']:
                chname = '%s| %s'%(number,name)
                label  = '%s : [B] %s[/B]'%(chname, title)
                if opt == 'favorites' and not favorite: return None
                    
                if now >= starttime and now < stoptime: 
                    if opt == 'broadcast': return broadcast
                    return self.addLink(label, uri, infoList={"favorite":favorite,"chnum":number,"chname":name,"mediatype":"video","label":label,"title":label}, infoArt={'thumb':LOGO_URL%(name),'fanart':FANART})

            elif opt == 'lineup':
                if stoptime < now: continue
                elif now >= starttime and now < stoptime: 
                    label = '%s - [B]%s[/B]'%(starttime.strftime('%I:%M %p').lstrip('0'),title)
                else: 
                    label  = '%s - %s'%(starttime.strftime('%I:%M %p').lstrip('0'),title)
                    uri    = list(uri)
                    uri[1] = 'NEXT_SHOW'
                    uri    = tuple(uri)
                self.addLink(label, uri, infoList={"favorite":favorite,"chnum":number,"chname":name,"mediatype":"video","label":label,"title":label}, infoArt={'thumb':LOGO_URL%(name),'fanart':FANART})

        return programmes
        
        
    def cleanString(self, text):
        return text.replace('_',' ')


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

    
    def resolveYoutube(self, url, seek=0):
        log('resolveYoutube, url = %s, seek = %s'%(url,seek))
        """Returns Video_ID extracting from the given url of Youtube
        Examples of URLs:
          Valid:
            'http://youtu.be/_lOT2p_FCvA',
            'www.youtube.com/watch?v=_lOT2p_FCvA&feature=feedu',
            'http://www.youtube.com/embed/_lOT2p_FCvA',
            'http://www.youtube.com/v/_lOT2p_FCvA?version=3&amp;hl=en_US',
            'https://www.youtube.com/watch?v=rTHlyTphWP0&index=6&list=PLjeDyYvG6-40qawYNR4juzvSOg-ezZ2a6',
            'youtube.com/watch?v=_lOT2p_FCvA',
          Invalid:
            'youtu.be/watch?v=_lOT2p_FCvA',
        """

        if url.startswith(('youtu', 'www')):
            url = 'http://%s'%url
        query = urllib.parse.urlparse(url)
        if 'youtube' in query.hostname:
            if query.path == '/watch':
                match = urllib.parse.parse_qs(query.query)['v'][0]
            elif query.path.startswith(('/embed/', '/v/')):
                match = query.path.split('/')[2]
        elif 'youtu.be' in query.hostname:
            match = query.path[1:]
        else:
            match = None
        if match:
            return 'plugin://plugin.video.tubed/?mode=play&video_id={vid}&start_offset={offset}'.format(vid=match, offset=float(seek))
        return url
    

    def resolveURL(self, id, opt, epid=None ):
        log('resolveURL, id = %s, opt = %s, epid = %s'%(id,opt,epid))
        lizs = []
        urls = []
        if opt == 'live':
            channel   = self.getChannel(id)
            urls      = [channel.get('source_url')]
            broadcast = self.buildChannel((channel,'broadcast'))
            runtime   = (broadcast.get('stream_duration',0))
        elif opt == 'vod':
            channel, broadcast = self.getBroadcast(id,epid)
            parts   = (broadcast.get('parts',[]))
            runtime = (broadcast.get('stream_duration',0))
            for part in  parts: urls.append(part.get('source_url'))
        if not urls: urls = [channel.get('source_url')]
        for url in urls:
            name = (broadcast.get('title'))
            liz  = xbmcgui.ListItem(name)
            if xbmcgui.Window(10000).getProperty('PseudoTVRunning') == "True":
                liz.setPath(self.resolveYoutube(url))
            else: #apply channel offset when not using PseudoTV
                liz.setPath(self.resolveYoutube(url,broadcast.get('view_duration',0)))
            liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name,"duration":runtime,"plot":(broadcast.get('description',''))})
            liz.setArt({'thumb':ICON,'fanart':FANART,"icon":LOGO,"logo":LOGO,"clearart":LOGO})
            liz.setProperty("IsPlayable","true")
            if 'm3u8' in url.lower() and inputstreamhelper.Helper('hls').check_inputstream():
                liz.setProperty('IsInternetStream','true')
                liz.setProperty('inputstream','inputstream.adaptive')
                liz.setProperty('inputstream.adaptive.manifest_type','hls')
            return liz  #todo playlist?
        return xbmcgui.ListItem()

        # # 
        # self.listitems = []
        # self.playlist  = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        # self.playlist.clear()
        # channel = list(filter(lambda k:k.get('_id','') == id, self.getGuidedata()))[0]
        # urls = channel.get('stitched',{}).get('urls',[])
        # if isinstance(urls, list): urls = [url['url'] for url in urls if url['type'].lower() == 'hls'][0]
        # liz = xbmcgui.ListItem(channel.get('name'),path=urls)
        # liz.setProperty('IsPlayable','true')
        # liz.setProperty('IsInternetStream','true')
        # if opt != 'pvr':
            # self.browseGuide(opt='play',data=[channel])
            # [self.playlist.add(urls,lz,idx) for idx,lz in enumerate(self.listitems)]
            # liz = self.listitems.pop(0)
            # liz.setPath(path=urls)
        # return liz
        

    def playVOD(self, id, epid):
        log('playVOD, id = %s, epid = %s'%(id,epid))
        liz = self.resolveURL(id,'vod',epid)
        log('playVOD, url = %s'%(liz.getPath()))   
        xbmcplugin.setResolvedUrl(ROUTER.handle, True, liz)
        
        
    def playLive(self, id, opt='live'):
        log('playLive, id = %s, opt = %s'%(id,opt))
        if id == 'NEXT_SHOW': 
            found = False
            liz   = xbmcgui.ListItem()
            notificationDialog(LANGUAGE(30029), time=4000)
        else:
            found = True
            liz   = self.resolveURL(id, opt)
            log('playLive, url = %s'%(liz.getPath()))  
        xbmcplugin.setResolvedUrl(ROUTER.handle, found, liz)

           
    def addPlaylist(self, name, path='', infoList={}, infoArt={}, infoVideo={}, infoAudio={}, infoType='video'):
        log('addPlaylist, name = %s'%name)
        liz = xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable','true')
        liz.setProperty('IsInternetStream','true')
        if infoList:  liz.setInfo(type=infoType, infoLabels=infoList)
        else:         liz.setInfo(type=infoType, infoLabels={"mediatype":infoType,"label":name,"title":name})
        if infoArt:   liz.setArt(infoArt)
        else:         liz.setArt({'thumb':ICON,'fanart':FANART,"icon":LOGO,"logo":LOGO,"clearart":LOGO})
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
        else:         liz.setArt({'thumb':ICON,'fanart':FANART,"icon":LOGO,"logo":LOGO,"clearart":LOGO})
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
        else:        liz.setArt({'thumb':ICON,'fanart':FANART,"icon":LOGO,"logo":LOGO,"clearart":LOGO})
        if infoList.get('favorite',None) is not None: liz = self.addContextMenu(liz, infoList)
        xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(*uri), liz, isFolder=True)
        
        
    def addContextMenu(self, liz, infoList={}):
        log('addContextMenu')
        if infoList['favorite']:
            liz.addContextMenuItems([(LANGUAGE(49010), 'RunScript(special://home/addons/%s/favorites.py, %s)'%(ADDON_ID,urllib.parse.quote(json.dumps({"chnum":infoList.pop('chnum'),"chname":infoList.pop('chname'),"mode":"del"}))))])
        else:
            liz.addContextMenuItems([(LANGUAGE(49009), 'RunScript(special://home/addons/%s/favorites.py, %s)'%(ADDON_ID,urllib.parse.quote(json.dumps({"chnum":infoList.pop('chnum'),"chname":infoList.pop('chname'),"mode":"add"}))))])
        return liz
        
        
    def run(self): 
        ROUTER.run()
        xbmcplugin.setContent(ROUTER.handle     ,CONTENT_TYPE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(ROUTER.handle ,cacheToDisc=DISC_CACHE)