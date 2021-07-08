#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of Media Maintenance.
#
# Media Maintenance is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Media Maintenance is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Media Maintenance.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, re, traceback, json, collections, requests, schedule, subprocess

from six.moves   import urllib
from contextlib  import contextmanager
from simplecache import SimpleCache, use_cache
from itertools   import repeat, cycle, chain, zip_longest
from kodi_six    import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode
from functools   import partial, wraps

try:
    CORES = 2
    USING_THREAD = (CORES == 1 or xbmc.getCondVisibility('System.Platform.Windows')) #multiprocessing takes foreground focus from windows, bug in python?
    if USING_THREAD:    from multiprocessing.dummy import Pool as ThreadPool
    else:               from multiprocessing.pool  import ThreadPool
except Exception as e:
    USING_THREAD = True
    from _threadpool import ThreadPool

# Plugin Info
ADDON_ID       = 'script.media.maintenance'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

# Globals
NOTIFY         = True
DEBUG          = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
DUPMATCH       = int(REAL_SETTINGS.getSetting('Duplicate_Match'))
SONARR_URL     = '%s/api/series?apikey=%s'%(REAL_SETTINGS.getSetting('Sonarr_IP'),REAL_SETTINGS.getSetting('Sonarr_API'))
RADARR_URL     = '%s/api/movie?apikey=%s'%(REAL_SETTINGS.getSetting('Radarr_IP'),REAL_SETTINGS.getSetting('Radarr_API'))
JSON_TV_ENUMS  = '["title", "genre", "year", "rating", "playcount", "episode", "file", "season", "watchedepisodes", "art", "uniqueid"]'
JSON_MV_ENUMS  = '["title", "genre", "year", "rating", "playcount", "streamdetails", "file", "art", "uniqueid"]'

@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try: yield
    finally: xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def log(msg, level=xbmc.LOGDEBUG):
    if not DEBUG and level != xbmc.LOGERROR: return
    if   level == xbmc.LOGERROR: msg = '%s, %s'%((msg),traceback.format_exc())
    try: xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    except Exception as e: 'log failed! %s'%(e)

def dumpJSON(dict1, idnt=None, sortkey=True):
    if not dict1 or isinstance(dict1,str): return dict1
    elif isinstance(dict1, str): return dict1
    return (json.dumps(dict1, indent=idnt, sort_keys=sortkey))
    
def loadJSON(string1):
    if not string1: return []
    elif isinstance(string1,dict): return string1
    elif isinstance(string1,str): 
        string1 = (string1.strip('\n').strip('\t').strip('\r'))
        try: return json.loads(string1, strict=False)
        except Exception as e: log("loadJSON failed! %s \n %s"%(e,string1), xbmc.LOGERROR)
    return {}
           
def sendJSON(command, cache=False):
    response = loadJSON(xbmc.executeJSONRPC(command))
    log('sendJSON, command = %s, response = %s'%(command, response))
    return response
    
def findItemIDX(list1, list2):
    return [idx for idx, lst1 in enumerate(list1) for lst2 in list2 if lst1.getLabel() == lst2['label']]
   
def notificationDialog(message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
    try:    xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
    except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
    return True

def selectDialog(list, header=ADDON_NAME, autoclose=0, preselect=None, multi=True, useDetails=True):
    if preselect is None: preselect = {True:[],False:-1}[multi]
    if multi: return xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
    else: return xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
        
def progressDialogBG(percent=0, control=None, message='', header=ADDON_NAME):
    if control is None and percent == 0:
        control = xbmcgui.DialogProgressBG()
        control.create(header, message)
    elif control:
        if percent == 100 or control.isFinished(): return control.close()
        else: control.update(percent, header, message)
    return control

def yesnoDialog(message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=0):
    try:    
        if customlabel:
            return xbmcgui.Dialog().yesnocustom(heading, message, customlabel, nolabel, yeslabel, autoclose)
        else: raise Exception()
    except: return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, autoclose)
        
def roundupDIV(p, q):
    try:
        d, r = divmod(p, q)
        if r: d += 1
        return d
    except ZeroDivisionError: 
        return 1
    
class MM(object):
    def __init__(self, cache=None):
        if cache is None:
            self.cache = SimpleCache()
        else:
            self.cache = cache
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def cacheJSON(self, command, life=datetime.timedelta(minutes=15)):
        cacheName = '%s.cacheJSON.%s'%(ADDON_ID,command)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            cacheResponse = dumpJSON(sendJSON(command))
            self.cache.set(cacheName, cacheResponse, checksum=len(cacheResponse), expiration=life)
        return loadJSON(cacheResponse)
        
        
    def openURL(self, url, life=datetime.timedelta(minutes=15)):
        try:
            self.log('openURL, url = %s'%(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                cacheresponse = requests.get(url).json()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, dumpJSON(cacheresponse), expiration=life)
                return cacheresponse
            return loadJSON(cacheresponse)
        except Exception as e:
            self.log("openURL Failed! %s"%(e), xbmc.LOGERROR)
            notificationDialog(LANGUAGE(30001))
            return {}
        
           
    def getUserList(self, type='series'):
        setSetting1 = {'series':'TVShowList','movie':'MoviesList'}[type]
        try:    return loadJSON(REAL_SETTINGS.getSetting(setSetting1))
        except: return []
        
        
    def setUserList(self, userList, type='series'):
        log('setUserList, UserList = %s, type = %s'%(userList,type))
        dataSet = {'series':{'setSetting0':'ScanSonarr', 'setSetting1':'TVShowList', 'setSetting2':'ViewTVShows'},
                   'movie' :{'setSetting0':'ScanRadarr', 'setSetting1':'MoviesList', 'setSetting2':'ViewMovies'}}[type]
        
        if len(userList) > 0: 
            userList = [dict(t) for t in {tuple(d.items()) for d in userList}]
            msg = LANGUAGE(30010)%(len(userList),'s' if len(userList) > 1 else '')
            REAL_SETTINGS.setSetting(dataSet['setSetting1'],dumpJSON(userList))
            REAL_SETTINGS.setSetting(dataSet['setSetting2'],msg)
        else:
            msg = ''
            notificationDialog(LANGUAGE(30017))
            REAL_SETTINGS.setSetting(dataSet['setSetting0'],'')
            REAL_SETTINGS.setSetting(dataSet['setSetting1'],'')
            REAL_SETTINGS.setSetting(dataSet['setSetting2'],'')
        return True
        

    def buildListitems(self, items, type='series'): #todo move from selectdialog to window UI and control panel
        mediaLST = list(self.poolList(self.buildListitem, items, type))
        log("buildListitems, found %s"%(len(mediaLST)))
        return mediaLST
        
        
    def buildListitem(self, data):
        item, type = data
        path = item['file']
        if item.get('year',0) > 0: label = '%s (%d)'%(item['label'],item['year'])
        else: label = item['label']
        label2 = path
        id     = {'type':type,'label':label,'title':item['title'],'year':item['year']} 
        for k,v in item.get('uniqueid',{}).items(): id[k] = str(v)  
        if type != 'series':
            id['dbid'] = item['movieid']
            video = item['streamdetails']['video']
            audio = item['streamdetails']['audio']
            if path.startswith('stack://'): label = ' %s [[B]STACK[/B]]'%label
            if len(video) > 0: label = '%s - Video [Codec: [B]%s[/B]|Height: [B]%s[/B]|Runtime: [B]%s[/B]]'%(label,video[0]['codec'].upper(),video[0]['height'],video[0]['duration'])
            if len(audio) > 0: label = '%s - Audio [Codec: [B]%s[/B]|Channels: [B]%s[/B]|Language: [B]%s[/B]]'%(label,audio[0]['codec'].upper(),audio[0]['channels'],audio[0]['language'].title())
        else: id['dbid'] = item['tvshowid']
        thumb = (item['art'].get('poster','') or item.get('thumbnail','') or ICON)
        art = {"thumb":thumb,"poster":thumb,"fanart":FANART,"icon":ICON,"logo":ICON}
        return self.getListitem(label, label2, path=path, infoArt=art, infoProp=id)
        
        
    def viewTVShows(self):
        with busy_dialog():
            TVShowList = self.buildListitems(self.getTVShows())
            TVShowList.insert(0, self.getListitem(LANGUAGE(30044),LANGUAGE(30045))) #Select All
            TVShowList.insert(1, self.getListitem(LANGUAGE(30048),LANGUAGE(30049))) #Unselect All
        select = selectDialog(TVShowList, LANGUAGE(30037), preselect=findItemIDX(TVShowList,self.getUserList()))
        if select is None or len(select) == 0: return
        elif 0 in select: self.setUserList([loadJSON(TVShowList[idx].getProperty('id')) for idx in range(2,len(TVShowList))])
        elif 1 in select: self.setUserList([])
        else: self.setUserList([loadJSON(TVShowList[idx].getProperty('id')) for idx in select])
        return


    def getMonitored(self, mtype='series'):
        self.log('getMonitored, type = %s'%type)
        dataSet = {'series':{'setSetting':'ScanSonarr', 'mediaList':self.getTVShows, 'url':SONARR_URL},
                   'movie' :{'setSetting':'ScanRadarr', 'mediaList':self.getMovies , 'url':RADARR_URL}}[mtype]
        with busy_dialog():
            results = self.openURL(dataSet['url'])
            if not results: return
            userList = self.getUserList(mtype)
            userList.extend(self.poolList(self.findMonitored, results, (mtype, dataSet, userList)))
        self.setUserList(userList, mtype)
        REAL_SETTINGS.setSetting(dataSet['setSetting'],LANGUAGE(30011)%(datetime.datetime.now().strftime('%Y-%m-%d')))
        return
            
        
    def findMonitored(self, data):
        item, meta = data
        type, dataSet, userList = meta
        if not item["monitored"]: return None
        mediaList = dataSet['mediaList']()
        for kodiItem in mediaList:
            conditions = [item["title"] == kodiItem["title"] and item["year"] == kodiItem["year"],
                          item[{"series":"tvdbId"}[type]] == kodiItem.get("uniqueid",{}).get({"series":"tvdb","movie":"tmdb"}[type],0),
                          kodiItem.get('year',0) == 0 and item["title"] == kodiItem["title"]]
            if True in conditions:
                if kodiItem.get('year',0) > 0: label = '%s (%d)'%(kodiItem['title'],kodiItem['year'])
                else: label = kodiItem['title']
                id = {'type':type,'label':label,'title':kodiItem['title'],'year':kodiItem['year'],'dbid':kodiItem['tvshowid']} 
                if id not in userList: return id
        return None
            
            
    def scanDuplicates(self):
        dupLST = []
        delLST = []
        with busy_dialog(): 
            MoviesList = self.getMovies(cache=False)
            
        if len(MoviesList) > 0:
            busy = progressDialogBG(0, message=LANGUAGE(30050))
            duplicates = [item for item, count in collections.Counter([{0:'%s (%d)'%(movie['label'],movie['year']),1:movie['label']}[DUPMATCH] for movie in MoviesList]).items() if count > 1]
            for idx, item in enumerate(duplicates):
                updateDialogProgress = (idx) * 100 // len(duplicates)
                busy = progressDialogBG(updateDialogProgress, busy)
                for movie in MoviesList:
                    title = {0:'%s (%d)'%(movie['label'],movie['year']),1:movie['label']}[DUPMATCH]
                    if item.lower() == title.lower(): dupLST.append(movie)

        if len(dupLST) > 0:
            dupLST.sort(key=lambda x:x['label'])
            listitem = self.buildListitems(dupLST,type='movie')
        else: return notificationDialog(LANGUAGE(30033))
        busy = progressDialogBG(100, busy)
        selects = selectDialog(listitem,LANGUAGE(30036))
        if selects:
            busy = progressDialogBG(0, message=LANGUAGE(30040))
            delLST = [self.requestFile(listitem[select].getLabel2()) for select in selects if not listitem[select].getLabel2().startswith('stack://')]
            # delLST = [self.requestFile(dupLST[item].getLabel2()) for item in items]
            for idx, movie in enumerate(delLST):
                updateDialogProgress = (idx+1) * 100 // len(delLST)
                busy = progressDialogBG(updateDialogProgress, busy)
                self.removeContent(movie)
        
        
    def chkSeason(self, playingItem):
        log('chkSeason')
        notificationDialog('Coming Soon')
        
        
    def removeSeason(self, playingItem):
        log('removeSeason')
        print(json.dumps(playingItem))
        type = playingItem["type"]
        dbid = playingItem["id"]
        if type == 'tvshow': seasons = self.getSeasons(dbid)
        paths = self.getDirectory(playingItem["folder"])['files']
        print(paths, seasons)
        for season in seasons:
            for path in paths:
                print(path['filetype'], season['label'].lower(), path['label'].lower(),path["file"])
                print(re.match('(?:s|season)\W?(\d{1,2})', season['label'].lower(), re.I | re.M).group())
                # if path['filetype'] == 'directory' and season['label'].lower() == path['label'].lower(): print self.getDirectory(path["file"])

            # self.removeLibrary(type, epid)
        # if type == 'tvshow': self.removeLibrary(type, dbid)
        
        #todo check "watch" flag counts
        #fetch tvshowid from seasonid, check season episode total to sonarr, if playcount > 0 on all remove.
        # {"jsonrpc":"2.0","method":"VideoLibrary.GetSeasonDetails","params":{"seasonid":2075,"properties":["episode","tvshowid"]},"id":6}
    
    
    def getDirectory(self, path):
        log('getDirectory')
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"video","properties":["season","episode"]},"id":1}'%(path))
        json_response = self.cacheJSON(json_query)
        if 'result' not in json_response: return {}
        return json_response['result']
    
    
    def getSeasons(self, id):
        log('getSeasons, id = %s'%id)
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetSeasons","params":{"tvshowid":%s},"id":1}'%(id))
        json_response = self.cacheJSON(json_query)
        if 'result' not in json_response: return {}
        return json_response['result'].get('seasons',{})
    

    def splitStack(self, file):
        path = file.replace(',,',',').split(' , ')
        return '|'.join(path).replace('stack://','').split(', media = video')[0].split('|')


    def removeContent(self, playingItem, silent=False, bypass=False):
        #todo parse kodis watched % value then set to settings.xml
        #todo if trakt installed mark watched b4 delete
        #todo mark watched in kodi b4 delete.
        #todo allow option to ignore tvshow delete if watch flag count > 1.
        #todo add "select all" option in tvshow monitor list. or move option to settings bypassing monitor list
        print(playingItem)
        try:
            type = playingItem["type"]
            dbid = playingItem["id"]
            log("removeContent, type = " + type + ", dbid = " + str(dbid))
            file = playingItem.get("file","")
            mediaInfo = playingItem["label"]
            if file.startswith('pvr://recordings/'):
                if REAL_SETTINGS.getSetting('Monitor_Recordings') == 'false': return
            elif type == 'movie':
                if REAL_SETTINGS.getSetting('Monitor_Movies') == 'false': return
            elif type in ['season','tvshow']: return self.removeSeason(playingItem)
            elif type == 'episode':
                tvshow   = playingItem["showtitle"]
                userList = self.getUserList()
                if tvshow not in userList and not bypass: return
                mediaInfo = '%s - %sx%s - %s'%(tvshow,playingItem["season"],playingItem["episode"],mediaInfo)
            else: return notificationDialog(LANGUAGE('NA'))
            if silent == False:
                if not yesnoDialog('%s/n%s'%(mediaInfo, file), heading='%s - %s'%(ADDON_NAME,LANGUAGE(30021)%(type)), yeslabel='Remove', nolabel='Keep', autoclose=15000): return
            
            if not file.startswith('pvr://recordings/'): 
                if self.removeLibrary(type, dbid):
                    notificationDialog(LANGUAGE(30023)%mediaInfo)

            ##DANGER ZONE##
            if REAL_SETTINGS.getSetting('Enable_Removal') == 'true':
                if self.deleteFile(file): 
                    notificationDialog(LANGUAGE(30051)%mediaInfo)
                else: 
                    notificationDialog(LANGUAGE(30022))
            ### TEMP####
            else: #todo clean nfos if not removing media
                file = os.path.join(os.path.dirname(file),'movie.nfo')
                if self.deleteFile(file): 
                    notificationDialog(LANGUAGE(30051)%mediaInfo)
                else: 
                    notificationDialog(LANGUAGE(30022))
                
            ###############
        except Exception as e:
            log("removeContent Failed! %s"%(e), xbmc.LOGERROR)
            log('removeContent, playingItem = %s'%(playingItem))
        
        
    def deleteFile(self, file):
        log("deleteFile")
        for i in range(3):
            try: 
                if xbmcvfs.delete(file): return True
            except: pass
            if self.myMonitor.waitForAbort(1): break
        if xbmcvfs.exists(file): return False
        return True
        
        
    def removeLibrary(self, type, id):
        log("removeLibrary, type = %s, id = %s"%(type,id))
        param  = {'episode':'episodeid','movie':'movieid','movie':'movieid','tvshow':'tvshowid','season':'seasonid','channel':''}[type]
        method = {'episodeid':'RemoveEpisode','movieid':'RemoveMovie','tvshowid':'RemoveTVShow','seasonid':''}[param]
        json_query = '{"jsonrpc":"2.0","method":"VideoLibrary.%s","params":{"%s":%s},"id":1}'%(method, param, str(id))
        return sendJSON(json_query)
        
        
    def cleanLibrary(self, type="video"):
        type = {'video':'video','episode':'tvshows','movie':'movies'}[type]
        json_query = '{"jsonrpc":"2.0","method":"VideoLibrary.Clean","params":{"showdialogs":false,"content":"5s"},"id":1}'%type
        return sendJSON(json_query)
        

    def getActivePlayer(self, return_item=False):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
        json_response = sendJSON(json_query)
        try:    id = json_response.get('result',[{'playerid':1}])[0].get('playerid',1)
        except: id = 1
        self.log("getActivePlayer, id = %s" % (id))
        if return_item: return item
        return id


    def getPlayerItem(self, playlist=False):
        self.log('getPlayerItem, playlist = %s' % (playlist))
        if playlist: json_query = '{"jsonrpc":"2.0","method":"Playlist.GetItems","params":{"playlistid":%s,"properties":["runtime","title","plot","genre","year","studio","mpaa","season","episode","showtitle","thumbnail","uniqueid","file","customproperties"]},"id":1}'%(self.getActivePlaylist())
        else:        json_query = '{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%s,"properties":["file","writer","channel","channels","channeltype","mediapath","uniqueid","customproperties"]}, "id": 1}'%(self.getActivePlayer())
        result = self.cacheJSON(json_query).get('result', {})
        return (result.get('item', {}) or result.get('items', []))


    def requestFile(self, file, media='video', fallback={}):
        log("requestFile, file = " + file + ", media = " + media) 
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"%s","properties":%s},"id":1}' % (self.escapeDirJSON(file), media, self.getEnums(id="List.Fields.Files", type='items')))
        json_response = self.cacheJSON(json_query)
        if 'result' not in json_response: return fallback
        return json_response['result'].get('filedetails',fallback)
        
        
    def escapeDirJSON(self, mydir):
        if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
        return mydir
        
        
    def getEnums(self, id, type=''):
        self.log('getEnums id = %s, type = %s' % (id, type))
        json_query = ('{"jsonrpc":"2.0","method":"JSONRPC.Introspect","params": {"getmetadata": true, "filterbytransport": true,"filter": {"getreferences": false, "id":"%s","type":"type"}},"id":1}'%(id))
        json_response = self.cacheJSON(json_query).get('result',{}).get('types',{}).get(id,{})
        return (json_response.get(type,{}).get('enums',[]) or json_response.get('enums',[]))


    def getTVShows(self, cache=True):
        if not self.hasTV(): return []
        json_query    = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"properties":%s}, "id": 1}'%(JSON_TV_ENUMS))
        if cache: json_response = self.cacheJSON(json_query)
        else: json_response = sendJSON(json_query)
        if not 'result' in json_response: return []
        return sorted(filter(lambda k:k['label'] != '', json_response['result'].get('tvshows',[])), key=lambda x:x['label'])
        
        
    def getMovies(self, cache=True):
        if not self.hasMovie(): return []
        json_query    = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":%s}, "id": 1}'%(JSON_MV_ENUMS))
        if cache: json_response = self.cacheJSON(json_query)
        else: json_response = sendJSON(json_query)
        if not 'result' in json_response: return []
        return sorted(filter(lambda k:k['label'] != '', json_response['result'].get('movies',[])), key=lambda x:x['label']) 
        

    def hasMovie(self):
        return (xbmc.getCondVisibility('Library.HasContent(Movies)'))
        
        
    def hasTV(self):
        return (xbmc.getCondVisibility('Library.HasContent(TVShows)'))


    def getListitem(self, label="", label2="", path="", infoList=None, infoArt=None, infoProp=None, offscreen=False):
        liz = xbmcgui.ListItem(label, label2, path, offscreen)
        if not infoList is None: liz.setInfo(type='video', infoLabels=infoList)
        else: liz.setInfo(type='video', infoLabels={"mediatype":'video',"label":label,"title":label})
        if not infoArt  is None: liz.setArt(infoArt)
        else: liz.setArt({"thumb":ICON,"poster":ICON,"fanart":FANART,"icon":ICON,"logo":ICON})
        if not infoProp is None: liz.setProperty('id', dumpJSON(infoProp))
        # if not infoProp is None: [liz.setProperty(key, str(pvalue)) for key, pvalue in infoProp.items()]
        return liz


    def buildMenu(self):
        items  = [LANGUAGE(30002),LANGUAGE(30034),LANGUAGE(30035)]
        {None:sys.exit,
        -1:sys.exit,
         0:self.viewTVShows,
         1:self.scanDuplicates,
         2:REAL_SETTINGS.openSettings}[selectDialog(items,multi=False,useDetails=False)]()
        return self.buildMenu()
        
   
    def poolList(self, func, items=[], args=None, kwargs=None, chunksize=None):
        results = []
        if len(items) == 0: return results
        try:
            if chunksize is None: chunksize = roundupDIV(len(items), self.cpuCount)
            if len(items) == 0 or chunksize < 1: chunksize = 1 #set min. size
            self.log("poolList, chunksize = %s, items = %s"%(chunksize,len(items)))
            
            pool = ThreadPool(self.cpuCount)
            if kwargs and isinstance(kwargs,dict):
                results = pool.imap(partial(func, **kwargs), items, chunksize)
            else:
                if args: items = zip(items,repeat(args))
                results = pool.imap(func, items, chunksize)
            pool.close()
            pool.join()
        except Exception as e: 
            self.log("poolList, threadPool Failed! %s"%(e), xbmc.LOGERROR)
            results = self.genList(func, items, args, kwargs)
        
        if results: 
            try:    results = list(filter(None, results)) #catch pickle error if/when using processing
            except: results = list(results)
        return results
        
        
    def genList(self, func, items=[], args=None, kwargs=None):
        self.log("genList, %s"%(func.__name__))
        try:
            if kwargs and isinstance(kwargs,dict):
                results = (partial(func, **kwargs)(item) for item in items)
            elif args:
                results = (func((item, args)) for item in items)
            else:
                results = (func(item) for item in items)
            return list(filter(None, results))
        except Exception as e: 
            self.log("genList, Failed! %s"%(e), xbmc.LOGERROR)
            return []


if __name__ == '__main__':
    try: arg = sys.argv[1]
    except: arg = None    
    if arg is None: MM().buildMenu()
    elif arg == '-viewTVShows':  MM().viewTVShows()
    elif arg == '-scanSonarr':   MM().getMonitored()
    elif arg == '-clearTVShows': MM().setUserList([])
    elif arg == '-scanRadarr':   MM().getMonitored('movie')
    elif arg == '-clearMovies':  MM().setUserList([], 'movie')
    REAL_SETTINGS.openSettings()