#   Copyright (C) 2018 Lunatixz
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
import os, sys, time, datetime, re, traceback
import urlparse, urllib, urllib2, socket, json, collections
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
from simplecache import SimpleCache, use_cache

# Plugin Info
ADDON_ID       = 'script.media.maintenance'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString
DEBUG          = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
DUPMATCH       = int(REAL_SETTINGS.getSetting('Duplicate_Match'))
SONARR_URL     = '%s/api/series?apikey=%s'%(REAL_SETTINGS.getSetting('Sonarr_IP'),REAL_SETTINGS.getSetting('Sonarr_API'))
RADARR_URL     = '%s/api/movie?apikey=%s'%(REAL_SETTINGS.getSetting('Radarr_IP'),REAL_SETTINGS.getSetting('Radarr_API'))
TIMEOUT        = 15
NOTIFY         = True
JSON_TV_ENUMS  = '["title", "genre", "year", "rating", "plot", "studio", "mpaa", "cast", "playcount", "episode", "imdbnumber", "premiered", "votes", "lastplayed", "fanart", "thumbnail", "file", "originaltitle", "sorttitle", "episodeguide", "season", "watchedepisodes", "dateadded", "tag", "art", "userrating", "ratings", "runtime", "uniqueid" ]'
JSON_MV_ENUMS  = '["title", "genre", "year", "rating", "director", "trailer", "tagline", "plot", "plotoutline", "originaltitle", "lastplayed", "playcount", "writer", "studio", "mpaa", "cast", "country", "imdbnumber", "runtime", "set", "showlink", "streamdetails", "top250", "votes", "fanart", "thumbnail", "file", "sorttitle", "resume", "setid", "dateadded", "tag", "art", "userrating", "ratings", "premiered", "uniqueid"]'
JSON_IT_ENUMS  = '["title","artist","albumartist","genre","year","rating","album","track","duration","comment","lyrics","musicbrainztrackid","musicbrainzartistid","musicbrainzalbumid","musicbrainzalbumartistid","playcount","fanart","director","trailer","tagline","plot","plotoutline","originaltitle","lastplayed","writer","studio","mpaa","cast","country","imdbnumber","premiered","productioncode","runtime","set","showlink","streamdetails","top250","votes","firstaired","season","episode","showtitle","thumbnail","file","resume","artistid","albumid","tvshowid","setid","watchedepisodes","disc","tag","art","genreid","displayartist","albumartistid","description","theme","mood","style","albumlabel","sorttitle","episodeguide","uniqueid","dateadded","channel","channeltype","hidden","locked","channelnumber","starttime","endtime","specialsortseason","specialsortepisode","compilation","releasetype","albumreleasetype","contributors","displaycomposer","displayconductor","displayorchestra","displaylyricist","userrating"]'
JSON_FL_ENUMS  = '["title","artist","albumartist","genre","year","rating","album","track","duration","comment","lyrics","musicbrainztrackid","musicbrainzartistid","musicbrainzalbumid","musicbrainzalbumartistid","playcount","fanart","director","trailer","tagline","plot","plotoutline","originaltitle","lastplayed","writer","studio","mpaa","cast","country","imdbnumber","premiered","productioncode","runtime","set","showlink","streamdetails","top250","votes","firstaired","season","episode","showtitle","thumbnail","file","resume","artistid","albumid","tvshowid","setid","watchedepisodes","disc","tag","art","genreid","displayartist","albumartistid","description","theme","mood","style","albumlabel","sorttitle","episodeguide","uniqueid","dateadded","size","lastmodified","mimetype","specialsortseason","specialsortepisode"]'

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def uni(string, encoding = 'utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode): string = unicode(string, encoding, errors='ignore')
        elif isinstance(string, unicode): string = string.encode('ascii', 'replace')
    return string

class MM(object):
    def __init__(self):
        self.cache      = SimpleCache()
        
        
    def sendJSON(self, command, cache=False):
        log('sendJSON, command = ' + str(command))
        cacheresponse = self.cache.get(ADDON_NAME + '.sendJSON, command = %s'%json.dumps(command))
        if DEBUG or not cache: cacheresponse = None
        if not cacheresponse:
            cacheresponse = uni(xbmc.executeJSONRPC(command))
            self.cache.set(ADDON_NAME + '.sendJSON, command = %s'%json.dumps(command), cacheresponse, expiration=datetime.timedelta(hours=12))
        return json.loads(cacheresponse)
    
    
    def openURL(self, url):
        try:
            log('openURL, url = ' + str(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if DEBUG: cacheresponse = None
            if not cacheresponse:
                request = urllib2.Request(url)
                request.add_header('User-Agent','Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)')
                cacheresponse = urllib2.urlopen(request, timeout=TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheresponse, expiration=datetime.timedelta(minutes=15))
            return json.loads(cacheresponse)
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            self.notificationDialog(LANGUAGE(30001))
            return ''
            
            
    def getMonitored(self, type='series'):
        log('getMonitored, type = ' + type)
        if type == 'series': 
            mediaList = self.getTVShows()
            url = SONARR_URL
            setSetting = 'ScanSonarr'
        else: 
            mediaList = self.getMovies()
            url = RADARR_URL
            setSetting = 'ScanRadarr'
        results  = self.openURL(url)
        if not results: return
        userList = self.getUserList(type)
        for idx, item in enumerate(results):
            updateDialogProgress = (idx) * 100 // len(results)
            REAL_SETTINGS.setSetting(setSetting,'Scanning... (%d'%(updateDialogProgress)+'%)')
            match = False
            show  = item["title"]
            for kodititle in userList:
                if kodititle.lower() == show.lower():
                    log('getMonitored, monitor match: show = ' + show + ', kodititle = ' + kodititle)
                    match = True
                    break
            if match: continue
            if item["monitored"]: 
                for title in mediaList:
                    title = title['title']
                    if title.lower() == show.lower(): 
                        log('getMonitored, kodi match: show = ' + show + ', title = ' + title)
                        userList.append(title)
                        break
        if type == 'series': REAL_SETTINGS.setSetting(setSetting,LANGUAGE(30011)%(datetime.datetime.now().strftime('%Y-%m-%d')))
        else: REAL_SETTINGS.setSetting(setSetting,LANGUAGE(30011)%(datetime.datetime.now().strftime('%Y-%m-%d')))
        if len(userList) > 0: self.setUserList(userList, type)
        
           
    def getUserList(self, type='series'):
        REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
        if type == 'series': 
            try: return (REAL_SETTINGS.getSetting('TVShowList').split(':&:') or [])
            except: return []
        else:
            try: return (REAL_SETTINGS.getSetting('MoviesList').split(':&:') or [])
            except: return []
        
        
    def setUserList(self, userList, type='series'):
        msg = ""
        if type == 'series': 
            setSetting0 = 'ScanSonarr'
            setSetting1 = 'TVShowList'
            setSetting2 = 'ViewTVShows'
        else: 
            setSetting0 = 'ScanRadarr'
            setSetting1 = 'MoviesList'
            setSetting2 = 'ViewMovies'
            
        plural = 's' if len(userList) > 1 else '' 
        if len(userList) > 0: 
            msg = LANGUAGE(30010)%(len(userList),plural)
        else: 
            self.notificationDialog(LANGUAGE(30017))
            REAL_SETTINGS.setSetting(setSetting0,'')
        userList = ':&:'.join(list(set(userList)))
        log('setUserList, UserList = ' + userList + ', type = ' + type)
        REAL_SETTINGS.setSetting(setSetting1,userList)
        REAL_SETTINGS.setSetting(setSetting2,msg)
        if len(userList) == 0: REAL_SETTINGS.openSettings()
            
        
        
    def hasMovie(self):
        return bool(xbmc.getCondVisibility('Library.HasContent(Movies)'))
        
        
    def hasTV(self):
        return bool(xbmc.getCondVisibility('Library.HasContent(TVShows)'))

        
    def removeSeason(self, playingItem):
        self.notificationDialog('Coming Soon')
        #todo check "watch" flag counts
        #fetch tvshowid from seasonid, check season episode total to sonarr, if playcount > 0 on all remove.
        # {"jsonrpc":"2.0","method":"VideoLibrary.GetSeasonDetails","params":{"seasonid":2075,"properties":["episode","tvshowid"]},"id":6}
    
    
    def splitStack(self, file):
        path = file.replace(',,',',').split(' , ')
        return '|'.join(path).replace('stack://','').split(', media = video')[0].split('|')


    def removeContent(self, playingItem, silent=False, bypass=False):
        #todo parse kodis watched % value then set to settings.xml
        #todo if trakt installed mark watched b4 delete
        #todo mark watched in kodi b4 delete.
        #todo allow option to ignore tvshow delete if watch flag count > 1.
        #todo add "select all" option in tvshow monitor list. or move option to settings bypassing monitor list
        try:
            type = playingItem["type"]
            dbid = playingItem["id"]
            log("removeContent, type = " + type + ", dbid = " + str(dbid)) 
            param  = {'episode':'episodeid','movie':'movieid','movie':'movieid','tvshow':'tvshowid','season':'seasonid'}[type]
            method = {'episodeid':'RemoveEpisode','movieid':'RemoveMovie','tvshowid':'RemoveTVShow','seasonid':''}[param]
            file = playingItem.get("file","")
            mediaInfo = playingItem["label"]
            if type == 'movie':
                if REAL_SETTINGS.getSetting('Monitor_Movies') == 'false': return
            elif type == 'season': return self.removeSeason(playingItem)
            else:
                tvshow   = playingItem["showtitle"]
                userList = self.getUserList()
                if tvshow not in userList and not bypass: return
                mediaInfo = '%s - %sx%s - %s'%(tvshow,playingItem["season"],playingItem["episode"],mediaInfo)
            if silent == False:
                if not self.yesnoDialog(mediaInfo, file, header='%s - %s'%(ADDON_NAME,LANGUAGE(30021)%(type)), yes='Remove', no='Keep', autoclose=15000): return
            if REAL_SETTINGS.getSetting('Enable_Removal') == 'true':
                json_query = '{"jsonrpc":"2.0","method":"VideoLibrary.%s","params":{"%s":%s},"id":1}'%(method, param, str(dbid))
                self.sendJSON(json_query)
                    # if path.startswith('stack://'):
                        # files = self.splitStack(path)
                        # for file in files: MoviesList.append({'label':label,'label2':file,'thumb':(item['art'].get('poster','') or item['thumbnail'])})
                    # else:
                if self.deleteFile(file):
                    self.notificationDialog(LANGUAGE(30023)%mediaInfo)
                    return
            self.notificationDialog(LANGUAGE(30022))
        except Exception as e:
            log("removeContent Failed! " + str(e), xbmc.LOGERROR)
            log('removeContent, playingItem = ' + json.dumps(playingItem))
        
        
    def deleteFile(self, file):
        log("deleteFile")
        for i in range(3):
            try: 
                if xbmcvfs.delete(file): return True
            except: pass
        if xbmcvfs.exists(file): return False
        return True
        
        
    def cleanLibrary(self, type="video"):
        type = {'video':'video','episode':'tvshows','movie':'movies'}[type]
        json_query = '{"jsonrpc":"2.0","method":"VideoLibrary.Clean","params":{"showdialogs":false,"content":"5s"},"id":1}'%type
        self.sendJSON(json_query)
        
        
    def getActivePlayer(self):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
        json_response = self.sendJSON(json_query)
        try: id = json_response['result'][0]['playerid']
        except: id = 1
        log("getActivePlayer, id = " + str(id)) 
        return id
        
        
    def requestItem(self):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%d,"properties":%s}, "id": 1}'%(self.getActivePlayer(), JSON_IT_ENUMS))
        json_response = self.sendJSON(json_query)
        if 'result' not in json_response: return {}
        return json_response['result'].get('item',{})
        
        
    def requestFile(self, file, media='video', fallback={}):
        log("requestFile, file = " + file + ", media = " + media) 
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"%s","properties":%s},"id":1}' % (self.escapeDirJSON(file), media, JSON_FL_ENUMS))
        json_response = self.sendJSON(json_query)
        if 'result' not in json_response: return fallback
        return json_response['result'].get('filedetails',fallback)
        
        
    def escapeDirJSON(self, mydir):
        if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
        return mydir
        
        
    def getTVShows(self):
        if not self.hasTV(): return []
        busy = self.progressDialogBG(0, string1=LANGUAGE(30038))
        json_query    = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"properties":%s}, "id": 1}'%(JSON_TV_ENUMS))
        json_response = self.sendJSON(json_query,cache=True)
        if not 'result' in json_response: return []
        self.progressDialogBG(100, busy)
        return sorted(json_response['result']['tvshows'], key=lambda x:x['label']) 
        
        
    def getMovies(self):
        if not self.hasMovie(): return []
        busy = self.progressDialogBG(0, string1=LANGUAGE(30039))
        json_query    = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":%s}, "id": 1}'%(JSON_MV_ENUMS))
        json_response = self.sendJSON(json_query)
        self.progressDialogBG(100, busy)
        if not 'result' in json_response: return []
        return sorted(json_response['result']['movies'], key=lambda x:x['label']) 
        
        
    def buildListitem(self, list, TV=False): #todo move to window UI and control panel
        mediaLST = []
        msg = LANGUAGE(30039)
        if TV: msg = LANGUAGE(30038)
        busy = self.progressDialogBG(0, string1=msg)
        for idx, item in enumerate(list):
            try:
                if TV: label = item['label']
                else: label = '%s (%d)'%(item['label'],item['year'])
                path  = item['file']
                updateDialogProgress = (idx) * 100 // len(list)
                busy = self.progressDialogBG(updateDialogProgress, busy, string1=label)
                if not TV:
                    video = item['streamdetails']['video']
                    audio = item['streamdetails']['audio']
                    if path.startswith('stack://'): label = ' %s [[B]STACK[/B]]'%label
                    if len(video) > 0: label = '%s - Video [Codec: [B]%s[/B]|Height: [B]%s[/B]|Runtime: [B]%s[/B]]'%(label,video[0]['codec'].upper(),video[0]['height'],video[0]['duration'])
                    if len(audio) > 0: label = '%s - Audio [Codec: [B]%s[/B]|Channels: [B]%s[/B]|Language: [B]%s[/B]]'%(label,audio[0]['codec'].upper(),audio[0]['channels'],audio[0]['language'].title())
                mediaLST.append(self.getListitem(label, path, (item['art'].get('poster','') or item['thumbnail'])))
            except Exception as e: log("buildListitem Failed! %s , item = %s"%(str(e),item), xbmc.LOGERROR)
        self.progressDialogBG(100, busy)
        log("buildListitem, found "  + str(len(mediaLST)))
        return mediaLST

    
    def viewTVShows(self):
        TVShowList = self.buildListitem(self.getTVShows(),TV=True)
        TVShowList.insert(0, self.getListitem(LANGUAGE(30044),LANGUAGE(30045),ICON, ICON))
        select = self.selectDialog(TVShowList, LANGUAGE(30037), preselect=self.findItemIDX(TVShowList,self.getUserList()))
        if select is None or select < 0: return
        elif 0 in select: self.setUserList([TVShowList[idx].getLabel() for idx in range(1,len(TVShowList))])
        elif select is not None: self.setUserList([TVShowList[idx].getLabel() for idx in select])

        
    def getListitem(self, label1="", label2="", iconImage="", thumbnailImage="", path="", offscreen=False):
        try: return xbmcgui.ListItem(label1, label2, iconImage, thumbnailImage, path, offscreen)
        except: return xbmcgui.ListItem(label1, label2, iconImage, thumbnailImage, path)
    
   
    def findItemIDX(self, tvlist, userlist):
        return [idx for idx, tvshow in enumerate(tvlist) for usershow in userlist if tvshow.getLabel() == usershow]
    
    
    def selectDialog(self, list, header=ADDON_NAME, autoclose=0, preselect=None, multi=True, useDetails=True):
        if preselect is None: preselect = {True:[],False:-1}[multi]
        if multi: return xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
        else: return xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
        

    def scanDuplicates(self):
        dupLST = []
        delLST = []
        MoviesList = self.getMovies()
        if len(MoviesList) > 0:
            duplicates = [item for item, count in collections.Counter([{0:'%s (%d)'%(movie['label'],movie['year']),1:movie['label']}[DUPMATCH] for movie in MoviesList]).items() if count > 1]
            for item in duplicates:
                for movie in MoviesList:
                    title = {0:'%s (%d)'%(movie['label'],movie['year']),1:movie['label']}[DUPMATCH]
                    if item.lower() == title.lower(): dupLST.append(movie)
        if len(dupLST) > 0:
            dupLST.sort(key=lambda x:x['label'])
            listitem = self.buildListitem(dupLST)
            selects = self.selectDialog(listitem,LANGUAGE(30036))
            if selects:
                busy = self.progressDialogBG(0, string1=LANGUAGE(30040))
                delLST = [self.requestFile(listitem[select].getLabel2()) for select in selects if not listitem[select].getLabel2().startswith('stack://')]
                # delLST = [self.requestFile(dupLST[item].getLabel2()) for item in items]
                for idx, movie in enumerate(delLST):
                    updateDialogProgress = (idx) * 100 // len(delLST)
                    busy = self.progressDialogBG(updateDialogProgress, busy)
                    self.removeContent(movie)
                self.progressDialogBG(100, busy)
        else: self.notificationDialog(LANGUAGE(30033))
        
        
    def buildMenu(self):
        items  = [LANGUAGE(30002),LANGUAGE(30034),LANGUAGE(30035)]
        {None:sys.exit,
        -1:sys.exit,
        0:self.viewTVShows,
        1:self.scanDuplicates,
        2:REAL_SETTINGS.openSettings}[self.selectDialog(items,multi=False,useDetails=False)]()
        
        
    def progressDialogBG(self, percent=0, control=None, string1='', header=ADDON_NAME):
        if percent == 0 and control is None:
            control = xbmcgui.DialogProgressBG()
            control.create(header, ADDON_NAME)
            control.update(percent, string1)
        if percent == 100 and control is not None: return control.close()
        elif control is not None: control.update(percent, string1)
        return control
        
        
    def notificationDialog(self, message, header=ADDON_NAME, show=NOTIFY, sound=False, time=1000, icon=ICON):
        log('notificationDialog: ' + message)
        if not show: return
        try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except : xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
      
      
    def yesnoDialog(self, str1, str2='', str3='', header=ADDON_NAME, yes='', no='', autoclose=0):
        return xbmcgui.Dialog().yesno(header, str1, str2, str3, no, yes, autoclose)
        

if __name__ == '__main__':
    try: arg = sys.argv[1]
    except: arg = None    
    if arg is None: MM().buildMenu()
    elif arg == '-viewTVShows':  MM().viewTVShows()
    elif arg == '-scanSonarr':   MM().getMonitored()
    elif arg == '-clearTVShows': MM().setUserList([])
    elif arg == '-scanRadarr':   MM().getMonitored('movie')
    elif arg == '-clearMovies':  MM().setUserList([], 'movie')
