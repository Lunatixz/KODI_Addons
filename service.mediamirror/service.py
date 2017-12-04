#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of MediaMirror
#
# MediaMirror is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MediaMirror is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MediaMirror.  If not, see <http://www.gnu.org/licenses/>.

import re, socket, json, copy, os, traceback, requests, datetime, time, random
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

# Plugin Info
ADDON_ID = 'service.mediamirror'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON = REAL_SETTINGS.getAddonInfo('icon')
DEBUG = REAL_SETTINGS.getSetting('enableDebug') == "true"
AUTO = REAL_SETTINGS.getSetting('autoOffset') == "true"
POLL = int(REAL_SETTINGS.getSetting('pollTIME'))
socket.setdefaulttimeout(30)

def log(msg, level = xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR:
        return
    elif level == xbmc.LOGERROR:
        msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + str(msg), level)
       
def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('ascii', 'ignore')
    return string
    
def uni(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('utf-8', 'ignore' )
        else:
           string = ascii(string)
    return string
     
def sendJSON(command):
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))
    return uni(data)
    
def dumpJson(mydict, sortkey=True):
    log("dumpJson")
    return json.dumps(mydict, sort_keys=sortkey)
    
def loadJson(string):
    log("loadJson")
    if len(string) == 0:
        return {}
    try:
        return json.loads(uni(string))
    except Exception,e:
        return json.loads(ascii(string))
        
def SendRemote(IPP, AUTH, CNUM, params):
    log('SendRemote, IPP = ' + IPP)
    try:
        xbmc_host, xbmc_port = IPP.split(":")
        username, password = AUTH.split(":")
        kodi_url = 'http://' + xbmc_host +  ':' + xbmc_port + '/jsonrpc'
        print kodi_url
        print params
        print username, password
        headers = {"Content-Type":"application/json"}
        time_before = time.time()
        r = requests.post(kodi_url,
                          data=json.dumps(params),
                          headers=headers,
                          auth=(username,password))
        xbmc.sleep(10) #arbitrary sleep to avoid network flood, add to latency value.
        time_after = time.time() 
        time_taken = time_after-time_before
        REAL_SETTINGS.setSetting("Client%d_latency"%CNUM,("%.2f" % round(time_taken,2)))
        if AUTO == True:
            REAL_SETTINGS.setSetting("Client%d_offSet"%CNUM,("%.2f" % round(time_taken,2)))
        return loadJson(response.read())
    except Exception,e:
        pass
    
def getActivePlayer():
    json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
    json_response = loadJson(sendJSON(json_query))
    if json_response and 'result' in json_response:
        for response in json_response['result']:
            id = response.get('playerid','')
            if id:
                log("getActivePlayer, id = " + str(id)) 
                return id
    return 1
    
class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.Player())
        
        
    def onPlayBackStarted(self):
        log('onPlayBackStarted')
        #collect detailed player info
        self.playType, self.playLabel, self.playFile, self.playThumb = self.getPlayerItem()
        #some client screensavers do not respect onplay, but do respect onstop. send stop to close screensaver before playback.
        if self.stopClient(self.Service.Monitor.IPPlst) == True:
            self.playClient(self.Service.Monitor.IPPlst)
        
        
    def onPlayBackEnded(self):
        log('onPlayBackEnded')
            
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        self.stopClient(self.Service.Monitor.IPPlst)
        
        
    def onPlayBackPaused(self):
        log('onPlayBackPaused')
        self.pauseClient(self.Service.Monitor.IPPlst)

        
    def onPlayBackResumed(self):
        log('onPlayBackResumed')
        self.resumeClient(self.Service.Monitor.IPPlst)
        
        
    def onPlayBackSpeedChanged(self):
        log('onPlayBackSpeedChanged')
        self.playClient(self.Service.Monitor.IPPlst)
        
        
    def onPlayBackSeekChapter(self):
        log('onPlayBackSeekChapter')
        self.playClient(self.Service.Monitor.IPPlst)
        
        
    def onPlayBackSeek(self):
        log('onPlayBackSeek')
        self.playClient(self.Service.Monitor.IPPlst)

        
    def getPlayerFile(self):
        log('getPlayerFile')
        try:
            return (self.getPlayingFile()).replace("\\\\","\\")
        except:
            return ''
            
            
    def getPlayerTime(self):
        log('getPlayerTime')
        try:
            return self.getTime()
        except:
            return 0
             
             
    def getPlayerLabel(self):
        log('getPlayerLabel')
        try:
            return (xbmc.getInfoLabel('Player.label') or xbmc.getInfoLabel('VideoPlayer.label'))
        except:
            return ''

            
    def getPlayerItem(self):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%d,"properties":["file","title","thumbnail","showtitle"]},"id":1}'%getActivePlayer())
        json_response = loadJson(sendJSON(json_query))
        if json_response and 'result' in json_response and 'item' in json_response['result']:
            type = json_response['result']['item']['type']
            if type == 'movie':
                label = json_response['result']['item']['label']
            else:
                label = (json_response['result']['item'].get('showtitle','') or json_response['result']['item']['label']) + ' - ' + json_response['result']['item']['title']
            if type == 'channel':
                file = json_response['result']['item']['id']
            else:
                file = json_response['result']['item'].get('file','')
            thumb = (json_response['result']['item']['thumbnail'] or ICON)
            return type, label, file, thumb
        return 'video', self.getPlayerLabel(), self.getPlayerFile(), ICON

        
    def getClientPVRid(self, IPP, label, id):
        log('getClientPVRid')      
        idLST = []
        for item in IPP[4]:
            log('getClientPVRid, %s =?= %s'%label, item['label'])
            if label == item['label']:
                log('getClientPVRid, found %s'%item['channelid'])
                #allow for duplicates, ex. multi-tuners on same PVR backend. 
                idLST.append(item['channelid'])
            if len(idLst) > 0:
                return random.choice(idLST)
        return id #return host id, maybe get a lucky match
        
                
    def sendClientInfo(self, IPPlst, label, thumb):
        log('sendClientInfo')
        params = ({"jsonrpc": "2.0", "method": "GUI.ShowNotification", "params": {"title":"Now Playing","message":label,"image":thumb}})
        seekValue = self.getPlayerTime()
        for IPP in IPPlst:
            SendRemote(IPP[0], IPP[1], IPP[3], params)
        return True
        
                
    def playClient(self, IPPlst):
        log('playClient')
        print self.playType, self.playLabel, self.playFile, self.playThumb
        for IPP in IPPlst:
            if type == 'channel':
                params = ({"jsonrpc": "2.0", "method": "Player.Open", "params": {"item": {"channelid": self.getClientPVRid(IPP, self.playLabel.split(' - ')[0], self.playFile)}}})
            elif self.getPlayerTime() > 0:
                seek = str(datetime.timedelta(seconds=self.getPlayerTime()))
                log('playClient, seek = ' + seek)
                seek = seek.split(":")
                try:
                    hours = int(seek[0])
                except:
                    hours = 0
                try:
                    minutes = int(seek[1])
                except:
                    minutes = 0
                Mseconds = str(seek[2])
                seconds = int(Mseconds.split(".")[0])
                try:
                    milliseconds = int(Mseconds.split(".")[1])
                    milliseconds = int(str(milliseconds)[:3])
                except:
                    milliseconds = 0        
                milliseconds + IPP[2] #add user offset.
                params = ({"jsonrpc": "2.0", "method": "Player.Open", "params": {"item": {"file": self.playFile},"options":{"resume":{"hours":hours,"minutes":minutes,"seconds":seconds,"milliseconds":milliseconds}}}})
            else:
                params = ({"jsonrpc": "2.0", "method": "Player.Open", "params": {"item": {"path": self.playFile}}})
            SendRemote(IPP[0], IPP[1], IPP[3], params)
        self.sendClientInfo(IPPlst, self.playLabel, thumb)
        return True

            
    def stopClient(self, IPPlst):
        log('stopClient')
        params = ({"jsonrpc":"2.0","id":1,"method":"Player.Stop","params":{"playerid":1}})       
        for IPP in IPPlst: 
            SendRemote(IPP[0], IPP[1], IPP[3], params)
        return True
        
        
    def pauseClient(self, IPPlst):
        log('pauseClient')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"pause"}})
        for IPP in IPPlst: 
            SendRemote(IPP[0], IPP[1], IPP[3], params)
        return True
        
        
    def resumeClient(self, IPPlst):
        log('resumeClient')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"play"}})       
        for IPP in IPPlst: 
            SendRemote(IPP[0], IPP[1], IPP[3], params)
        return True
        
        
    def playlistClient(self, IPPlst, file):
        log('PlaylistUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Player.Open","params":{"item": {"file": file}}})
        for IPP in IPPlst: 
            SendRemote(IPP[0], IPP[1], IPP[3], params)
        return True
             

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self, xbmc.Monitor())
        self.IPPlst = []
      
      
    def onSettingsChanged(self):
        log("onSettingsChanged")
        AUTO  = REAL_SETTINGS.getSetting('autoOffset') == "true"
        DEBUG = REAL_SETTINGS.getSetting('enableDebug') == "true"
        POLL  = int(REAL_SETTINGS.getSetting('pollTIME'))
        self.initClients()
        
        
    def initClients(self):
        log('initClients')
        self.IPPlst = []
        for i in range(1,6):
            if REAL_SETTINGS.getSetting("Client%d"%i) == "true":
                IPP = [REAL_SETTINGS.getSetting("Client%d_IPP"%i),REAL_SETTINGS.getSetting("Client%d_UPW"%i),float(REAL_SETTINGS.getSetting('Client%d_offSet'%i)),i]
                self.IPPlst.append(IPP + [self.initClientPVR(IPP)])
        log('initClients, IPPlst = ' + str(self.IPPlst))
        
        
    def initClientPVR(self, IPP):
        log('initClientPVR')
        params = ({"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":"alltv"},"id":1})
        json_response = SendRemote(IPP[0], IPP[1], IPP[3], params)
        if json_response and 'result' in json_response and 'channels' in json_response['result']:
            return json_response['result']['channels']
        return {}
        

class Service():
    def __init__(self):
        self.Player = Player()
        self.Monitor = Monitor()
        self.Player.Service  = self
        self.start()
 
 
    def chkClients(self):
        #check if clients are playing the same content, ie "insync", return "outofsync" clients.
        failedLst = []
        for IPPlst in self.Monitor.IPPlst:
            if xbmcgui.Window(10000).getProperty("PseudoTVRunning") == "True": 
                return []
                
            # try to find clients activeplayer... no known json request?
            for i in range(3):
                try:
                    params = ({"jsonrpc":"2.0","id":1,"method":"Player.GetItem","params":{"playerid":i,"properties":["title"]}})
                    json_response = SendRemote(IPPlst[0], IPPlst[1], IPPlst[3], params)
                    if json_response:
                        break
                except:
                    log("chkClients, Invalid ActivePlayer %d"%i)
                    
            log("chkClients, IPP = " + str(IPPlst[0]))
            if json_response and 'result' in json_response and 'item' in json_response['result']:
                if 'file' in json_response['result']['item']:
                    clientFile  = json_response['result']['item']['file']
                    log("chkClients, clientFile = " + clientFile)       
                    if clientFile != self.Player.getPlayerFile():
                        failedLst.append(IPPlst)
                else:
                    #not all items contain a file, ex. pvr, playlists. so check title.
                    clientLabel = json_response['result']['item']['label']
                    log("chkClients, clientLabel = " + clientLabel) 
                    if clientLabel != self.Player.getPlayerLabel():
                        failedLst.append(IPPlst)
            else:
                log("chkClients, json_response = " + str(json_response))
        return failedLst
        

    def start(self):
        self.Monitor.initClients()
        while not self.Monitor.abortRequested():
            if self.Player.isPlayingVideo() == True and len(self.Monitor.IPPlst) > 0:
                if xbmcgui.Window(10000).getProperty("PseudoTVRunning") == "True": 
                    self.Monitor.waitForAbort(POLL)
                    continue 
                self.Player.playClient(self.chkClients())
            if self.Monitor.waitForAbort(POLL):
                break
        self.Player.stopClient(self.Monitor.IPPlst)
Service()