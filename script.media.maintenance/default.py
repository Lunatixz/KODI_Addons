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
import urlparse, urllib, urllib2, socket, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
from simplecache import SimpleCache, use_cache

# Plugin Info
ADDON_ID      = 'script.media.maintenance'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
SONARR_URL    = '%s/api/series?apikey=%s'%(REAL_SETTINGS.getSetting('Sonarr_IP'),REAL_SETTINGS.getSetting('Sonarr_API'))
RADARR_URL    = '%s/api/movie?apikey=%s'%(REAL_SETTINGS.getSetting('Radarr_IP'),REAL_SETTINGS.getSetting('Radarr_API'))
TIMEOUT       = 15
NOTIFY        = True
JSON_ENUM     = '["genre","studio","mpaa","premiered","file","art","thumbnail"]'
ITEM_ENUM     = '["genre","studio","mpaa","premiered","file","art","thumbnail","title","episode","season","showtitle"]'


def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)

class MM(object):
    def __init__(self):
        self.cache = SimpleCache()
        self.TVShowList = self.getTVShows()
        self.MoviesList = self.getMovies()
        
        
    def openURL(self, url):
        try:
            log('openURL, url = ' + str(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                request = urllib2.Request(url)
                request.add_header('User-Agent','Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)')
                cacheresponse = urllib2.urlopen(request, timeout=TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheresponse, expiration=datetime.timedelta(minutes=15))
            return json.loads(cacheresponse)
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return ''
            
            
    def getMonitored(self, type='series'):
        log('getMonitored, type = ' + type)
        if type == 'series': 
            mediaList = self.TVShowList
            url = SONARR_URL
            setSetting = 'ScanSonarr'
        else: 
            mediaList = self.MoviesList
            url = RADARR_URL
            setSetting = 'ScanRadarr'
        results  = self.openURL(url)
        if not results: return
        userList = self.getUserList(type)
        for idx, item in enumerate(results):
            updateDialogProgress = (idx) * 100 // len(results)
            REAL_SETTINGS.setSetting('setSetting','Scanning... (%d'%(updateDialogProgress)+'%)')
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
                    title = title.getLabel()
                    if title.lower() == show.lower(): 
                        log('getMonitored, kodi match: show = ' + show + ', title = ' + title)
                        userList.append(title)
                        break
        self.notificationDialog(LANGUAGE(30004))
        if type == 'series': REAL_SETTINGS.setSetting(setSetting,LANGUAGE(30011)%(datetime.datetime.now().strftime('%Y-%m-%d')))
        else: REAL_SETTINGS.setSetting(setSetting,LANGUAGE(30011)%(datetime.datetime.now().strftime('%Y-%m-%d')))
        if len(userList) > 0: self.setUserList(userList, type)
        
           
    def getUserList(self, type='series'):
        REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
        if type == 'series': 
            try: return (REAL_SETTINGS.getSetting('TVShowList').split(',') or [])
            except: return []
        else:
            try: return (REAL_SETTINGS.getSetting('MoviesList').split(',') or [])
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
            
        if len(userList) > 0: 
            msg = LANGUAGE(30010)%(len(userList))
        else: 
            self.notificationDialog(LANGUAGE(30017))
            REAL_SETTINGS.setSetting(setSetting0,'')
        userList = ','.join(userList)
        log('setUserList, UserList = ' + userList + ', type = ' + type)
        REAL_SETTINGS.setSetting(setSetting1,userList)
        REAL_SETTINGS.setSetting(setSetting2,msg)
        
        
    def hasMovie(self):
        return bool(xbmc.getCondVisibility('Library.HasContent(Movies)'))
        
        
    def hasTV(self):
        return bool(xbmc.getCondVisibility('Library.HasContent(TVShows)'))

        
    def sendJSON(self, command):
        log('sendJSON, command = ' + str(command))
        return json.loads(unicode(xbmc.executeJSONRPC(command), 'utf-8', errors='ignore'))

        
    def removeContent(self, playingItem, silent=False):
        type = playingItem["type"]
        dbid = playingItem["id"]
        log("removeContent, type = " + type + ", dbid = " + str(dbid)) 
        param  = {'episode':'episodeid','movie':'movieid'}[type]
        method = {'episodeid':'RemoveEpisode','movieid':'RemoveMovie'}[param]
        json_query = '{"jsonrpc":"2.0","method":"VideoLibrary.%s","params":{"%s":%s},"id":1}'%(method, param, str(dbid))
        file = playingItem["file"]
        if type == 'movie':
            if REAL_SETTINGS.getSetting('Monitor_Movies') == 'false': return 
            mediaInfo = playingItem["label"]
        else: 
            tvshow   = playingItem["showtitle"]
            userList = self.getUserList()
            if tvshow not in userList: return
            mediaInfo = '%s - %sx%s - %s'%(tvshow,playingItem["season"],playingItem["episode"],playingItem["label"])
        if silent == False:
            if not self.yesnoDialog(mediaInfo, file, header='%s - %s'%(ADDON_NAME,LANGUAGE(30021)), yes='Remove', no='Keep', autoclose=15000): return
        if REAL_SETTINGS.getSetting('Enable_Removal') == 'true': 
            self.sendJSON(json_query)
            xbmcvfs.delete(file)
            self.notificationDialog(LANGUAGE(30023)%mediaInfo)
        else: self.notificationDialog(LANGUAGE(30022))

                
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
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%d,"properties":%s}, "id": 1}'%(self.getActivePlayer(), ITEM_ENUM))
        json_response = self.sendJSON(json_query)
        if 'result' not in json_response: return {}
        return json_response['result'].get('item',{})
         
        
    def getTVShows(self):
        TVShowList = []
        if not self.hasTV(): return TVShowList
        json_query    = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"properties":%s}, "id": 1}'%(JSON_ENUM))
        json_response = self.sendJSON(json_query)
        if 'result' not in json_response: return []
        busy = self.busyDialog(0)
        for idx, item in enumerate(json_response['result']['tvshows']):
            updateDialogProgress = (idx) * 100 // len(json_response)
            self.busyDialog(updateDialogProgress, busy)
            TVShowList.append({'label':item['label'],'label2':item['file'],'thumb':(item['art'].get('poster','') or item['thumbnail'])})
        TVShowList.sort(key=lambda x:x['label'])
        self.busyDialog(100, busy)
        log("getTVShows, found tvshows "  + str(len(TVShowList)))
        return [self.getListitem(show['label'],show['label2'],show['thumb']) for show in TVShowList]
        
        
    def getMovies(self):
        MoviesList = []
        if not self.hasMovie(): return MoviesList
        json_query    = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":%s}, "id": 1}'%(JSON_ENUM))
        json_response = self.sendJSON(json_query)
        if 'result' not in json_response: return []
        busy = self.busyDialog(0)
        for idx, item in enumerate(json_response['result']['movies']):
            updateDialogProgress = (idx) * 100 // len(json_response)
            self.busyDialog(updateDialogProgress, busy)
            MoviesList.append({'label':item['label'],'label2':item['file'],'thumb':(item['art'].get('poster','') or item['thumbnail'])})
        MoviesList.sort(key=lambda x:x['label'])
        self.busyDialog(100, busy)
        log("getMovies, found movies "  + str(len(MoviesList)))
        return [self.getListitem(show['label'],show['label2'],show['thumb']) for show in MoviesList]
    
    
    def viewTVShows(self):
        select = self.selectDialog(self.TVShowList, 'Select one or multiple TV Shows', preselect=self.findItemLens(self.TVShowList,self.getUserList()))
        if select is not None: self.setUserList([self.TVShowList[idx].getLabel() for idx in select])

        
    def getListitem(self, label1="", label2="", iconImage="", thumbnailImage="", path="", offscreen=False):
        try: return xbmcgui.ListItem(label1, label2, iconImage, thumbnailImage, path, offscreen)
        except: return xbmcgui.ListItem(label1, label2, iconImage, thumbnailImage, path)
    
   
    def findItemLens(self, tvlist, userlist):
        return [idx for idx, tvshow in enumerate(tvlist) for usershow in userlist if tvshow.getLabel() == usershow]
    
    
    def selectDialog(self, list, header=ADDON_NAME, autoclose=0, preselect=[], useDetails=True):
        return xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
        
        
    def progressDialogBG(self, percent=0, control=None, string1='', header=ADDON_NAME, notice=NOTIFY):
        if not notice: return
        if percent == 0 and not control:
            control = xbmcgui.DialogProgressBG()
            control.create(header, string1)
        elif percent == 100 and control: return control.close()
        elif control: control.update(percent, string1)
        return control
        
        
    def busyDialog(self, percent=0, control=None):
        if percent == 0 and not control:
            control = xbmcgui.DialogBusy()
            control.create()
        elif percent == 100 and control: return control.close()
        elif control: control.update(percent)
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
    if arg is None: REAL_SETTINGS.openSettings()
    elif arg == '-viewTVShows':  MM().viewTVShows()
    elif arg == '-scanSonarr':   MM().getMonitored()
    elif arg == '-clearTVShows': MM().setUserList([])
    elif arg == '-scanRadarr':   MM().getMonitored('movie')
    elif arg == '-clearMovies':  MM().setUserList([], 'movie')
        