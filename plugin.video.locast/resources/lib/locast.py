#   Copyright (C) 2021 Lunatixz
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
import os, sys, time, datetime, _strptime, re, routing
import random, string, traceback, tzlocal, pytz
import json, inputstreamhelper, requests

from six.moves                import urllib
from simplecache              import SimpleCache, use_cache
from itertools                import repeat, cycle, chain, zip_longest
from kodi_six                 import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode
from favorites                import *

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
ADDON_ID      = 'plugin.video.locast'
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
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
BASE_URL      = 'https://www.locast.org'
BASE_API      = 'https://api.locastnet.org/api'
GEO_URL       = 'http://ip-api.com/json'
GEO_URL_2     = 'https://api.bigdatacloud.net/data/reverse-geocode-client'
GEO_JSON      = 'https://geocode.xyz/{city},US?json=1'
TZ_API        = 'https://timezonedb.com/ajax.get-time-zone?coordinate={lat}%2C{lon}'
CONTENT_TYPE  = 'episodes'
DISC_CACHE    = False
DTFORMAT      = '%Y-%m-%dT%H:%M:%S' #'YYYY-MM-DDTHH:MM:SS'

@ROUTER.route('/')
def buildMenu():
    Locast().buildMenu()
  
@ROUTER.route('/live/<city>')
def getLive(city):
    Locast().getStations(city,opt='live')
    
@ROUTER.route('/favorites/<city>')
def getLiveFavs(city):
    Locast().getStations(city,opt='favorites')
    
@ROUTER.route('/channels/<city>')
def getChannels(city):
    Locast().getStations(city,opt='channels')

@ROUTER.route('/lineup/<city>/<name>')
def getLineup(city,name):
    Locast().getStations(city,urllib.parse.unquote(name),opt='lineup')

@ROUTER.route('/play/pvr/<id>')
def playChannel(id):
    Locast().playLive(id,opt='pvr')

@ROUTER.route('/play/live/<id>')
def playChannel(id):
    Locast().playLive(id,opt='live')

@ROUTER.route('/iptv/channels')
def iptv_channels():
    """Return JSON-STREAMS formatted data for all live channels"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(ROUTER.args.get('port')[0])
    IPTVManager(port,Locast()).send_channels()

@ROUTER.route('/iptv/epg')
def iptv_epg():
    """Return JSON-EPG formatted data for all live channel EPG data"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(ROUTER.args.get('port')[0])
    IPTVManager(port,Locast()).send_epg()
        
def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg), level)
      
def inputDialog(heading=ADDON_NAME, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    return xbmcgui.Dialog().input(heading, default, key, opt, close)
    
def okDialog(msg, heading=ADDON_NAME):
    return xbmcgui.Dialog().ok(heading, msg)

def okDisable(msg):
    if yesnoDialog(msg, nolabel=LANGUAGE(30009), yeslabel=LANGUAGE(30015)): 
        results = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":false}, "id": 1}'%ADDON_ID)
        if results and "OK" in results: return notificationDialog(LANGUAGE(30016))
    else: sys.exit()
        
def yesnoDialog(message, heading=ADDON_NAME, yeslabel='', nolabel='', autoclose=0):
    return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, autoclose)
    
def notificationDialog(message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
    try:    return xbmcgui.Dialog().notification(header, message, icon, time, sound)
    except: return xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))

def getLastDMA():
    return int(REAL_SETTINGS.getSetting('User_LastDMA') or '0')
    
def isPlaylistRandom():
    return xbmc.getInfoLabel('Playlist.Random').lower() == 'on' # Disable auto playlist shuffling if it's on
    
class Locast(object):
    def __init__(self, sysARG=sys.argv, dma=getLastDMA()):
        log('__init__, sysARG = %s'%(sysARG))
        self.sysARG        = sysARG
        self.cache         = SimpleCache()
        self.token         = (REAL_SETTINGS.getSetting('User_Token')  or None)
        
        if not self.login(): 
            sys.exit()
        else:
            self.lat, self.lon, self.zone, self.dma, self.now = self.getRegion()
            
        if self.dma != getLastDMA(): 
            REAL_SETTINGS.setSetting('User_LastDMA',str(self.dma))
        

    def reset(self):
        self.__init__()
        
           
    def buildMenu(self):
        MAIN_MENU = [(LANGUAGE(30003),(getLive    ,self.dma)),
                     (LANGUAGE(49011),(getLiveFavs,self.dma)),
                     (LANGUAGE(30004),(getChannels,self.dma))]
        for item in MAIN_MENU: self.addDir(*item)
            

    def getStations(self, city, name='', opt=''):
        log("getStations, city = %s, opt = %s, name = %s"%(city,opt,name))
        stations = self.getEPG(city)
        if not isinstance(stations,list):
            return notificationDialog(LANGUAGE(30017))
        for station in stations:
            if station['active'] == False: continue
            path     = str(station['id'])
            thumb    = (station.get('logoUrl','') or station.get('logo226Url','') or ICON)
            listings = station['listings']
            label    = (station.get('affiliateName','') or station.get('affiliate','') or station.get('callSign','') or station.get('name',''))
            stnum    = re.sub('[^\d\.]+','', label)
            stname   = ''
            favorite = None
            if stnum:
                stname    = re.compile('[^a-zA-Z]').sub('', label)
                stlabel   = '%s| %s'%(stnum,stname)
                favorite  = isFavorite(self.dma,stnum)
            else: stlabel = label
            if opt in ['live','favorites']:
                self.buildListings(listings, label, thumb, path, opt)
            elif opt == 'lineup' and (name.lower() == stlabel.lower()):
                self.buildListings(listings, label, thumb, path, opt)
            elif opt == 'play' and (name.lower() == station.get('name','').lower()):
                self.buildListings(listings, label, thumb, path, opt)
            elif opt == 'channels':
                chnum  = re.sub('[^\d\.]+','', label)
                if chnum:
                    chname = re.compile('[^a-zA-Z]').sub('', label)
                    label  = '%s| %s'%(chnum,chname)
                else: label = chname
                self.addDir(label, (getLineup, city,urllib.parse.quote(label)), infoList={"favorite":favorite,"chnum":stnum,"chname":stname,"mediatype":"video","label":label,"title":label}, infoArt={"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON})
            else: continue  


    def getDateTime(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone(self.zone))
        
        
    def buildListings(self, listings, chname, chlogo, path, opt=''):
        log('buildListings, chname = %s, opt = %s'%(chname,opt))
        now = self.now
        listings = sorted(listings, key=lambda k: k['startTime'])
        for listing in listings:
            try: starttime  = self.getDateTime(int(str(listing['startTime'])[:-3]))
            except: continue
            duration   = listing.get('duration',0)
            endtime    = starttime + datetime.timedelta(seconds=duration)
            title      = listing['title']
            favorite   = None
            chnum      = -1            
            # if listing['isNew']: label = '*%s'%label
            try:    aired = self.getDateTime(int(str(listing['airdate'])[:-3]))
            except: aired = starttime
                
            try:    type = {'Series':'episode'}[listing.get('showType','Series')]
            except: type = 'video'
                
            plot = (listing.get('description','') or listing.get('shortDescription','') or xbmc.getLocalizedString(161))
            if now > endtime: continue
                
            chlabel = chname
            chnum   = re.compile('[^\d\.]+').sub('',chname)
            if chnum:
                favorite = isFavorite(self.dma,chnum)
                chname   = re.compile('[^a-zA-Z]').sub('', chname)
                chlabel  = '%s| %s'%(chnum,chname)

            if   opt == 'favorites' and not favorite: continue
            elif opt in ['live','favorites']: 
                label = '%s : [B] %s[/B]'%(chlabel, title)
            elif opt in ['lineup','play']:
                if now >= starttime and now < endtime: 
                    label = '%s - [B]%s[/B]'%(starttime.strftime('%I:%M %p').lstrip('0'),title)
                else: 
                    label = '%s - %s'%(starttime.strftime('%I:%M %p').lstrip('0'),title)
                    path  = 'NEXT_SHOW'
            else: label = chlabel

            thumb      = (listing.get('preferredImage','') or chlogo)  
            infoLabels = {"favorite":favorite,"chnum":chnum,"chname":chname,"mediatype":type,"label":label,"title":label,'duration':duration,'plot':plot,'genre':listing.get('genres',[]),"aired":aired.strftime('%Y-%m-%d')}
            infoArt    = {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":chlogo,"logo":chlogo}
            infoVideo  = {} #todo added more meta from listings, ie mpaa, isNew, video/audio codec
            infoAudio  = {} #todo added more meta from listings, ie mpaa, isNew, video/audio codec    
                               
            if type == 'episode' and opt != 'play':
                infoLabels['tvshowtitle'] = listing.get('title','')
                if listing.get('seasonNumber',None):
                    infoLabels['season']  = listing.get('seasonNumber',0)
                    infoLabels['episode'] = listing.get('episodeNumber',0)
                    seaep = '%sx%s'%(str(listing.get('seasonNumber','')).zfill(2),str(listing.get('episodeNumber','')).zfill(2))
                    label = '%s - %s %s'%(label,seaep,listing.get('episodeTitle',''))
                else: 
                    label = '%s %s'%(label,listing.get('episodeTitle',''))
                infoLabels['title'] = label
                infoLabels['label'] = label
                           
            if opt in ['live','favorites']:
                if now >= starttime and now < endtime:
                    return self.addLink(label, (playChannel,path), infoLabels, infoArt, infoVideo, infoAudio, total=len(listings))
                else: continue
            elif opt == 'play': 
                if starttime <= now and endtime > now: infoLabels['duration'] = ((endtime) - now).seconds
                self.addPlaylist(label, path, infoLabels, infoArt, infoVideo, infoAudio)
            else: 
                self.addLink(label, (playChannel,path), infoLabels, infoArt, infoVideo, infoAudio, total=len(listings))


    @use_cache(1)
    def getREG(self, url):
        log('getREG, url = %s'%(url))
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'})
            return json.load(urllib.request.urlopen(req))
        except Exception as e: 
            log("getREG, %s, Failed! %s"%(url, e), xbmc.LOGERROR)
            return {}
        
        
    @use_cache(28)
    def getGEO(self, url):
        log('getGEO, url = %s'%(url))
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'})
            return json.load(urllib.request.urlopen(req))
        except Exception as e: 
            log("getGEO, %s, Failed! %s"%(url, e), xbmc.LOGERROR)
            return {}
        
        
    @use_cache(28)
    def getTZ(self,url):
        log('getTZ, url = %s'%(url))
        try:
            match = re.compile('Zone Name</td>(.*?)<td>(.*?)\</td>',re.IGNORECASE).search(str(urllib.request.urlopen(url).read()))
            return match.group(2)
        except Exception as e:
            log("getTZ, %s, Failed! %s"%(url, e), xbmc.LOGERROR)
            notificationDialog(LANGUAGE(49014))
            return None


    def getIPGEO(self):
        log('getIPGEO')
        geo_data = {'lat':0.0,'lon':0.0}
        for url in [GEO_URL,GEO_URL_2]:
            response = self.getREG(url)
            if   'lat'      in response: geo_data = {'lat':self.formatGEO(response.get('lat','0.0')),'lon':self.formatGEO(response.get('lon','0.0'))}
            elif 'latitude' in response: geo_data = {'lat':self.formatGEO(response.get('latitude','0.0')),'lon':self.formatGEO(response.get('longitude','0.0'))}
            if geo_data.get('lat') != 0.0: return geo_data
        
                
    def formatGEO(self, loc):
        return float('{0:.7f}'.format(float(loc)))


    def getURL(self, url, param={}, header={'Content-Type':'application/json'}, life=datetime.timedelta(minutes=5)):
        log('getURL, url = %s, header = %s'%(url, header))
        cachename     = '%s.getURL.url.%s.%s.%s'%(ADDON_NAME,url,param,header)
        cacheresponse = self.cache.get(cachename)
        if not cacheresponse:
            try:
                req = requests.get(url, param, headers=header)
                try: cacheresponse = req.json()
                except: return {}
                req.close()
                self.cache.set(cachename, json.dumps(cacheresponse), expiration=life)
                return cacheresponse
            except Exception as e: 
                log("getURL, Failed! %s"%(e), xbmc.LOGERROR)
                notificationDialog(LANGUAGE(30001))
                return {}
        else: return json.loads(cacheresponse)


    def postURL(self, url, param={}, header={'Content-Type':'application/json'}, life=datetime.timedelta(minutes=5)):
        log('postURL, url = %s, header = %s'%(url, header))
        cachename     = '%s.postURL.url.%s.%s.%s'%(ADDON_NAME,url,param,header)
        cacheresponse = self.cache.get(cachename)
        if not cacheresponse:
            try:
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
        header_dict                  = {}
        header_dict['Accept']        = 'application/json, text/javascript, */*; q=0.01'
        header_dict['Content-Type']  = 'application/json'
        header_dict['Connection']    = 'keep-alive'
        header_dict['Origin']        = BASE_URL
        header_dict['Referer']       = BASE_URL
        header_dict['Authorization'] = "Bearer %s" % self.token
        header_dict['User-Agent']    = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'
        return header_dict


    def chkUser(self, user):
        state = False
        try:    self.userdata = self.getURL(BASE_API + '/user/me',header=self.buildHeader())
        except: self.userdata = {}
        if self.userdata.get('email','').lower() == user.lower(): state = True
        log('chkUser = %s'%(state))
        return state


    def login(self):
        log('login')
        user     = REAL_SETTINGS.getSetting('User_Email')
        password = REAL_SETTINGS.getSetting('User_Password')
        
        if len(user) > 0:
            if self.chkUser(user): return True
            data = self.postURL(BASE_API + '/user/login',param='{"username":"' + user + '","password":"' + password + '"}')
            '''{u'token': u''}'''
            if data and 'token' in data: 
                self.token = data['token']
                if REAL_SETTINGS.getSetting('User_Token') != self.token: REAL_SETTINGS.setSetting('User_Token',self.token)
                if self.chkUser(user): 
                    try:
                        REAL_SETTINGS.setSetting('User_Donate',str(self.userdata.get('didDonate','False')))
                        REAL_SETTINGS.setSetting('User_totalDonations',str(self.userdata.get('totalDonations','0')))
                        REAL_SETTINGS.setSetting('User_LastLogin',self.getDateTime(float(str(self.userdata.get('lastlogin','')).rstrip('L'))/1000).strftime("%Y-%m-%d %I:%M %p"))
                        REAL_SETTINGS.setSetting('User_DonateExpire',self.getDateTime(float(str(self.userdata.get('donationExpire','')).rstrip('L'))/1000).strftime("%Y-%m-%d %I:%M %p"))
                    except: pass
                    REAL_SETTINGS.setSetting('User_DMA',str(self.userdata.get('lastDmaUsed','0')))
                    # self.dma = 
                    notificationDialog(LANGUAGE(30021)%(self.userdata.get('name','')))
                    return True
            elif data.get('message'): notificationDialog(data.get('message'))
            else: notificationDialog(LANGUAGE(30017))
        else:
            #firstrun wizard
            if yesnoDialog(LANGUAGE(30008),nolabel=LANGUAGE(30009), yeslabel=LANGUAGE(30010)):
                user     = inputDialog(LANGUAGE(30006))
                password = inputDialog(LANGUAGE(30007),opt=xbmcgui.ALPHANUM_HIDE_INPUT)
                REAL_SETTINGS.setSetting('User_Email'   ,user)
                REAL_SETTINGS.setSetting('User_Password',password)
                xbmc.sleep(2000)#wait for setsetting write
                return self.reset()
            else: okDialog(LANGUAGE(30012))
        return False


    def genClientID(self):
        return  urllib.parse.quote(''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits + '=' + '+') for _ in range(24)))
            
               
    def getEPG(self, city):
        log("getEPG, city = %s"%city)
        '''[{"id":104,"dma":501,"name":"WCBSDT (WCBS-DT)","callSign":"WCBS","logoUrl":"https://fans.tmsimg.com/h5/NowShowing/28711/s28711_h5_aa.png","active":true,"affiliate":"CBS","affiliateName":"CBS",
             "listings":[{"stationId":104,"startTime":1535410800000,"duration":1800,"isNew":true,"audioProperties":"CC, HD 1080i, HDTV, New, Stereo","videoProperties":"CC, HD 1080i, HDTV, New, Stereo","programId":"EP000191906491","title":"Inside Edition","description":"Primary stories and alternative news.","entityType":"Episode","airdate":1535328000000,"genres":"Newsmagazine","showType":"Series"}]}'''
        now = ('{0:.23s}{1:s}'.format(self.now.strftime('%Y-%m-%dT00:00:00'),'-05:00'))
        return self.getURL(BASE_API + '/watch/epg/%s'%(city), param={'start_time':urllib.parse.quote(now)}, header=self.buildHeader(), life=datetime.timedelta(minutes=45))
        
        
    def getAll(self):
        return self.getURL(BASE_API + '/dma',header=self.buildHeader())
              

    def getCity(self, lat, lon):
        log("getCity, lat = %s, lon = %s"%(lat, lon))
        '''{u'active': True, u'DMA': u'501', u'small_url': u'https://s3.us-east-2.amazonaws.com/static.locastnet.org/cities/new-york.jpg', u'large_url': u'https://s3.us-east-2.amazonaws.com/static.locastnet.org/cities/background/new-york.jpg', u'name': u'New York'}'''
        try:
            city = self.getURL(BASE_API + '/watch/dma/%s/%s'%(lat,lon),header=self.buildHeader())
            if city and 'DMA' not in city: 
                REAL_SETTINGS.setSetting('User_DMA','0')
                REAL_SETTINGS.setSetting('User_City','Unknown')
                xbmcgui.Window(10000).setProperty('User_City','Unknown')
                okDisable(city.get('message'))
                return 'Unknown', 0
            else: 
                REAL_SETTINGS.setSetting('User_DMA',str(city['DMA']))
                REAL_SETTINGS.setSetting('User_City',city['name'])
                xbmcgui.Window(10000).setProperty('User_City',str(city['name']))
        except: okDisable(LANGUAGE(30013))


    def getTime(self, zone):
        log("getCity, zone = %s"%(zone))
        return datetime.datetime.now(pytz.timezone(zone))#.astimezone(pytz.utc)


    def getRegion(self):
        log("getRegion")
        try:
            geo_data = self.getIPGEO()
            geo_tz   = tzlocal.get_localzone().zone
            
            self.getCity(geo_data.get('lat'), geo_data.get('lon'))
            geo_city = REAL_SETTINGS.getSetting('User_City')
            geo_dma  = int(REAL_SETTINGS.getSetting('User_DMA'))

            if geo_data.get('lat') == 0.0: 
                okDialog(LANGUAGE(30025)%('%s\n%s'%(GEO_URL,GEO_URL_2)))
                raise Exception(LANGUAGE(30025)%('%s\n%s'%(GEO_URL,GEO_URL_2)))
                
            elif DEBUG and int(REAL_SETTINGS.getSetting('User_Select_DMA') or '0') > 0:
                response = self.getGEO(GEO_JSON.format(city=urllib.parse.quote( REAL_SETTINGS.getSetting('User_Select_City'))))
                reg_data = {'lat':self.formatGEO(response.get('latt','0.0')),'lon':self.formatGEO(response.get('longt','0.0'))}
                if reg_data.get('lat') != 0.0:
                    geo_data = reg_data
                    geo_tz   = self.getTZ(TZ_API.format(lat=geo_data.get('lat'),lon=geo_data.get('lon'))) 
                    geo_city = REAL_SETTINGS.getSetting('User_Select_City')
                    geo_dma  = int(REAL_SETTINGS.getSetting('User_Select_DMA'))
                else: log('setRegion, reg_data = %s error'%(reg_data))
                
            log('setRegion, geo_city = %s, geo_dma = %s, geo_data = %s, geo_tz = %s'%(geo_city,geo_dma,geo_data,geo_tz))
            return geo_data['lat'], geo_data['lon'], geo_tz, geo_dma, self.getTime(geo_tz)
        except Exception as e:
            log("getRegion, Failed! %s"%(e), xbmc.LOGERROR) 
            notificationDialog(LANGUAGE(30001))
            sys.exit()
            

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


    def getChannels(self):
        log('getChannels')
        # https://github.com/add-ons/service.iptv.manager/wiki/JSON-STREAMS-format
        stations = self.getEPG(self.getRegion())
        return list(self.poolList(self.buildStation, stations,'channel'))


    def getGuide(self):
        log('getGuide')
        # https://github.com/add-ons/service.iptv.manager/wiki/JSON-EPG-format
        stations  = self.getEPG(self.getRegion())
        return {k:v for x in self.poolList(self.buildStation, stations,'programmes') for k,v in x.items()}
        

    def buildStation(self, data):
        station, opt = data
        if station['active'] == False: return None
        label    = (station.get('affiliateName','') or station.get('affiliate','') or station.get('callSign','') or station.get('name',''))
        stnum    = re.sub('[^\d\.]+','', label)
        stname   = re.compile('[^a-zA-Z]').sub('', label)
        favorite = isFavorite(self.dma,stnum)
        channel  = {"name"     :stname,
                    "stream"   :"plugin://%s/play/pvr/%s"%(ADDON_ID,station['id']), 
                    "id"       :"%s.%s@%s"%(stnum,slugify(stname),slugify(ADDON_NAME)), 
                    "logo"     :(station.get('logoUrl','') or station.get('logo226Url','') or ICON), 
                    "preset"   :stnum,
                    "group"    :ADDON_NAME,
                    "radio"    :False}#,
                    # "kodiprops":{"inputstream":"inputstream.adaptive",
                                 # "inputstream.adaptive.manifest_type":"hls",
                                 # "inputstream.adaptive.media_renewal_url":"plugin://%s/play/pvr/%s"%(ADDON_ID,station['id']),
                                 # "inputstream.adaptive.media_renewal_time":"900"}}
        if favorite: channel['group'] = ';'.join([LANGUAGE(49012),ADDON_NAME])
        if REAL_SETTINGS.getSettingBool('Build_Favorites') and not favorite: return None
        elif opt == 'channel': return channel
        else:
            programmes = {channel['id']:[]}
            listings   = station.get('listings',[])
            for listing in listings:
                try: starttime  = self.getDateTime(int(str(listing['startTime'])[:-3]))
                except: continue
                try:    aired = self.getDateTime(int(str(listing['airdate'])[:-3]))
                except: aired = starttime
                program = {"start"      :starttime.strftime(DTFORMAT),
                           "stop"       :(starttime + datetime.timedelta(seconds=listing.get('duration',0))).strftime(DTFORMAT),
                           "title"      :listing.get('title',channel['name']),
                           "description":(listing.get('description','') or listing.get('shortDescription','') or xbmc.getLocalizedString(161)),
                           "subtitle"   :listing.get('episodeTitle',''),
                           "genre"      :listing.get('genres',""),
                           "image"      :(listing.get('preferredImage','') or channel['logo']),
                           "date"       :aired.strftime('%Y-%m-%d'),
                           "credits"    :"",
                           "stream"     :""}
                           
                if listing.get('seasonNumber',0) > 0 and listing.get('episodeNumber',0) > 0:
                    program["episode"] = "S%sE%s"%(str(listing.get('seasonNumber',0)).zfill(2),str(listing.get('episodeNumber',0)).zfill(2))
                    
                programmes[channel['id']].append(program)
            return programmes
                       

    def resolveURL(self, id, opt):
        log('resolveURL, id = %s, opt = %s'%(id,opt))  
        self.listitems = []
        self.playlist  = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.playlist.clear()
        '''{u'dma': 501, u'streamUrl': u'https://acdn.locastnet.org/variant/E27GYubZwfUs.m3u8', u'name': u'WNBCDT2', u'sequence': 50, u'stationId': u'44936', u'callSign': u'4.2 COZITV', u'logo226Url': u'https://fans.tmsimg.com/assets/s78851_h3_aa.png', u'logoUrl': u'https://fans.tmsimg.com/assets/s78851_h3_aa.png', u'active': True, u'id': 1574529688491L}''' 
        data = self.getURL(BASE_API + '/watch/station/%s/%s/%s'%(id, self.lat, self.lon), header=self.buildHeader(), life=datetime.timedelta(seconds=5))
        url  = data.get('streamUrl')
        liz  = xbmcgui.ListItem(data.get('name'),path=url)
        liz.setProperty('IsPlayable','true')
        liz.setProperty('IsInternetStream','true')
        if opt != 'pvr':
            self.getStations(data.get('dma'), name=data.get('name'), opt='play')
            [self.playlist.add(url,lz,idx) for idx,lz in enumerate(self.listitems)]
            if isPlaylistRandom(): self.channelPlaylist.unshuffle()
            if isinstance(self.listitems,list): 
                liz = self.listitems.pop(0)
            liz.setPath(path=url)
        return liz
        
        
    def playLive(self, id, opt='live'):
        log('playLive, id = %s, opt = %s'%(id,opt))             
        if id == 'NEXT_SHOW': 
            found = False
            liz   = xbmcgui.ListItem(LANGUAGE(30029))
            notificationDialog(LANGUAGE(30029))
        else:            
            found = True
            liz   = self.resolveURL(id,opt)
            # if opt != 'pvr' and 'm3u8' in liz.getPath().lower() and inputstreamhelper.Helper('hls').check_inputstream():
                # liz.setProperty('inputstream','inputstream.adaptive')
                # liz.setProperty('inputstream.adaptive.manifest_type','hls')
                # liz.setProperty('inputstream.adaptive.media_renewal_url', 'plugin://%s/play/%s/%s'%(ADDON_ID,opt,id))
                # liz.setProperty('inputstream.adaptive.media_renewal_time', '900')
                #todo debug pvr (IPTV Simple) not playing with inputstream! temp. use kodiprops in m3u?
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
        if infoList['favorite']:
            liz.addContextMenuItems([(LANGUAGE(49010), 'RunScript(special://home/addons/%s/favorites.py, %s)'%(ADDON_ID,urllib.parse.quote(json.dumps({"dma":self.dma,"chnum":infoList.pop('chnum'),"chname":infoList.pop('chname'),"mode":"del"}))))])
        else:
            liz.addContextMenuItems([(LANGUAGE(49009), 'RunScript(special://home/addons/%s/favorites.py, %s)'%(ADDON_ID,urllib.parse.quote(json.dumps({"dma":self.dma,"chnum":infoList.pop('chnum'),"chname":infoList.pop('chname'),"mode":"add"}))))])
        return liz
        
        
    def run(self): 
        ROUTER.run()
        xbmcplugin.setContent(ROUTER.handle     ,CONTENT_TYPE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(ROUTER.handle ,cacheToDisc=DISC_CACHE)