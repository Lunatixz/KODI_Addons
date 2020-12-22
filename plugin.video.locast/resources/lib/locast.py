#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of Locast.
#
# Locast is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Locast is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Locast.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, re, sched, time, threading, urllib, distutils
import random, string, traceback
import socket, json, inputstreamhelper, requests
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

from six.moves import urllib
from simplecache import SimpleCache, use_cache

try:
    from multiprocessing import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
except: ENABLE_POOL = False
        
try:
  basestring #py2
except NameError: #py3
  basestring = str
  unicode = str
  
# Plugin Info
ADDON_ID      = 'plugin.video.locast'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
TIMEOUT       = 15
CONTENT_TYPE  = 'episodes'
USER_EMAIL    = REAL_SETTINGS.getSetting('User_Email')
PASSWORD      = REAL_SETTINGS.getSetting('User_Password')
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
TOKEN         = REAL_SETTINGS.getSetting('User_Token')
FREEREFRESH   = int(REAL_SETTINGS.getSetting('Free_RefreshRate'))
BASE_URL      = 'https://www.locast.org'
BASE_API      = 'https://api.locastnet.org/api'
GEO_URL       = 'http://ip-api.com/json'

MAIN_MENU     = [(LANGUAGE(30003), '' , 3),
                 (LANGUAGE(30004), '' , 4),
                 (LANGUAGE(30005), '' , 20)]
SCHEDULER = sched.scheduler(time.time, time.sleep)

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg), level)
    
def uni(string1, encoding = 'utf-8'):
    if isinstance(string1, basestring):
        if not isinstance(string1, unicode): string1 = unicode(string1, encoding)
        elif isinstance(string1, unicode): string1 = string1.encode('ascii', 'replace')
    return string1  
        
def inputDialog(heading=ADDON_NAME, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    retval = xbmcgui.Dialog().input(heading, default, key, opt, close)
    if len(retval) > 0: return retval    
    
def okDialog(str1, str2='', str3='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2, str3)

def okDisable(string1):
    if yesnoDialog(string1, no=LANGUAGE(30009), yes=LANGUAGE(30015)): 
        results = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":False}, "id": 1}'%ADDON_ID)
        if results and "OK" in results: notificationDialog(LANGUAGE(30016))
    else: sys.exit()
        
def yesnoDialog(str1, str2='', str3='', header=ADDON_NAME, yes='', no='', autoclose=0):
    return xbmcgui.Dialog().yesno(header, str1, str2, str3, no, yes, autoclose)
    
def notificationDialog(message, header=ADDON_NAME, sound=False, time=1000, icon=ICON):
    try: xbmcgui.Dialog().notification(header, message, icon, time, sound)
    except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
     

def toBool(str):
    if type(str) == str:
        lowerStr = str.lower()
        if lowerStr == 'true':
            return True
        elif lowerStr == 'false':
            return False
        else:
            log('toBool failed for string %s'%(str))
            raise ValueError
    else:
        return str


socket.setdefaulttimeout(TIMEOUT) 
class Locast(object):
    def __init__(self, sysARG):
        log('__init__, sysARG = %s'%(sysARG))
        self.sysARG = sysARG
        self.cacheToDisc = True
        self.token   = (TOKEN or None)
        self.cache   = SimpleCache()
        self.lastDMA = 0
        self.now     = datetime.datetime.now()
        self.lat, self.lon = self.setRegion()
        self.player  = None
        if self.login(USER_EMAIL, PASSWORD) == False: sys.exit()  


    def getURL(self, url, param={}, header={}, life=datetime.timedelta(minutes=15)):
        log('getURL, url = %s, header = %s'%(url, header))
        cacheresponse = self.cache.get(ADDON_NAME + '.getURL, url = %s.%s.%s'%(url,param,header))
        if DEBUG: cacheresponse = None
        if not cacheresponse:
            try:
                req = requests.get(url, param, headers=header)
                cacheresponse = req.json()
                req.close()
                self.cache.set(ADDON_NAME + '.getURL, url = %s.%s.%s'%(url,param,header), json.dumps(cacheresponse), expiration=life)
                return cacheresponse
            except Exception as e: 
                log("getURL, Failed! %s"%(e), xbmc.LOGERROR)
                notificationDialog(LANGUAGE(30001))
                return {}
        else: return json.loads(cacheresponse)


    def postURL(self, url, param={}, header={}, life=datetime.timedelta(minutes=15)):
        log('postURL, url = %s, header = %s'%(url, header))
        cacheresponse = self.cache.get(ADDON_NAME + '.postURL, url = %s.%s.%s'%(url,param,header))
        if DEBUG: cacheresponse = None
        if not cacheresponse:
            try:#post
                req = requests.post(url, param, headers=header)
                cacheresponse = req.json()
                req.close()
                self.cache.set(ADDON_NAME + '.postURL, url = %s.%s.%s'%(url,param,header), json.dumps(cacheresponse), expiration=life)
                return cacheresponse
            except Exception as e: 
                log("postURL, Failed! %s"%(e), xbmc.LOGERROR)
                notificationDialog(LANGUAGE(30001))
                return {}
        else: return json.loads(cacheresponse)
            
            
    def buildHeader(self):
        header_dict                 = {}
        header_dict['Accept']       = 'application/json, text/javascript, */*; q=0.01'
        header_dict['Content-Type'] = 'application/json'
        header_dict['Connection']   = 'keep-alive'
        header_dict['Origin']       = BASE_URL
        header_dict['Referer']      = BASE_URL
        header_dict['Authorization'] = "Bearer %s" % self.token
        header_dict['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'
        return header_dict


    def genClientID(self):
        return  urllib.parse.quote(''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits + '=' + '+') for _ in range(24)))
            
            
    def chkUser(self, user):
        log('chkUser')
        try:    self.userdata = self.getURL(BASE_API + '/user/me',header=self.buildHeader())
        except: self.userdata = {}
        if self.userdata.get('email','').lower() == user.lower(): return True
        return False


    def login(self, user, password):
        log('login')
        if len(user) > 0:
            if self.chkUser(user) == True: return True
            data = self.postURL(BASE_API + '/user/login','{"username":"' + user + '","password":"' + password + '"}',self.buildHeader())
            '''{u'token': u''}'''
            if data and 'token' in data: 
                self.token = data['token']
                if TOKEN != self.token: REAL_SETTINGS.setSetting('User_Token',self.token)
                if self.chkUser(user): 
                    REAL_SETTINGS.setSetting('User_totalDonations',str(self.userdata.get('totalDonations','0')))
                    REAL_SETTINGS.setSetting('User_DonateExpire',datetime.datetime.fromtimestamp(float(str(self.userdata.get('donationExpire','')).rstrip('L'))/1000).strftime("%Y-%m-%d %I:%M %p"))
                    REAL_SETTINGS.setSetting('User_Donate',str(self.userdata.get('didDonate','False')))
                    REAL_SETTINGS.setSetting('User_LastLogin',datetime.datetime.fromtimestamp(float(str(self.userdata.get('lastlogin','')).rstrip('L'))/1000).strftime("%Y-%m-%d %I:%M %p"))
                    self.lastDMA = self.userdata.get('lastDmaUsed','')
                    notificationDialog(LANGUAGE(30021)%(self.userdata.get('name','')))
                    return True
            else: notificationDialog(LANGUAGE(30017)) 
        else:
            #firstrun wizard
            if yesnoDialog(LANGUAGE(30008),no=LANGUAGE(30009), yes=LANGUAGE(30010)):
                user     = inputDialog(LANGUAGE(30006))
                password = inputDialog(LANGUAGE(30007),opt=xbmcgui.ALPHANUM_HIDE_INPUT)
                REAL_SETTINGS.setSetting('User_Email'   ,user)
                REAL_SETTINGS.setSetting('User_Password',password)
                return self.login(user, password)
            else: okDialog(LANGUAGE(30012))
        return False

                                                                
    def getEPG(self, city):
        log("getEPG, city = %s"%city)
        '''[{"id":104,"dma":501,"name":"WCBSDT (WCBS-DT)","callSign":"WCBS","logoUrl":"https://fans.tmsimg.com/h5/NowShowing/28711/s28711_h5_aa.png","active":true,"affiliate":"CBS","affiliateName":"CBS",
             "listings":[{"stationId":104,"startTime":1535410800000,"duration":1800,"isNew":true,"audioProperties":"CC, HD 1080i, HDTV, New, Stereo","videoProperties":"CC, HD 1080i, HDTV, New, Stereo","programId":"EP000191906491","title":"Inside Edition","description":"Primary stories and alternative news.","entityType":"Episode","airdate":1535328000000,"genres":"Newsmagazine","showType":"Series"}]}'''
        now = ('{0:.23s}{1:s}'.format(datetime.datetime.now().strftime('%Y-%m-%dT00:00:00'),'-05:00'))
        return self.getURL(BASE_API + '/watch/epg/%s'%(city), param={'start_time':urllib.parse.quote(now)}, header=self.buildHeader(), life=datetime.timedelta(minutes=45))
        
        
    def getCity(self):
        log("getCity")
        '''{u'active': True, u'DMA': u'501', u'small_url': u'https://s3.us-east-2.amazonaws.com/static.locastnet.org/cities/new-york.jpg', u'large_url': u'https://s3.us-east-2.amazonaws.com/static.locastnet.org/cities/background/new-york.jpg', u'name': u'New York'}'''
        try:
            city = self.getURL(BASE_API + '/watch/dma/%s/%s'%(self.lat,self.lon),header=self.buildHeader())
            if city and 'DMA' not in city: okDisable(city.get('message'))
            else:
                REAL_SETTINGS.setSetting('User_City',str(city['name']))
                return city
        except: okDisable(LANGUAGE(30013))


    # @use_cache(1)
    def setRegion(self):
        try: geo_data = json.load(urllib.request.urlopen(GEO_URL))
        except: geo_data = {'lat':0.0,'lon':0.0}
        return float('{0:.7f}'.format(geo_data['lat'])), float('{0:.7f}'.format(geo_data['lon']))

        
    def getRegion(self):
        log("getRegion")
        try: return self.getCity()['DMA']
        except: return self.lastDMA if self.lastDMA > 0 else sys.exit()
        

    def getStations(self, name, city, opt=None):
        log("getStations, name = %s, city = %s, opt = %s"%(name, city, opt))
        stations = self.getEPG(city)
        for station in stations:
            if station['active'] == False: continue
            path     = str(station['id'])
            thumb    = (station.get('logoUrl','') or station.get('logo226Url','') or ICON)
            listings = station['listings']
            label    = (station.get('affiliateName','') or station.get('affiliate','') or station.get('callSign','') or station.get('name',''))
            stnum    = re.sub('[^\d\.]+','', label)
            if stnum:
                stname    = re.compile('[^a-zA-Z]').sub('', label)
                stlabel   = '%s| %s'%(stnum,stname)
            else: stlabel = label
            if opt == 'Live':
                self.cacheToDisc = False
                self.buildListings(listings, label, thumb, path, opt)
            elif opt == 'Lineup' and (name.lower() == stlabel.lower()):
                self.cacheToDisc = False
                self.buildListings(listings, label, thumb, path, opt)
            elif opt == 'Lineups': 
                chnum  = re.sub('[^\d\.]+','', label)
                if chnum:
                    chname = re.compile('[^a-zA-Z]').sub('', label)
                    label  = '%s| %s'%(chnum,chname)
                else: label = chname
                self.addDir(label, city, 5, infoArt={"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON})
            else: continue
        
        
    def buildMenu(self, city):
        [self.addDir(item[0],city,item[2]) for item in MAIN_MENU]
            
            
    def buildListings(self, listings, chname, chlogo, path, opt='uEPG'):
        log('buildListings, chname = %s, opt = %s'%(chname,opt))
        now = datetime.datetime.now()
        for listing in listings:
            try: starttime  = datetime.datetime.fromtimestamp(int(str(listing['startTime'])[:-3]))
            except: continue
            duration   = listing.get('duration',0)
            endtime    = starttime + datetime.timedelta(seconds=duration)
            label      = listing['title']
            # if listing['isNew']: label = '*%s'%label
            try: aired = datetime.datetime.fromtimestamp(int(str(listing['airdate'])[:-3]))
            except: aired = starttime
            try: type  = {'Series':'episode'}[listing.get('showType','Series')]
            except: type = 'video'
            plot = (listing.get('description','') or listing.get('shortDescription','') or label)
            if now > endtime: continue
            elif opt == 'Live': 
                chnum  = re.sub('[^\d\.]+','', chname)
                if chnum:
                    chname  = re.compile('[^a-zA-Z]').sub('', chname)
                    chname  = '%s| %s'%(chnum,chname)
                    label   = '%s : [B] %s[/B]'%(chname, label)
                else: label = chname
            elif opt == 'Lineup':
                if now >= starttime and now < endtime: 
                    label = '%s - [B]%s[/B]'%(starttime.strftime('%I:%M %p').lstrip('0'),label)
                else: 
                    label = '%s - %s'%(starttime.strftime('%I:%M %p').lstrip('0'),label)
                    
            thumb      = (listing.get('preferredImage','') or chlogo)  
            infoLabels = {"mediatype":type,"label":label,"title":label,'duration':duration,'plot':plot,'genre':listing.get('genres',[]),"aired":aired.strftime('%Y-%m-%d')}
            infoArt    = {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":chlogo,"logo":chlogo}
            infoVideo  = False #todo added more meta from listings, ie mpaa, isNew, video/audio codec
            infoAudio  = False #todo added more meta from listings, ie mpaa, isNew, video/audio codec
            if type == 'episode':
                infoLabels['tvshowtitle'] = listing.get('title',label)
                if listing.get('seasonNumber',None):
                    infoLabels['season']  = listing.get('seasonNumber',0)
                    infoLabels['episode'] = listing.get('episodeNumber',0)
                    seaep = '%sx%s'%(str(listing.get('seasonNumber','')).zfill(2),str(listing.get('episodeNumber','')).zfill(2))
                    label = '%s - %s %s'%(label,seaep,listing.get('episodeTitle',''))
                else: label = '%s %s'%(label,listing.get('episodeTitle',''))
                infoLabels['title'] = label
                infoLabels['label'] = label
            if opt == 'Live':
                if now >= starttime and now < endtime: return self.addLink(label, path, 9, infoLabels, infoArt, infoVideo, infoAudio, total=len(listings))
                else: continue
            self.addLink(label, path, 9, infoLabels, infoArt, infoVideo, infoAudio, total=len(listings))

  
    def uEPG(self):
        log('uEPG')
        stations = self.getEPG(self.getRegion())
        return urllib.parse.quote(json.dumps(list(self.poolList(self.buildStation, stations))))


    def buildStation(self, station):
        log('buildStation')
        chname     = (station.get('affiliateName','') or station.get('affiliate','') or station.get('callSign','') or station.get('name',''))
        chnum      = station['id']
        link       = str(chnum)
        chlogo     = (station.get('logoUrl','') or station.get('logo226Url','') or ICON)
        isFavorite = False
        guidedata  = []
        newChannel = {}
        newChannel['channelname']   = chname
        newChannel['channelnumber'] = chnum
        newChannel['channellogo']   = chlogo
        newChannel['isfavorite']    = isFavorite
        listings = station['listings']
        for listing in listings:
            try:    type = {'Series':'episode'}[listing.get('showType','Series')]
            except: type = 'video'
            label = listing['title']
            plot  = (listing.get('description','') or label)
            try:    aired = datetime.datetime.fromtimestamp(int(str(listing['airdate'])[:-3]))
            except: aired = self.now
            duration  = listing.get('duration',0)
            tmpdata   = {"mediatype":type,"label":label,"title":label,'duration':duration,'plot':plot,'genre':listing.get('genres',[]),"aired":aired.strftime('%Y-%m-%d')}
            starttime = datetime.datetime.fromtimestamp(int(str(listing['startTime'])[:-3]))
            endtime   = starttime + datetime.timedelta(seconds=duration)
            if endtime < self.now: continue
            tmpdata['starttime'] = time.mktime((starttime).timetuple())
            tmpdata['url'] = self.sysARG[0]+'?mode=9&name=%s&url=%s'%(chname,link)
            tmpdata['art'] = {"thumb":chlogo,"poster":chlogo,"fanart":FANART,"icon":chlogo,"logo":chlogo}
            guidedata.append(tmpdata)
        newChannel['guidedata'] = guidedata
        return newChannel
        
        
    def poolList(self, method, items):
        results = []
        if ENABLE_POOL:
            pool = ThreadPool(cpu_count())
            results = pool.imap_unordered(method, items, chunksize=25)
            pool.close()
            pool.join()
        else: results = [method(item) for item in items]
        results = filter(None, results)
        return results
        
        
    def resolveURL(self, id):
        log("resolveURL, id = %s"%(id))
        '''{u'dma': 501, u'streamUrl': u'https://acdn.locastnet.org/variant/E27GYubZwfUs.m3u8', u'name': u'WNBCDT2', u'sequence': 50, u'stationId': u'44936', u'callSign': u'4.2 COZITV', u'logo226Url': u'https://fans.tmsimg.com/assets/s78851_h3_aa.png', u'logoUrl': u'https://fans.tmsimg.com/assets/s78851_h3_aa.png', u'active': True, u'id': 1574529688491L}''' 
        return self.getURL(BASE_API + '/watch/station/%s/%s/%s'%(id, self.lat, self.lon), header=self.buildHeader())

        
    def playLive(self, name, url):
        log("playLive %s"%(self.sysARG[1]))     
        self.liz_url = self.resolveURL(int(url))['streamUrl']+'?id='+url
        log('playLive url=%s'%(self.liz_url))
        liz  = xbmcgui.ListItem(name, path=self.liz_url)
        if 'm3u8' in url.lower() and inputstreamhelper.Helper('hls').check_inputstream() and not DEBUG:
            liz.setProperty('inputstreamaddon','inputstream.adaptive')
            liz.setProperty('inputstream.adaptive.manifest_type','hls')
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)
    
           
    def addLink(self, name, u, mode, infoList=False, infoArt=False, infoVideo=False, infoAudio=False, total=0):
        name = name.encode("utf-8")
        log('addLink, name = %s'%name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'True')
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
        else: liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False: liz.setArt({'thumb':ICON,'fanart':FANART})
        else: liz.setArt(infoArt)
        if infoVideo is not False: liz.addStreamInfo('video', infoVideo)
        if infoAudio is not False: liz.addStreamInfo('audio', infoAudio)
        u=self.sysARG[0]+"?url="+urllib.parse.quote(u)+"&mode="+str(mode)+"&name="+urllib.parse.quote(name)
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,totalItems=total)



    def addDir(self, name, u, mode, infoList=False, infoArt=False):
        name = name.encode("utf-8")
        log('addDir, name = %s'%name)
        liz=xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable', 'False')
        if infoList == False: liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
        else: liz.setInfo(type="Video", infoLabels=infoList)
        if infoArt == False: liz.setArt({'thumb':ICON,'fanart':FANART})
        else: liz.setArt(infoArt)
        u=self.sysARG[0]+"?url="+urllib.parse.quote(u)+"&mode="+str(mode)+"&name="+urllib.parse.quote(name)
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,isFolder=True)
     

    def getParams(self):
        return dict(urllib.parse.parse_qsl(self.sysARG[2][1:]))

            
    def run(self):  
        params=self.getParams()
        try: url=urllib.parse.unquote(params["url"])
        except: url=None
        try: name=urllib.parse.unquote(params["name"])
        except: name=None
        try: mode=int(params["mode"])
        except: mode=None
        log("Mode: %s"%(mode))
        log("URL : %s"%(url))
        log("Name: %s"%(name))

        if mode==None:  self.buildMenu(self.getRegion())
        elif mode == 1: self.getStations(name, url)
        elif mode == 3: self.getStations(name, url, 'Live')
        elif mode == 4: self.getStations(name, url, 'Lineups')
        elif mode == 5: self.getStations(name, url, 'Lineup')
        elif mode == 20: xbmc.executebuiltin("RunScript(script.module.uepg,json=%s&refresh_path=%s&refresh_interval=%s)"%(self.uEPG(),urllib.parse.quote(self.sysARG[0]+"?mode=20"),"7200"))

        elif mode == 9: 
            self.playLive(name, url)
            isPremiumUser = toBool(REAL_SETTINGS.getSetting('User_Donate'))
            if not isPremiumUser:
                log('Free Player Created, name=%s id=%s'%(name,url))
                self.player = MyPlayer()
                self.player.setID(int(url))
                self._event = SCHEDULER.enter(FREEREFRESH,1, self.refreshStream, (name, int(url),))
                t = threading.Thread( target = SCHEDULER.run )
                t.start()

                while(not xbmc.abortRequested and not self.player.isStopped()):
                    xbmc.sleep(1000)

                for event in SCHEDULER.queue:
                    SCHEDULER.cancel(event)
                log('Free Player Terminated, name=%s id=%s'%(name,url))

        xbmcplugin.setContent(int(self.sysARG[1])    , CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), cacheToDisc=self.cacheToDisc)
        
        
    def refreshStream(self, name, id):
        if self.player.isPlaying():
            try:
                # is it playing the same channel?
                current_id = int(urllib.parse.parse_qs(urllib.parse.urlparse(self.player.getPlayingFile()).query)['id'][0])
                if current_id == id:
                    log('Refreshing Stream, name=%s id=%s'%(name,id))
                    lizUrl = self.resolveURL(int(id))['streamUrl']+'?id='+id
                    lizListItem  = xbmcgui.ListItem(name)
                    lizListItem.setProperty('IsPlayable', 'True')
                    lizListItem.setInfo(type="Video", infoLabels={"mediatype":"video","title":name})
                    lizListItem.setArt({'thumb':ICON,'fanart':FANART})
                    self.player.play(lizUrl, lizListItem)
                    self._event = SCHEDULER.enter(FREEREFRESH,1, self.refreshStream, (name, id,))
            except KeyError:
                # playing a different url, stop refreshing
                pass
 
 
 
        
class MyPlayer(xbmc.Player):
    def __init__(self):
        self._isStopped = False
        self._id = 0
        xbmc.Player.__init__(self)
        
    def onPlayBackEnded(self):
        log('onPlayBackEnded')

    def onPlayBackStarted(self):
        log('onPlayBackStarted, id=%s'%(self._id))
        # if playback is NOT this stream, then stop this thread
        try:
            current_id = int(urllib.parse.parse_qs(urllib.parse.urlparse(self.getPlayingFile()).query)['id'][0])
            if current_id != self._id:
                self._isStopped = True
        except KeyError:
            # playing a different url, stop refreshing
            self._isStopped = True
            
    
    def onPlayBackStopped(self):
        self._isStopped = True
        log('onPlayBackStopped, id=%s'%(self._id))

    def getID(self):
        return self._id

        
    def setID(self, id):
        log('Player setID, id=%s'%(self._id))
        self._id = id

    def isStopped(self):
        return self._isStopped
    
    
    
