#   Copyright (C) 2016 Jason Anderson, Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os, sys, re, unicodedata, traceback
import time, datetime, threading, _strptime, calendar, socket
import httplib, urllib, urllib2, zlib, feedparser, HTMLParser
import base64, shutil, random, errno

from operator import itemgetter
from parsers import HDTrailers
from parsers import xmltv
from utils import *
from xml.etree import ElementTree as ET
from xml.dom.minidom import parse, parseString
from subprocess import Popen, PIPE, STDOUT
from Playlist import Playlist
from Globals import *
from Channel import Channel
from VideoParser import VideoParser
from FileAccess import FileAccess
from hdhr import hdhr
from apis import sickbeard
from apis import couchpotato
from apis import tvdb
from apis import tmdb
from datetime import date
from datetime import timedelta
from BeautifulSoup import BeautifulSoup
from parsers import ustvnow
from pyfscache import *

socket.setdefaulttimeout(30)
sys.setrecursionlimit(10000)

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
    
# Commoncache plugin import
try:
    import StorageServer
except Exception,e:
    import storageserverdummy as StorageServer
    CACHE_ENABLED = False
    
try:
    from metahandler import metahandlers
    metaget = metahandlers.MetaData(preparezip=False, tmdb_api_key=TMDB_API_KEY)
    ENHANCED_DATA = True                
except Exception,e:  
    ENHANCED_DATA = False
    xbmc.log("script.pseudotv.live-ChannelList: metahandler Import failed! " + str(e))    

class ChannelList:
    def __init__(self):
        self.networkList = []
        self.studioList = []
        self.mixedGenreList = []
        self.showGenreList = []
        self.movieGenreList = []
        self.movie3Dlist = []
        self.musicGenreList = []
        self.pluginList = []
        self.PVRList = []
        self.FavouritesList = []
        self.HDHRList = []
        self.USTVList = []
        self.showList = []
        self.channels = []
        self.file_detail_CHK = []
        self.threadPaused = False
        self.background = True   
        self.quickflipEnabled = False
        self.runningActionChannel = 0
        self.runningActionId = 0
        self.enteredChannelCount = 0
        self.filecount = 0
        self.startDate = 0
        self.startTime = 0 
        self.sleepTime = 0
        self.xmlTvFile = ''
        self.stars = ''
        self.genre = ''
        self.rating = ''
        self.FileListCache = ''
        self.videoParser = VideoParser()
        self.youtube_player = self.youtube_player_ok()
        self.vimeo_player = self.vimeo_player_ok()
        self.USTVnow_ok = isUSTVnow()
        random.seed() 

        
    def readConfig(self):
        self.durFilter = 0
        self.Playlist_Limit = PlaylistLimit()
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.log('Force Reset is ' + str(self.forceReset))
        self.startMode = int(REAL_SETTINGS.getSetting("StartMode"))
        self.log('Start Mode is ' + str(self.startMode))
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        self.channelResetSetting = int(REAL_SETTINGS.getSetting("ChannelResetSetting"))
        self.inc3D = REAL_SETTINGS.getSetting('Include3D') == "true"
        self.log("Include 3D is " + str(self.inc3D))
        self.incIceLibrary = REAL_SETTINGS.getSetting('IncludeIceLib') == "true"
        self.log("IceLibrary is " + str(self.incIceLibrary))
        self.incBCTs = REAL_SETTINGS.getSetting('IncludeBCTs') == "true"
        self.log("IncludeBCTs is " + str(self.incBCTs)) 
        self.includeMeta = REAL_SETTINGS.getSetting('IncludeMeta') == "true"
        self.log("IncludeMeta is " + str(self.includeMeta)) 
        self.sbAPI = sickbeard.SickBeard(REAL_SETTINGS.getSetting('sickbeard.baseurl'),REAL_SETTINGS.getSetting('sickbeard.apikey'))
        self.cpAPI = couchpotato.CouchPotato(REAL_SETTINGS.getSetting('couchpotato.baseurl'),REAL_SETTINGS.getSetting('couchpotato.apikey'))
        self.quickFlip = REAL_SETTINGS.getSetting('Enable_quickflip') == "true"
        self.startTime = time.time()
        self.tvdbAPI = tvdb.TVDB()
        self.tmdbAPI = tmdb.TMDB() 
        self.findMaxChannels()

        if SETTOP:
            self.backgroundUpdating = 0
            self.channelResetSetting = 0
        self.log('Background Updating is ' + str(self.backgroundUpdating))
        self.log('Channel Reset Setting is ' + str(self.channelResetSetting))
            
        if self.forceReset == True:
            REAL_SETTINGS.setSetting("INTRO_PLAYED","false") # Intro Video Reset
            REAL_SETTINGS.setSetting('StartupMessage', 'false') # Startup Message Reset 
            REAL_SETTINGS.setSetting('ReminderLst', '') # Reset Reminders
            REAL_SETTINGS.setSetting('FavChanLst', '') # Reset FavChannels
            REAL_SETTINGS.setSetting('ForceChannelReset', 'false') # Force Channel Reset
            self.forceReset = False

        try:
            self.lastResetTime = int(ADDON_SETTINGS.getSetting("LastResetTime"))
        except Exception,e:
            self.lastResetTime = 0
        try:
            self.lastExitTime = int(ADDON_SETTINGS.getSetting("LastExitTime"))
        except Exception,e:
            self.lastExitTime = int(time.time())
                      

    def setupList(self, background=False):
        self.readConfig()
        foundvalid = False
        makenewlists = False
        self.background = background
        self.updateDialogProgress = self.myOverlay.progressPercentage
        self.log("setupList, background = " + str(self.background))

        if self.backgroundUpdating > 0 and self.myOverlay.isMaster == True:
            makenewlists = True
            
        # Go through all channels, create their arrays, and setup the new playlist
        for i in range(self.maxChannels):
            self.channels.append(Channel())                
            self.setupChannel(i + 1, self.background, makenewlists, False)
            
            if self.channels[i].isValid == True:
                self.updateDialogProgress = i * 100 // self.enteredChannelCount
                self.setBackgroundStatus("Initializing: Loading Channel " + str(i + 1),self.updateDialogProgress,string2=" ")
                foundvalid = True
                
        if makenewlists == True:
            REAL_SETTINGS.setSetting('ForceChannelReset', 'false')

        if foundvalid == False and makenewlists == False:
            for i in range(self.maxChannels):
                self.setupChannel(i + 1, self.background, True, False)
                
                if self.channels[i].isValid == True:
                    self.updateDialogProgress = i * 100 // self.enteredChannelCount
                    self.setBackgroundStatus("Initializing: Loading Channel " + str(i + 1),self.updateDialogProgress,string2=" ")
                    foundvalid = True
                    break
                    
        self.setBackgroundStatus('Initializing: Loading complete',100)
        return self.channels 

        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelList: ' + msg, level)


    # Determine the maximum number of channels by opening consecutive settings until we don't find one.
    def findMaxChannels(self):
        self.log('findMaxChannels')
        localCount = 0
        self.maxChannels = 0
        self.enteredChannelCount = 0      
        self.freshBuild = False

        for i in range(CHANNEL_LIMIT):
            chtype = 9999
            chsetting1 = ''
            chsetting2 = ''
            chsetting3 = ''
            chsetting4 = ''
            
            try:
                chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_type'))
                chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_1')
                chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_2')
                chsetting3 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_3')
                chsetting4 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_4')
            except Exception,e:
                pass

            if chtype == 0:
                if FileAccess.exists(xbmc.translatePath(chsetting1)):
                    localCount += 1
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
            elif chtype <= 7:
                if len(chsetting1) > 0:
                    localCount += 1
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
            elif chtype != 9999:
                if len(chsetting1) > 0:
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1

            if self.forceReset and (chtype != 9999):
                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_changed', "True")

        #if local quota not met, disable quickFlip.
        if self.quickFlip == True and localCount > (self.enteredChannelCount/4):
            self.quickflipEnabled = True
        
        if self.maxChannels == 1:
            REAL_SETTINGS.setSetting("Config","%i channel"%self.enteredChannelCount)
        else:
            REAL_SETTINGS.setSetting("Config","%i channels"%self.enteredChannelCount)
        self.log('findMaxChannels, quickflipEnabled = ' + str(self.quickflipEnabled))
        self.log('findMaxChannels return ' + str(self.maxChannels))

        
    def sendJSON(self, command):
        self.log('sendJSON')
        data = ''
        try:
            data = xbmc.executeJSONRPC(uni(command))
        except UnicodeEncodeError:
            data = xbmc.executeJSONRPC(ascii(command))
        return uni(data)
        
     
    def setupChannel(self, channel, background = False, makenewlist = False, append = False):
        returnval = False
        createlist = makenewlist
        chtype = 9999
        chsetting1 = ''
        chsetting2 = ''
        chsetting3 = ''
        chsetting4 = ''
        needsreset = False
        valid = False 
        self.background = background
        self.settingChannel = channel
                               
        try:
            chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
            chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')
            chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_2')
            chsetting3 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_3')
            chsetting4 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_4')
        except:
            pass

        while len(self.channels) < channel:
            self.channels.append(Channel())

        if chtype == 9999:
            valid = False
        elif chtype == 0:
            if FileAccess.exists(xbmc.translatePath(chsetting1)) == True:
                valid = True
        elif chtype == 7:
            if FileAccess.exists(chsetting1) == True:
                valid = True
        elif chtype in [8,9]:
            if self.Valid_ok(chsetting2) == True:
                valid = True
        elif chtype == 10:
            if self.youtube_player != 'False':
                valid = True
        elif chtype in [11,15,16]:
            if self.Valid_ok(chsetting1) == True:
                valid = True
        else:
            if len(chsetting1) > 0:
                valid = True
        self.log('setupChannel ' + str(channel) + ', valid = ' + str(valid))
        
        if valid == False:
            self.channels[channel - 1].isValid = False
            return False
        
        # find missing channel logos
        if chtype not in [6,7]:
            FindLogo(chtype, self.getChannelName(chtype, channel, chsetting1))
            
        self.channels[channel - 1].type = chtype
        self.channels[channel - 1].isSetup = True
        self.channels[channel - 1].hasChanged = False
        self.channels[channel - 1].loadRules(channel)
        self.runActions(RULES_ACTION_START, channel, self.channels[channel - 1])

        try:
            needsreset = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_changed') == 'True'
        except:
            needsreset = False
                 
        # LiveTV Force Reset
        if chtype == 8 and REAL_SETTINGS.getSetting('ForceLiveChannelReset') == "true":
            needsreset = True

        if needsreset:
            self.channels[channel - 1].isSetup = False
            
        self.log('setupChannel ' + str(channel) + ', needsreset = ' + str(needsreset))
        self.log('setupChannel ' + str(channel) + ', makenewlist = ' + str(makenewlist))
            
        # If possible, use an existing playlist
        # Don't do this if we're appending an existing channel
        # Don't load if we need to reset anyway
        if FileAccess.exists(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') and append == False and needsreset == False:
            try:
                self.channels[channel - 1].totalTimePlayed = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_time', True))
                createlist = True
                
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    self.setBackgroundStatus("Initializing: Loading Channel " + str(channel),string2='loading playlist')
                    self.channels[channel - 1].isValid = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    timedif = time.time() - self.lastResetTime
                    returnval = True
                    
                    if chtype == 8: 
                        # If this channel has been watched for longer than it lasts, reset the channel
                        if self.channels[channel - 1].totalTimePlayed < self.channels[channel - 1].getTotalDuration():
                            createlist = False 
       
                        if timedif >= (LIVETV_MAXPARSE - 7200) or self.channels[channel - 1].totalTimePlayed >= (LIVETV_MAXPARSE - 7200):
                            createlist = True
                    else: 
                        if self.channelResetSetting == 0:
                            # If this channel has been watched for longer than it lasts, reset the channel
                            if self.channels[channel - 1].totalTimePlayed < self.channels[channel - 1].getTotalDuration():
                                createlist = False

                        if self.channelResetSetting > 0 and self.channelResetSetting < 4:
                        
                            if self.channelResetSetting == 1 and timedif < (60 * 60 * 24):
                                createlist = False

                            if self.channelResetSetting == 2 and timedif < (60 * 60 * 24 * 7):
                                createlist = False

                            if self.channelResetSetting == 3 and timedif < (60 * 60 * 24 * 30):
                                createlist = False

                            if timedif < 0:
                                createlist = False

                        if self.channelResetSetting == 4:
                            createlist = False
            except Exception,e:
                self.log('setupChannel ' + str(channel) + ', _time failed! ' + str(e))
                
        if createlist or needsreset:
            # self.clearFileListCache(chtype, channel)
            self.channels[channel - 1].isValid = False
            if makenewlist:
                try:
                    FileAccess.delete(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u')
                except:
                    self.log("Unable to delete " + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)
                append = False

                if createlist:
                    ADDON_SETTINGS.setSetting('LastResetTime', str(int(time.time())))
                    
        if append == False:
            if chtype in [0,1,3,5,6] and chsetting2 == str(MODE_ORDERAIRDATE):
                self.channels[channel - 1].mode = MODE_ORDERAIRDATE

            # if there is no start mode in the channel mode flags, set it to the default
            if self.channels[channel - 1].mode & MODE_STARTMODES == 0:
                if self.startMode == 0:
                    self.channels[channel - 1].mode |= MODE_RESUME
                elif self.startMode == 1:
                    self.channels[channel - 1].mode |= MODE_REALTIME
                elif self.startMode == 2:
                    self.channels[channel - 1].mode |= MODE_RANDOM

        if ((createlist or needsreset) and makenewlist) or append:
            self.log('setupChannel, Updating Channel ' + str(channel))
            
            if self.makeChannelList(channel, chtype, chsetting1, chsetting2, chsetting3, chsetting4, append) == True:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    returnval = True
                    self.updateDialogProgress = (channel - 1) // self.enteredChannelCount
                    self.setBackgroundStatus("Initializing: Loading Channel " + str(channel),inc=self.updateDialogProgress,string2='reading playlist')
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    self.channels[channel - 1].isValid = True
                    
                    # Don't reset variables on an appending channel
                    if append == False:
                        self.channels[channel - 1].totalTimePlayed = 0
                        ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', '0')

                        if needsreset and self.channels[channel - 1].hasChanged == False:
                            ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_changed', 'False')
                            self.channels[channel - 1].isSetup = True
                            
        if self.channels[channel - 1].hasChanged == True:
            ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_changed', 'True')
                    
        self.runActions(RULES_ACTION_BEFORE_CLEAR, channel, self.channels[channel - 1])

        # Don't clear history when appending channels            
        if append == False and self.myOverlay.isMaster:
            self.clearPlaylistHistory(channel)
            self.updateDialogProgress = (channel - 1) // self.enteredChannelCount
            self.setBackgroundStatus("Initializing: Loading Channel " + str(channel),inc=self.updateDialogProgress,string2='clearing playlist')
            
        if append == False:
            self.runActions(RULES_ACTION_BEFORE_TIME, channel, self.channels[channel - 1])

            if self.channels[channel - 1].mode & MODE_ALWAYSPAUSE > 0:
                self.channels[channel - 1].isPaused = True

            if self.channels[channel - 1].mode & MODE_RANDOM > 0:
                self.channels[channel - 1].showTimeOffset = random.randint(0, self.channels[channel - 1].getTotalDuration())

            if self.channels[channel - 1].mode & MODE_REALTIME > 0:
                timedif = int(self.myOverlay.timeStarted) - self.lastExitTime
                self.channels[channel - 1].totalTimePlayed += timedif

            if self.channels[channel - 1].mode & MODE_RESUME > 0:
                self.channels[channel - 1].showTimeOffset = self.channels[channel - 1].totalTimePlayed
                self.channels[channel - 1].totalTimePlayed = 0

            while self.channels[channel - 1].showTimeOffset > self.channels[channel - 1].getCurrentDuration():
                self.channels[channel - 1].showTimeOffset -= self.channels[channel - 1].getCurrentDuration()
                self.channels[channel - 1].addShowPosition(1)

        self.channels[channel - 1].name = self.getChannelName(chtype, channel, chsetting1)

        if ((createlist or needsreset) and makenewlist) and returnval:
            self.runActions(RULES_ACTION_FINAL_MADE, channel, self.channels[channel - 1])
        else:
            self.runActions(RULES_ACTION_FINAL_LOADED, channel, self.channels[channel - 1])
            
        self.log('setupChannel ' + str(channel) + ', append = ' + str(append))
        self.log('setupChannel ' + str(channel) + ', createlist = ' + str(createlist))
        return returnval

        
    def clearPlaylistHistory(self, channel):
        self.log("clearPlaylistHistory")

        if self.channels[channel - 1].isValid == False:
            self.log("clearPlaylistHistory, channel " + str(channel) + " playlist not valid")
            return

        # if we actually need to clear anything
        if self.channels[channel - 1].totalTimePlayed > (60 * 60 * 24 * 2):
            try:
                fle = FileAccess.open(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', 'w')
            except:
                self.log("clearPlaylistHistory Unable to open the smart playlist", xbmc.LOGERROR)
                return

            flewrite = uni("#EXTM3U\n")
            tottime = 0
            timeremoved = 0

            for i in range(self.channels[channel - 1].Playlist.size()):
                tottime += self.channels[channel - 1].getItemDuration(i)

                if tottime > (self.channels[channel - 1].totalTimePlayed - (60 * 60 * 12)):
                    tmpstr = str(self.channels[channel - 1].getItemDuration(i)) + ','
                    tmpstr += self.channels[channel - 1].getItemTitle(i) + "//" + self.channels[channel - 1].getItemEpisodeTitle(i) + "//" + self.channels[channel - 1].getItemDescription(i) + "//" + self.channels[channel - 1].getItemgenre(i) + "//" + self.channels[channel - 1].getItemtimestamp(i) + "//" + self.channels[channel - 1].getItemLiveID(i)
                    tmpstr = uni(tmpstr[:2036])
                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                    tmpstr = uni(tmpstr) + uni('\n') + uni(self.channels[channel - 1].getItemFilename(i))
                    flewrite += uni("#EXTINF:") + uni(tmpstr) + uni("\n")
                else:
                    timeremoved = tottime
            fle.write(flewrite)
            fle.close()

            if timeremoved > 0:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == False:
                    self.channels[channel - 1].isValid = False
                else:
                    self.channels[channel - 1].totalTimePlayed -= timeremoved
                    # Write this now so anything sharing the playlists will get the proper info
                    ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', str(self.channels[channel - 1].totalTimePlayed))


    def getChannelName(self, chtype, channel, opt=None, suffix=True):
        self.log("getChannelName")
        chname = self.getChname(channel)
        if chname and len(chname) > 0:
            return chname

        if chtype in [0,1,2,3,4,5,6,7,12,16]:
            if not opt:
                opt = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')
            if chtype == 0:
                return self.getSmartPlaylistName(opt)
            elif chtype == 1 or chtype == 2:
                return opt
            elif chtype == 6:
                return opt.split('|')[0]
            elif chtype == 3:
                if suffix == False:
                    return opt
                else:
                    return opt + " TV"
            elif chtype == 4:
                if suffix == False:
                    return opt
                else:
                    return opt + " Movies"
            elif chtype == 5:
                if suffix == False:
                    return opt
                else:
                    return opt + " Mixed"
            elif chtype == 12:
                if suffix == False:
                    return opt
                else:
                    return opt + " Music"
            elif chtype in [7,16]:
                try:
                    if opt[-1] == '/' or opt[-1] == '\\':
                        return os.path.split(opt[:-1])[1]
                    elif len(os.path.split(opt)[1]) > 0:
                        return os.path.split(opt)[1]
                    else:
                        return opt
                except:
                    return opt        
        return ''
        
        
    def getChtype(self, channel): 
        self.log("getChtype")
        try:
            return int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
        except:
            return 9999
        
        
    def getChname(self, channel):
        self.log("getChname")
        try:
            if int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount')) > 0:
                for i in range(RULES_PER_PAGE):         
                    try:
                        if int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_id" %str(i+1))) == 1:
                            return ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_opt_1" %str(i+1))
                    except:
                        pass
        except:
            pass
        return ''
                
                
    # Open the smart playlist and read the name out of it...this is the channel name
    def getSmartPlaylistName(self, fle):
        self.log('getSmartPlaylistName')
        fle = xbmc.translatePath(fle)

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log("getSmartPlaylistName Unable to open the smart playlist " + fle, xbmc.LOGERROR)
            return ''

        try:
            dom = parse(xml)
        except:
            self.log('getSmartPlaylistName Problem parsing playlist ' + fle, xbmc.LOGERROR)
            xml.close()
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log('getSmartPlaylistName return ' + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.log("Unable to get the playlist name.", xbmc.LOGERROR)
            return ''
    
    
    # Based on a smart playlist, create a normal playlist that can actually be used by us
    def makeChannelList(self, channel, chtype, setting1, setting2, setting3, setting4, append = False):
        self.log('makeChannelList, CHANNEL: ' + str(channel))
        # self.getFileListCache(chtype, channel)
        msg = 'default' 
        fileListCHK = False
        israndom = False  
        isreverse = False
        bctType = None
        fileList = []
        limit = MEDIA_LIMIT #Global

        # Correct Youtube/Media Limit/Sort Values from outdated configurations
        if chtype in [7,10,11,13,15,16]:
            if chtype == 10:
                setting2 = setting2.replace('7','Multi Playlist').replace('8','Multi Channel').replace('3','User Subscription')
                setting2 = setting2.replace('4','User Favorites').replace('5','Search Query').replace('9','Raw gdata')
                setting2 = setting2.replace('31','Seasonal').replace('1','Channel').replace('2','Playlist')   
            setting3 = setting3.replace('Unlimited','0').replace('Global','')
            setting4 = setting4.replace('Default','0').replace('Random','1').replace('Reverse','2') 
        
            # Set Media Sort
            if setting4 == '1':
                #RANDOM
                israndom = True
            elif setting4 == '2':
                #REVERSE ORDER
                isreverse = True
            # Set Media Limit
            try:
                limit = int(setting3)
                # Enforce Media limits for LowPower profiles
                if isLowPower() == True:
                    raise Exception()
            except Exception,e:
                limit = MEDIA_LIMIT  
        
            # set real max limits for 'unlimited' by chtype
            if chtype in [15,16] and (limit > PLUGINUPNP_MAXPARSE or limit == 0):
                limit = PLUGINUPNP_MAXPARSE
            elif chtype in [10,11] and (limit > YOUTUBERSS_MAXPARSE or limit == 0):
                limit = YOUTUBERSS_MAXPARSE
            elif limit == 0:
                limit = self.Playlist_Limit
                         
        elif chtype == 8:
            limit = LIVETV_MAXPARSE
        elif chtype == 9:
            limit = int(INTERNETTV_MAXPARSE / INTERNETTV_DURATION)
        elif limit == 0:
            limit = self.Playlist_Limit #Unlimited limit ie. '0' is a invalid limit count, and only valid for kodi xsp. Make it a real number by setting a boundary.
        else:
            limit = MEDIA_LIMIT
        self.log("makeChannelList, Using Parse-limit " + str(limit))
        
        # Directory
        if chtype == 7:
            fileList = self.createDirectoryPlaylist(setting1, setting3, setting4, limit)     
            
        # LiveTV
        elif chtype == 8:
            self.log("Building LiveTV Channel, " + setting1 + " , " + setting2 + " , " + setting3)
            # HDHomeRun #
            if setting2[0:9] == 'hdhomerun' and REAL_SETTINGS.getSetting('HdhomerunMaster') == "true":
                #If you're using a HDHomeRun Dual and want Tuner 1 assign false. *Thanks Blazin912*
                self.log("Building LiveTV using tuner0")
                setting2 = re.sub(r'\d/tuner\d',"0/tuner0",setting2)
            elif setting2[0:9] == 'hdhomerun' and REAL_SETTINGS.getSetting('HdhomerunMaster') == "false":
                self.log("Building LiveTV using tuner1")
                setting2 = re.sub(r'\d/tuner\d',"1/tuner1",setting2) 
            fileList = self.buildLiveTVFileList(setting1, setting2, setting3, setting4, limit)
                
        # InternetTV  
        elif chtype == 9:
            self.log("Building InternetTV Channel, " + setting1 + " , " + setting2 + " , " + setting3)
            fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4, limit)

        # Youtube                          
        elif chtype == 10:
            setting2 = correctYoutubeSetting2(setting2)
            self.log("Building Youtube Channel " + setting1 + " using type " + setting2 + "...")
            
            if setting2 == '31':
                today = datetime.datetime.now()
                month = today.strftime('%B')
                if setting1.lower() != month.lower():
                    setting1 = month
                    ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", month)
            fileList = self.createYoutubeFilelist(setting1, setting2, setting3, setting4, limit)

        # RSS/iTunes/feedburner/Podcast   
        elif chtype == 11:
            self.log("Building RSS Feed " + setting1 + " using type " + setting2 + "...")
            fileList = self.createRSSFileList(setting1, setting2, setting3, setting4, limit)      
                
        # MusicVideos
        elif chtype == 13:
            self.log("Building Music Videos")
            fileList = self.MusicVideos(setting1, setting2, setting3, setting4, limit)    
            
        # Extras
        elif chtype == 14:
            self.log("Extras, " + setting1 + "...")
            fileList = self.Extras(setting1, setting2, setting3, setting4, channel, 6)     
            
        # Direct Plugin
        elif chtype == 15:
            self.log("Building Plugin Channel, " + setting1 + "...")
            fileList = self.buildPluginFileList(setting1, setting2, setting3, setting4, limit)    

        # Direct UPNP
        elif chtype == 16:
            self.log("Building UPNP Channel, " + setting1 + "...")
            fileList = self.buildUPNPFileList(setting1, setting2, setting3, setting4, limit)  
                
        # LocalTV
        else:
            if chtype == 0:
                if FileAccess.copy(setting1, MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                    if FileAccess.exists(MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                        self.log("Unable to copy or find playlist " + setting1)
                        return False

                fle = MADE_CHAN_LOC + os.path.split(setting1)[1]
            else:
                fle = self.makeTypePlaylist(chtype, setting1, setting2)
           
            if len(fle) == 0:
                self.log('Unable to locate the playlist for channel ' + str(channel), xbmc.LOGERROR)
                return False

            try:
                xml = FileAccess.open(fle, "r")
            except Exception,e:
                self.log("makeChannelList Unable to open the smart playlist " + fle, xbmc.LOGERROR)
                return False

            try:
                dom = parse(xml)
            except Exception,e:
                self.log('makeChannelList Problem parsing playlist ' + fle, xbmc.LOGERROR)
                xml.close()
                return False
            xml.close()

            if self.getSmartPlaylistType(dom) == 'mixed':
                bctType = 'mixed'
                fileList = self.buildMixedFileList(dom, channel, limit)
                
            elif self.getSmartPlaylistType(dom) == 'movies':
                bctType = 'movies'
                fileList = self.buildFileList(fle, channel, limit, 'video')
            
            elif self.getSmartPlaylistType(dom) in ['episodes','tvshow']:
                bctType = 'episodes'
                fileList = self.buildFileList(fle, channel, limit, 'video')
                
            elif self.getSmartPlaylistType(dom) in ['songs','albums','artists']:
                fileList = self.buildFileList(fle, channel, limit, 'music')
                
            else:
                fileList = self.buildFileList(fle, channel, limit, 'video')

            try:
                order = dom.getElementsByTagName('order')
                if order[0].childNodes[0].nodeValue.lower() == 'random' and self.channels[channel - 1].mode == 8:
                    israndom = True
            except Exception,e:
                pass
        
        try:
            if append == True:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "r")
                channelplaylist.seek(0, 2)
                channelplaylist.close()
            else:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "w")
        except Exception,e:
            self.log('Unable to open the cache file ' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)
            return False

        if append == False:
            #first queue m3u
            channelplaylist.write(uni("#EXTM3U\n"))
            
        if not fileList or len(fileList) == 0:  
            self.log("Unable to get information about channel " + str(channel), xbmc.LOGERROR)
            channelplaylist.close()
            return False
    
        if israndom:
            random.shuffle(fileList)
            msg = 'random' 
        elif isreverse:
            fileList.reverse()
            msg = 'reverse'
        self.log("makeChannelList, Using Media Sort " + msg)
        self.channels[channel - 1].isRandom = israndom
        self.channels[channel - 1].isReverse = isreverse
        
        if len(fileList) > self.Playlist_Limit:
            fileList = fileList[:self.Playlist_Limit]
        fileList = self.runActions(RULES_ACTION_LIST, channel, fileList)
        
        # inject BCT into filelist
        if self.incBCTs == True and bctType != None:
            fileList = self.insertBCT(chtype, channel, fileList, bctType)

        if append:
            if len(fileList) + self.channels[channel - 1].Playlist.size() > self.Playlist_Limit:
                fileList = fileList[:(self.Playlist_Limit - self.channels[channel - 1].Playlist.size())]
        else:
            if len(fileList) > self.Playlist_Limit:

                fileList = fileList[:self.Playlist_Limit]
                        
        if len(fileList) == 0:
            self.channels[channel - 1].isValid = False

        # Write each entry into the new playlist
        for string in fileList:
            channelplaylist.write(uni("#EXTINF:") + uni(string) + uni("\n"))
         
        # cleanup   
        del fileList[:]
        channelplaylist.close()
        self.log('makeChannelList return')
        return True

        
    def makeTypePlaylist(self, chtype, setting1, setting2):
        if chtype == 1:
            if len(self.networkList) == 0:
                self.fillTVInfo()
            return self.createNetworkPlaylist(setting1, setting2)
            
        elif chtype == 2:
            if len(self.studioList) == 0:
                self.fillMovieInfo()
            return self.createStudioPlaylist(setting1)
            
        elif chtype == 3:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()
            return self.createGenrePlaylist('episodes', chtype, setting1, setting2)
            
        elif chtype == 4:
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()
            return self.createGenrePlaylist('movies', chtype, setting1)
            
        elif chtype == 5:
            if len(self.mixedGenreList) == 0:
                if len(self.showGenreList) == 0:
                    self.fillTVInfo()

                if len(self.movieGenreList) == 0:
                    self.fillMovieInfo()

                self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
                self.mixedGenreList.sort(key=lambda x: x.lower())
            return self.createGenreMixedPlaylist(setting1, setting2)
            
        elif chtype == 6:
            if len(self.showList) == 0:
                self.fillTVInfo()
            return self.createShowPlaylist(setting1, setting2)
            
        elif chtype == 12:
            if len(self.musicGenreList) == 0:
                self.fillMusicInfo()
            return self.createGenrePlaylist('songs', chtype, setting1)
        self.log('makeTypePlaylists invalid channel type: ' + str(chtype))
        return ''    


    def writeXSPHeader(self, fle, pltype, plname, match='one'):
        fle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fle.write('<smartplaylist type="'+pltype+'">\n')
        fle.write('    <name>'+self.cleanString(plname)+'</name>\n')
        fle.write('    <match>'+match+'</match>\n')


    def writeXSPFooter(self, fle, limit, sort, order='ascending'):
        fle.write('    <limit>'+str(limit)+'</limit>\n')
        fle.write('    <order direction="'+order+'">'+sort+'</order>\n')
        fle.write('</smartplaylist>\n')
            
        
    def createNetworkPlaylist(self, network, setting2):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'network_' + '_' + network + '.xsp')

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "episodes", self.getChannelName(1, self.settingChannel, network))
        fle.write('    <rule field="studio" operator="is">\n')        
        fle.write('        <value>' + self.cleanString(network) + '</value>\n')
        fle.write('    </rule>\n')
        self.writeXSPFooter(fle, 0, "random")
        fle.close()
        return flename


    def createShowPlaylist(self, show, setting2):
        show = show.split('|')
        chname = ' & '.join(show)
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Show_' + chname + '.xsp')
        
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, 'episodes', self.getChannelName(6, self.settingChannel, chname))
        fle.write('    <rule field="tvshow" operator="is">\n')
        
        for i in range(len(show)):
            fle.write('        <value>' + self.cleanString((show[i])) + '</value>\n')
        fle.write('    </rule>\n')
        
        self.writeXSPFooter(fle, 0, "random")
        fle.close()
        return flename

    
    def fillMixedGenreInfo(self):
        if len(self.mixedGenreList) == 0:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()
            self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
            self.mixedGenreList.sort(key=lambda x: x.lower())


    def makeMixedList(self, list1, list2):
        self.log("makeMixedList")
        newlist = []
        
        for item in list1:
            curitem = item.lower()

            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break
        self.log("makeMixedList return " + str(newlist))
        return newlist

        
    def createGenreMixedPlaylist(self, genre, setting2):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'mixed_' + genre + '.xsp')
        
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''
        epname = os.path.basename(self.createGenrePlaylist('episodes', 3, genre, setting2))
        moname = os.path.basename(self.createGenrePlaylist('movies', 4, genre))
        self.writeXSPHeader(fle, 'mixed', self.getChannelName(5, self.settingChannel, genre))
        fle.write('    <rule field="playlist" operator="is">' + epname + '</rule>\n')
        fle.write('    <rule field="playlist" operator="is">' + moname + '</rule>\n')
        self.writeXSPFooter(fle, 0, "random")
        fle.close()
        return flename


    def createGenrePlaylist(self, pltype, chtype, genre, setting2=None):  
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + pltype + '_' + genre + '.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, pltype, self.getChannelName(chtype, self.settingChannel, genre))
        fle.write('    <rule field="genre" operator="is">\n')
        fle.write('        <value>' + self.cleanString(genre) + '</value>\n')
        fle.write('    </rule>\n')
        self.writeXSPFooter(fle, 0, "random")
        fle.close()
        return flename


    def createStudioPlaylist(self, studio):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Studio_' + studio + '.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "movies", self.getChannelName(2, self.settingChannel, studio))
        fle.write('    <rule field="studio" operator="is">\n')
        fle.write('        <value>' + self.cleanString(studio) + '</value>\n')
        fle.write('    </rule>\n')
        self.writeXSPFooter(fle, 0, "random")
        fle.close()
        return flename
        
        
    def createCinemaExperiencePlaylist(self):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'movies_CinemaExperience.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''
        
        self.writeXSPHeader(fle, "movies", 'PseudoCinema Experience', 'all')
        fle.write('    <rule field="videoresolution" operator="greaterthan">\n')
        fle.write('        <value>720</value>\n')
        fle.write('    </rule>\n')
        fle.write('    <rule field="playcount" operator="is">\n')
        fle.write('        <value>0</value>\n')
        fle.write('    </rule>\n')
        fle.write('    <group>none</group>\n')
        self.writeXSPFooter(fle, 0, "dateadded", "descending")
        fle.close()
        return flename
        
        
    def createRecentlyAddedTV(self):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'episodes_RecentlyAddedTV.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "episodes", 'Recently Added TV', 'all')
        self.writeXSPFooter(fle, 0, "dateadded", "descending")
        fle.close()
        return flename
        
    
    def createRecentlyAddedMovies(self):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'movies_RecentlyAddedMovies.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "movies", 'Recently Added Movies', 'all')
        self.writeXSPFooter(fle, 0, "dateadded", "descending")
        fle.close()
        return flename
        

    def createDirectoryPlaylist(self, setting1, setting3, setting4, limit):
        self.log("createDirectoryPlaylist")
        fileList = []
        LocalLST = []
        LocalFLE = ''
        filecount = 0 
        
        if not setting1.endswith('/'):
            setting1 = os.path.join(setting1,'')
        LocalLST = self.walk(setting1)
        
        for i in range(len(LocalLST)):         
            if self.threadPause() == False:
                del fileList[:]
                break
                
            LocalFLE = (LocalLST[i])
            duration = self.getDuration(LocalFLE)
                                                                
            if duration > 0:
                filecount += 1
                self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(filecount),inc=int(((filecount) // limit) // self.enteredChannelCount))
                title = (os.path.split(LocalFLE)[1])
                title = os.path.splitext(title)[0].replace('.', ' ')
                description = LocalFLE.replace('//','/').replace('/','\\')
                GenreLiveID = ['Unknown', 'other', 0, 0, False, 1, 'NR', False, False, 0.0, 0]
                tmpstr = self.makeTMPSTR(duration, title, 0, 'Directory Video', description, GenreLiveID, LocalFLE)
                fileList.append(tmpstr)
                    
                if filecount >= limit:
                    break
                    
        if filecount == 0:
            self.log('Unable to access Videos files in ' + setting1)
            
        # cleanup   
        del LocalLST[:]
        return fileList

        
    def BuildCinemaExperienceFileList(self, setting1, setting2, setting3, setting4, channel, PrefileList):
        self.log("BuildCinemaExperienceFileList")
        GenreLiveID = ['Movie', 'movie', 0, 0, False, 1, 'NR', False, False, 0.0, 0]
        fileList = []
        fleList = []
        TrailersStrLST = []
        TrailersLST = []
        TrailerCount = 0
        showcount = 0
        
        if self.youtube_player != 'False':
            self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="Populating the PseudoCinema Experience")
            
            for f in self.requestList(setting2):
                if self.threadPause() == False:
                    del fileList[:]
                    break
                try:
                    files = re.search('"file" *: *"(.*?)",', f)
                    labels = re.search('"label" *: *"(.*?)",', f)
                    plots = re.search('"plot" *: *"(.*?)",', f)
                    file = (files.group(1)).replace(self.youtube_player,'')
                    label = labels.group(1)
                    plot = plots.group(1)
                    
                    if plot == 'CE_INTRO':
                        Intro = file
                    elif plot == 'CE_CELL':
                        Cellphone = file
                    elif plot == 'CE_COMING_SOON':
                        ComingSoon = file
                    elif plot == 'CE_PREMOVIE':
                        PreMovie = file
                    elif plot == 'CE_FEATURE_PRESENTATION':
                        FeaturePres = file
                    elif plot == 'CE_INTERMISSION':
                        Intermission = file 
                except:
                    pass
                 
            #Parse Trailers
            TrailerLST1 = self.InternetTrailer(1)
            TrailerLST2 = self.InternetTrailer(2)
            #Mix/Shuffle Trailers
            if TrailerLST1 and len(TrailerLST1) > 0:
                random.shuffle(TrailerLST1)
            if TrailerLST2 and len(TrailerLST2) > 0:
                random.shuffle(TrailerLST2)
            TrailerLST = TrailerLST1 + TrailerLST2
            random.shuffle(TrailerLST)

            #Ratings
            fleList = self.getRatingList(14, 'PseudoCinema', channel, PrefileList)
            #Intro
            IntroStr = self.makeTMPSTR(self.getYoutubeDuration(Intro), 'PseudoCinema', 0, 'Intro', 'Welcome to the PseudoCinema Experience', GenreLiveID, self.youtube_player + Intro, includeMeta=False)
            #Cellphone
            CellphoneStr = self.makeTMPSTR(self.getYoutubeDuration(Cellphone), 'PseudoCinema', 0, 'Cellphone', 'Welcome to the PseudoCinema Experience', GenreLiveID, self.youtube_player + Cellphone, includeMeta=False)
            #Comingsoon
            ComingSoonStr = self.makeTMPSTR(self.getYoutubeDuration(ComingSoon), 'PseudoCinema', 0, 'Coming Soon', 'Welcome to the PseudoCinema Experience', GenreLiveID, self.youtube_player + ComingSoon, includeMeta=False)
            #PreMovie
            PreMovieStr = self.makeTMPSTR(self.getYoutubeDuration(PreMovie), 'PseudoCinema', 0, 'PreMovie', 'Welcome to the PseudoCinema Experience', GenreLiveID, self.youtube_player + PreMovie, includeMeta=False)
            #FeaturePresentation
            FeaturePresStr = self.makeTMPSTR(self.getYoutubeDuration(FeaturePres), 'PseudoCinema', 0, 'Feature Presentation', 'Welcome to the PseudoCinema Experience', GenreLiveID, self.youtube_player + FeaturePres, includeMeta=False)
            #Intermission
            IntermissionStr = self.makeTMPSTR(self.getYoutubeDuration(Intermission), 'PseudoCinema', 0, 'Intermission', 'Welcome to the PseudoCinema Experience: Next Movie will begin in 10 Minutes//Intermission', GenreLiveID, self.youtube_player + Intermission, includeMeta=False)

            for n in range(len(fleList)):         
                if self.threadPause() == False:
                    del fileList[:]
                    break
                line = fleList[n]
                fileList.append(line)
                fileList.append(IntermissionStr)
                showcount += 1
                self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="Populating the PseudoCinema Experience, Preparing %s Movies" % str(showcount))

            for i in range(len(TrailerLST)):         
                if self.threadPause() == False:
                    del fileList[:]
                    break
                aTrailer = TrailerLST[i]
                dur = aTrailer.split(',')[0]
                file = aTrailer.split(',')[1]
                file = file.replace('plugin://plugin.video.youtube/?action=play_video&videoid=', self.youtube_player)
                TrailersStrLST.append(self.makeTMPSTR(str(dur), 'PseudoCinema', 0, 'Trailer', 'Welcome to the PseudoCinema Experience', GenreLiveID, file, includeMeta=False))
                TrailerCount += 1
                
                # Only add two trailers
                if TrailerCount > 4:
                    break

            PreShowLST = [IntroStr, CellphoneStr, ComingSoonStr]
            PreMovieLST = [PreMovieStr, FeaturePresStr]
            PreShowLST.extend(TrailersStrLST)
            PreShowLST.extend(PreMovieLST)
            PreShowLST.extend(fileList)
            
        # cleanup   
        del fileList[:]
        del fleList[:]
        del TrailersStrLST[:]
        del TrailersLST[:]
        return PreShowLST

    
    def Extras(self, setting1, setting2, setting3, setting4, channel, limit):
        self.log("Extras")
        showList = []
        if setting1.lower() == 'cinema': 
            showList = self.BuildCinemaExperienceFileList(setting1, setting2, setting3, setting4, channel, self.buildFileList(self.createCinemaExperiencePlaylist(), channel, limit))
        return showList
        
        
    # pack string for playlist
    def packGenreLiveID(self, GenreLiveID):
        self.log("packGenreLiveID, GenreLiveID = " + str(GenreLiveID))
        genre = GenreLiveID[0]
        LiveID = '|'.join(str(x) for x in GenreLiveID[1:])
        return genre, LiveID

        
    # unpack list for parsing
    def unpackLiveID(self, LiveID):
        self.log("unpackLiveID, LiveID = " + LiveID)
        try:
            # test unpack, return list, except return default
            type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = LiveID.split('|')
            LiveID = LiveID.split('|')
        except:
            LiveID = ['other',0,0,False,1,'NR',False, False, 0.0, 0]
        return LiveID
    
    
    def makeTMPSTR(self, duration, Stitle, year, SEtitle, description, GenreLiveID, file, timestamp=None, includeMeta=True):
        self.log("makeTMPSTR, includeMeta = " + str(includeMeta))
        chtype = self.getChtype(self.settingChannel)
        genre, LiveID = self.packGenreLiveID(GenreLiveID)
        type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = self.unpackLiveID(LiveID)
        Stitle = self.cleanLabels(Stitle)
        SEtitle = self.cleanLabels(SEtitle)
        year, title, showtitle = getTitleYear(Stitle, year)
        
        # use youtube vdid for dbid
        if file.startswith(self.youtube_player):
            dbepid = file.split(self.youtube_player)[1]
            # if no id, default to youtube type.
            if id == '0':
                type = 'youtube'
                
        if type in ['tvshow','episode']:
            if includeMeta == True:
                stars, year, duration, description, Stitle, SEtitle, id, genre, rating, playcount = self.getTVmeta(stars, year, duration, description, title, SEtitle, id, genre, rating, playcount)
        elif type == 'movie':
            if includeMeta == True:
                stars, year, duration, description, Stitle, subtitle, id, genre, rating, playcount = self.getMovieMeta(stars, year, duration, description, title, SEtitle, id, genre, rating, playcount)
        elif type == 'youtube':
            if includeMeta == True:
                stars, year, duration, description, Stitle, SEtitle, dbepid, genre, rating, playcount, hd, cc = self.getYoutubeMeta(stars, year, duration, description, title, SEtitle, dbepid, genre, rating, playcount, hd, cc)
        elif type == 'vimeo':
            if includeMeta == True:
                Stitle, description, duration, dbid = self.getVimeoMeta(id)
                
        Stitle = self.cleanLabels(Stitle)
        SEtitle = self.cleanLabels(SEtitle)
        year, title, showtitle = getTitleYear(Stitle, year)           
        
        if type == 'movie':
            Stitle = showtitle
        else:
            Stitle = title
                 
        description = self.cleanLabels(description)
        genre = self.cleanLabels(genre)
        rating = self.cleanRating(rating)
        file = self.cleanPlayableFile(file)
        
        GenreLiveID = [genre,type,id,dbepid,managed,playcount,rating,hd,cc,stars,year]
        genre, LiveID = self.packGenreLiveID(GenreLiveID)

        if not timestamp:
            timestamp = datetime.datetime.now()
        timestamp = str(timestamp).split('.')[0]

        try:
            Stitle = (trim(Stitle, 350, ''))
        except Exception,e:
            self.log("Stitle Trim failed! " + str(e))
            Stitle = (Stitle[:350])
        try:
            SEtitle = (trim(SEtitle, 350, ''))
        except Exception,e:
            self.log("SEtitle Trim failed! " + str(e))
            SEtitle = (SEtitle[:350])
        try:
            description = (trim(description, 350, '...'))
        except Exception,e:
            self.log("description Trim failed! " + str(e))
            description = (description[:350])  
            
        if chtype == 8:
            description = description + ' ' + timestamp
        tmpstr = str(duration) + ',' + Stitle + "//" + SEtitle + "//" + description + "//" + genre + "//" + timestamp + "//" + LiveID + '\n' + file
        tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")                  
        return tmpstr

        
    def cleanPlayableFile(self, file):
        self.log('cleanPlayableFile')
        if self.youtube_player != 'False':
            file = file.replace('http://www.youtube.com/watch?v=', self.youtube_player)
            file = file.replace('https://www.youtube.com/watch?v=', self.youtube_player)
            file = file.replace('plugin://plugin.video.bromix.youtube/play/?video_id=', self.youtube_player)
            file = file.replace('plugin://plugin.video.youtube/?action=play_video&videoid=', self.youtube_player)
        file = file.replace("\\\\", "\\")
        return file
        

    def cleanString(self, string):
        self.log("cleanString")
        newstr = uni(string)
        newstr = newstr.replace('&', '&amp;')
        newstr = newstr.replace('>', '&gt;')
        newstr = newstr.replace('<', '&lt;')
        newstr = newstr.replace('"', '&quot;')
        return uni(newstr)

    
    def uncleanString(self, string):
        self.log("uncleanString")
        newstr = uni(string)
        newstr = newstr.replace('&amp;', '&')
        newstr = newstr.replace('&gt;', '>')
        newstr = newstr.replace('&lt;', '<')
        newstr = newstr.replace('&quot;', '"')
        return uni(newstr)
              
              
    def cleanLabels(self, text, format=''):
        self.log('cleanLabels, IN = ' + text)
        text = uni(text)
        text = re.sub('\[COLOR (.+?)\]', '', text)
        text = re.sub('\[/COLOR\]', '', text)
        text = re.sub('\[COLOR=(.+?)\]', '', text)
        text = re.sub('\[color (.+?)\]', '', text)
        text = re.sub('\[/color\]', '', text)
        text = re.sub('\[Color=(.+?)\]', '', text)
        text = re.sub('\[/Color\]', '', text)
        text = text.replace("[]",'')
        text = text.replace("[UPPERCASE]",'')
        text = text.replace("[/UPPERCASE]",'')
        text = text.replace("[LOWERCASE]",'')
        text = text.replace("[/LOWERCASE]",'')
        text = text.replace("[B]",'')
        text = text.replace("[/B]",'')
        text = text.replace("[I]",'')
        text = text.replace("[/I]",'')
        text = text.replace('[D]','')
        text = text.replace('[F]','')
        text = text.replace("[CR]",'')
        text = text.replace("[HD]",'')
        text = text.replace("()",'')
        text = text.replace("[CC]",'')
        text = text.replace("[Cc]",'')
        text = text.replace("[Favorite]", "")
        text = text.replace("[DRM]", "")
        text = text.replace('(cc).','')
        text = text.replace('(n)','')
        text = text.replace("(SUB)",'')
        text = text.replace("(DUB)",'')
        text = text.replace('(repeat)','')
        text = text.replace("(English Subtitled)", "")    
        text = text.replace("*", "")
        text = text.replace("\n", "")
        text = text.replace("\r", "")
        text = text.replace("\t", "")
        text = text.replace("/",'')
        text = text.replace("\ ",'')
        text = text.replace("/ ",'')
        text = text.replace("\\",'/')
        text = text.replace("//",'/')
        text = text.replace('/"','')
        text = text.replace('*NEW*','')
        text = text.replace('plugin.video.','')
        text = text.replace('plugin.audio.','')

        if format == 'title':
            text = text.title().replace("'S","'s")
        elif format == 'upper':
            text = text.upper()
        elif format == 'lower':
            text = text.lower()
        else:
            text = text
            
        text = self.uncleanString(text.strip())
        self.log('cleanLabels, OUT = ' + text)
        return text
    
    
    def cleanRating(self, rating):
        self.log("cleanRating")
        rating = uni(rating)
        rating = self.cleanLabels(rating,'upper')
        rating = rating.replace('RATED ','')
        rating = rating.replace('US:','')
        rating = rating.replace('UK:','')
        rating = rating.replace('UNRATED','NR')
        rating = rating.replace('NOTRATED','NR')
        rating = rating.replace('UNKNOWN','NR')
        rating = rating.replace('N/A','NR')
        rating = rating.replace('NA','NR')
        rating = rating.replace('APPROVED','NR')
        rating = rating.replace('NOT RATED','NR')
        rating = rating.replace('PASSE','NR')
        rating = rating.replace('NRD','NR')
        rating = rating.split(' ')[0]
        return uni(rating[0:5])

        
    def fillMusicInfo(self, sortbycount = False):
        self.log("fillMusicInfo")
        self.musicGenreList = []
        json_query = ('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties":["genre"]}, "id": 1}')
        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.musicGenreList[:]
                return

            match = re.search('"genre" *: *\[(.*?)\]', f)
          
            if match:
                genres = match.group(1).split(',')
               
                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.musicGenreList)):
                        if self.threadPause() == False:
                            del self.musicGenreList[:]
                            return
                            
                        itm = self.musicGenreList[g]
                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True
                            if sortbycount:
                                self.musicGenreList[g][1] += 1
                            break

                    if found == False:
                        if sortbycount:
                            self.musicGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.musicGenreList.append(genre.strip('"').strip())
    
        if sortbycount:
            self.musicGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.musicGenreList.sort(key=lambda x: x.lower())
        self.log("found genres " + str(self.musicGenreList))
     
    
    def fillTVInfo(self, sortbycount = False):
        self.log("fillTVInfo")
        json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties":["studio", "genre"]}, "id": 1}')
        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.networkList[:]
                del self.showList[:]
                del self.showGenreList[:]
                return

            match = re.search('"studio" *: *\[(.*?)\]', f)
            network = ''

            if match:
                network = (match.group(1).split(','))[0]
                network = (network.strip('"').strip())
                found = False

                for item in range(len(self.networkList)):
                    if self.threadPause() == False:
                        del self.networkList[:]
                        del self.showList[:]
                        del self.showGenreList[:]
                        return

                    itm = self.networkList[item]

                    if sortbycount:
                        itm = itm[0]

                    if itm.lower() == network.lower():
                        found = True

                        if sortbycount:
                            self.networkList[item][1] += 1

                        break

                if found == False and len(network) > 0:
                    if sortbycount:
                        self.networkList.append([network, 1])
                    else:
                        self.networkList.append(network)

            match = re.search('"label" *: *"(.*?)",', f)

            if match:
                show = (match.group(1).strip())
                self.showList.append([show, network])
                
            match = re.search('"genre" *: *\[(.*?)\]', f)

            if match:
                genres = (match.group(1).split(','))
                
                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.showGenreList)):
                        if self.threadPause() == False:
                            del self.networkList[:]
                            del self.showList[:]
                            del self.showGenreList[:]
                            return

                        itm = self.showGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.showGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.showGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.showGenreList.append(genre.strip('"').strip())

        if sortbycount:
            self.networkList.sort(key=lambda x: x[1], reverse = True)
            self.showGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.networkList.sort(key=lambda x: x.lower())
            self.showGenreList.sort(key=lambda x: x.lower())

        if (len(self.showList) == 0) and (len(self.showGenreList) == 0) and (len(self.networkList) == 0):
            self.log(json_folder_detail)

        self.log("found shows " + str(self.showList))
        self.log("found genres " + str(self.showGenreList))
        self.log("fillTVInfo return " + str(self.networkList))


    def fillMovieInfo(self, sortbycount = False):
        self.log("fillMovieInfo")
        studioList = []
        json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties":["studio", "genre"]}, "id": 1}')
        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.movieGenreList[:]
                del self.studioList[:]
                del studioList[:]
                break

            match = re.search('"genre" *: *\[(.*?)\]', f)

            if match:
                genres = match.group(1).split(',')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.movieGenreList)):
                        itm = self.movieGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.movieGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.movieGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.movieGenreList.append(genre.strip('"').strip())

            match = re.search('"studio" *: *\[(.*?)\]', f)
           
            if match:
                studios = match.group(1).split(',')
                
                for studio in studios:
                    curstudio = studio.strip('"').strip()
                    found = False

                    for i in range(len(studioList)):
                        if studioList[i][0].lower() == curstudio.lower():
                            studioList[i][1] += 1
                            found = True
                            break

                    if found == False and len(curstudio) > 0:
                        studioList.append([curstudio, 1])

        maxcount = 0

        for i in range(len(studioList)):
            if studioList[i][1] > maxcount:
                maxcount = studioList[i][1]

        bestmatch = 1
        lastmatch = 1000
        counteditems = 0

        for i in range(maxcount, 0, -1):
            itemcount = 0

            for j in range(len(studioList)):
                if studioList[j][1] == i:
                    itemcount += 1

            if abs(itemcount + counteditems - 8) < abs(lastmatch - 8):
                bestmatch = i
                lastmatch = itemcount

            counteditems += itemcount

        if sortbycount:
            studioList.sort(key=lambda x: x[1], reverse=True)
            self.movieGenreList.sort(key=lambda x: x[1], reverse=True)
        else:
            studioList.sort(key=lambda x: x[0].lower())
            self.movieGenreList.sort(key=lambda x: x.lower())

        for i in range(len(studioList)):
            if studioList[i][1] >= bestmatch:
                if sortbycount:
                    self.studioList.append([studioList[i][0], studioList[i][1]])
                else:
                    self.studioList.append(studioList[i][0])

        if (len(self.movieGenreList) == 0) and (len(self.studioList) == 0):
            self.log(json_folder_detail)

        self.movieGenreList = (self.movieGenreList)
        self.studioList = (self.studioList)
        
        self.log("found genres " + str(self.movieGenreList))
        self.log("fillMovieInfo return " + str(self.studioList))

        
    # replace with json request info todo
    def isMedia3D(self, path):
        Media3D = False
        # if self.inc3D == True:
            # FILTER_3D = ['3d','sbs','fsbs','ftab','hsbs','h.sbs','h-sbs','htab','sbs3d','3dbd','halfsbs','half.sbs','half-sbs','fullsbs','full.sbs','full-sbs','3dsbs','3d.sbs']
            # for i in range(len(FILTER_3D)):
                # if FILTER_3D[i] in path.lower():   
                    # Media3D = True  
        self.log("isMedia3D = " + str(Media3D))                      
        return Media3D
          

    def buildFileList(self, dir_name, channel, limit, fletype = 'video'):
        self.log("buildFileList")
        self.dircount = 0
        self.filecount = 0
        fileList = []
        self.file_detail_CHK = []
        self.startDate = self.startTime
        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2=" querying Kodi database")
        fileList = self.getFileList(self.requestList(dir_name, fletype), channel, limit)
        self.log("buildFileList return")
        return fileList
  
  
    def buildPluginFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log('buildPluginFileList')
        self.dircount = 0
        self.filecount = 0
        fileList = []  
        self.file_detail_CHK = []
        self.startDate = self.startTime
        
        if setting1.endswith('/'):
            setting1 = setting1[:-1]
            
        PluginPath = (setting1.replace('plugin://','')).split('/')[0]
        PluginName = (xbmcaddon.Addon(id=PluginPath)).getAddonInfo('name')
        
        try:
            excludeLST = setting2.split(',')
        except:
            excludeLST = []

        excludeLST += EX_FILTER
        excludeLST = removeStringElem(excludeLST)
        self.log('buildPluginFileList, excludeLST = ' + str(excludeLST))
        fileList = self.getFileList(self.requestList(setting1), self.settingChannel, limit, excludeLST)
        self.log("buildPluginFileList return")
        return fileList
        
        
    def buildUPNPFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log('buildUPNPFileList')
        Directs = ''
        self.dircount = 0
        self.filecount = 0
        fileList = []  
        self.file_detail_CHK = []
        
        if setting1.endswith('/'):
            setting1 = setting1[:-1]
                    
        try:
            excludeLST = setting2.split(',')
        except:
            excludeLST = []
  
        excludeLST += EX_FILTER
        excludeLST = removeStringElem(excludeLST)
        self.log('buildUPNPFileList, excludeLST = ' + str(excludeLST))
        fileList = self.getFileList(self.requestList(setting1), self.settingChannel, limit, excludeLST)
        self.log("buildUPNPFileList return")
        return fileList

        
    def buildMixedFileList(self, dom1, channel, limit):
        self.log('buildMixedFileList')
        fileList = []
        try:
            rules = dom1.getElementsByTagName('rule')
            order = dom1.getElementsByTagName('order')
        except Exception,e:
            self.log('buildMixedFileList Problem parsing playlist ' + filename, xbmc.LOGERROR)
            xml.close()
            
            return fileList

        for rule in rules:
            rulename = rule.childNodes[0].nodeValue

            if FileAccess.exists(xbmc.translatePath('special://profile/playlists/video/') + rulename):
                FileAccess.copy(xbmc.translatePath('special://profile/playlists/video/') + rulename, MADE_CHAN_LOC + rulename)
                fileList.extend(self.buildFileList(MADE_CHAN_LOC + rulename, channel, limit))
            else:
                fileList.extend(self.buildFileList(GEN_CHAN_LOC + rulename, channel, limit))

        self.log("buildMixedFileList returning")
        return fileList

        
    # *Thanks sphere, adapted from plugin.video.ted.talks
    # People still using Python <2.7 201303 :(
    def __total_seconds__(self, delta):
        try:
            return delta.total_seconds()
        except AttributeError:
            return int((delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10 ** 6)) / 10 ** 6

            
    def parsePVRDate(self, dateString):
        self.log("parsePVRDate") 
        if dateString is not None:
            t = time.strptime(dateString, '%Y-%m-%d %H:%M:%S')
            tmpDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
            timestamp = calendar.timegm(tmpDate.timetuple())
            local_dt = datetime.datetime.fromtimestamp(timestamp)
            assert tmpDate.resolution >= timedelta(microseconds=1)
            return local_dt.replace(microsecond=tmpDate.microsecond) 
        else:
            return None
   
   
    def parseUTCXMLTVDate(self, dateString):
        self.log("parseUTCXMLTVDate") 
        if dateString is not None:
            try:
                if dateString.find(' ') != -1:
                    # remove timezone information
                    dateString = dateString[:dateString.find(' ')]
            except:
                pass
            t = time.strptime(dateString, '%Y%m%d%H%M%S')
            tmpDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
            timestamp = calendar.timegm(tmpDate.timetuple())
            local_dt = datetime.datetime.fromtimestamp(timestamp)
            assert tmpDate.resolution >= timedelta(microseconds=1)
            return local_dt.replace(microsecond=tmpDate.microsecond) 
        else:
            return None
       
       
    def parseXMLTVDate(self, dateString, offset=0):
        self.log("parseXMLTVDate") 
        if dateString is not None:
            try:
                if dateString.find(' ') != -1:
                    # remove timezone information
                    dateString = dateString[:dateString.find(' ')]
            except:
                pass
            t = time.strptime(dateString, '%Y%m%d%H%M%S')
            d = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
            d += datetime.timedelta(hours = offset)
            return d
        else:
            return None
            
            
    def buildLiveTVFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log("buildLiveTVFileList")  
        showList = []
        # Validate XMLTV Data #
        if self.xmltv_ok(setting3) == True:
            chname = (self.getChannelName(8, self.settingChannel, setting1))
            if setting3.startswith('http://mobilelistings.tvguide.com'):
                showList = self.fillLiveTVGuide(setting1, setting2, setting3, setting4, chname, limit)
            elif setting3 == 'pvr':
                showList = self.fillLiveTVPVR(setting1, setting2, setting3, setting4, chname, limit)
            elif setting3 == 'hdhomerun':
                showList = self.fillLiveHDHRGuide(setting1, setting2, setting3, setting4, chname, limit)
            elif setting3 == 'ustvnow':
                showList = self.fillLiveUSTVGuide(setting1, setting2, setting3, setting4, chname, limit)
            else:   
                showList = self.fillLiveTVXMLTV(setting1, setting2, setting3, setting4, chname, limit)

        if len(showList) == 0:
            self.setChannelChanged(self.settingChannel)
            desc = 'Guidedata from ' + str(setting3) + ' currently unavailable, please verify channel configuration.'
            showList = self.buildInternetTVFileList('5400', setting2, self.getChannelName(9, self.settingChannel, setting1), desc, 24)
        # elif len(showList) < LIVETV_MAXPARSE:
            # self.setChannelChanged(self.settingChannel)
        return showList     
        
                
    def fillLiveUSTVGuide(self, setting1, setting2, setting3, setting4, chname, limit): 
        showList = []
        showcount = 0        
        try:
            listing = 'http://m-api.ustvnow.com/gtv/1/live/channelguide'
            self.log("fillLiveUSTVGuide, listing = " + listing)  
            a = json.loads(getRequest(listing))
            for b in a['results']: 
                if self.threadPause() == False:
                    del showList[:]
                    break
                              
                if showcount > limit:
                    break
                    
                dur = 0
                now = datetime.datetime.now()         
                offset = ((time.timezone / 3600) - 5 ) * -1
                
                if b['stream_code'].lower() == setting1.lower():
                    startDate  = datetime.datetime.fromtimestamp(float(b['ut_start']));
                    stopDate   = startDate + datetime.timedelta(seconds=int(b['guideremainingtime']));
        
                    #skip old shows that have already ended
                    if now > stopDate:
                        continue
                          
                    #adjust the duration of the current show
                    if now >= startDate and now <= stopDate:   
                        dur = b['guideremainingtime']
                    
                    #use the full duration for an upcoming show
                    if now < startDate:
                        dur = b['guideremainingtime']
                        
                    if dur > 0:
                        try:
                            dbid = encodeString('http://mc.ustvnow.com/gtv/1/live/viewposter?srsid=' + str(b['srsid']) + '&cs=' + b['callsign'] + '&tid=' + b['mediatype'])
                        except:
                            dbid = 0
                        try:
                            epid = b['scheduleid']
                        except:
                            epid = 0
                        try:
                            genre = b['xcdrappname']
                        except:
                            genre = 'Unknown'

                        title = b['title']
                        subtitle = b['episode_title']
                        description = b['description']
                        synopsis = b['synopsis']
                        if not subtitle:                        
                            subtitle = 'USTVnow'
                        if not description:
                            if not subtitle:
                                description = title  
                            else:
                                description = subtitle
                        try:
                            labelseasonepval = re.findall(r"(?:s|season)(\d{2})(?:e|x|episode|\n)(\d{2})", subtitle.lower(), re.I)
                            seasonNumber = int(labelseasonepval[0][0])
                            episodeNumber = int(labelseasonepval[0][1])
                        except Exception,e:
                            seasonNumber = 0
                            episodeNumber = 0

                        year, title, showtitle = getTitleYear(title) 
                        
                        if dur > 3600:
                            type = 'movie'
                        else:
                            type = 'tvshow'
                  
                        if type == 'tvshow':
                            showtitle = title
                            episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ (subtitle)).replace('  ',' ')
                            if str(episodetitle[0:5]) == '00x00':
                                episodetitle = episodetitle.split("- ", 1)[-1]
                            subtitle = episodetitle
                        
                        #Enable Enhanced Parsing for current and future shows only
                        includeMeta = self.includeMeta
                        if (title.lower() == 'paid programing' or subtitle.lower() == 'paid programing' or description.lower() == 'paid programing'):
                            includeMeta = False  
                            
                        dbid = str(dbid) +':'+ str(epid)
                        GenreLiveID = [genre,type,0,dbid,False,1,'NR', False, False, 0.0, year]
                        tmpstr = self.makeTMPSTR(dur, showtitle, year, subtitle, description, GenreLiveID, setting2, startDate, includeMeta)
                        showList.append(tmpstr)
                        showcount += dur
                        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(showcount/60/60),inc=int(((showcount/60/60) // limit) // self.enteredChannelCount))
        except Exception,e:
            self.log("fillLiveUSTVGuide failed! " + str(e), xbmc.LOGERROR)               
        return showList
        
    #todo move all hrhr to apis/pyHDHR
    def fillLiveHDHRGuide(self, setting1, setting2, setting3, setting4, chname, limit):
        self.log("fillLiveHDHRGuide")    
        showList = []
        showcount = 0  
        now = datetime.datetime.now()         
        offset = ((time.timezone / 3600) - 5 ) * -1          
        try:
            listing = 'http://my.hdhomerun.com/api/guide.php?DeviceAuth=%s' %hdhr.authID()
            self.log("fillLiveHDHRGuide, listing = " + listing)  
            a = json.loads(getRequest(listing))
            for b in a:
                if self.threadPause() == False:
                    del showList[:]
                    break
                              
                if showcount > limit:
                    break
   
                chid = str(b['GuideNumber'])
                if chid == setting1:
                    self.log("fillLiveHDHRGuide, "+chid+" == "+setting1)    
                    try:
                        if b['ImageURL'].startswith('http'):
                            GrabLogo(b['ImageURL'],chname)
                    except:
                        pass
                    try:
                        name  = b['Affiliate']
                    except:
                        name = b['GuideName']
                    rating = 'NR' 
                    for i in b['Guide']:     
                        dur = 0
                        stopDate = datetime.datetime.fromtimestamp(float(i['EndTime']))
                        startDate= datetime.datetime.fromtimestamp(float(i['StartTime']))

                        #skip old shows that have already ended
                        if now > stopDate:
                            continue

                        #adjust the duration of the current show
                        if now >= startDate and now <= stopDate:
                            dur = (stopDate - startDate).seconds
                        
                        #use the full duration for an upcoming show
                        if now < startDate:
                            dur = (stopDate - startDate).seconds
         
                        if dur > 0:
                            title = i['Title']
                            try:
                                dbid = encodeString(i['ImageURL'])
                            except:
                                dbid = 0
                            try:
                                epid = i['SeriesID']
                            except:
                                epid = 0
                            try:
                                description = i['Synopsis']
                            except:
                                description = ''
                            try:
                                genre = list(i['Filter'])[0]
                            except:
                                genre = 'Unknown'
                            try:
                                EpisodeNumber  = i['EpisodeNumber']
                            except:
                                EpisodeNumber = 'S00E00'
                            try:
                                subtitle  = i['EpisodeTitle']
                            except:
                                subtitle = ''
                                
                            if not subtitle:                        
                                subtitle = 'HDHomerun'
                            if not description:
                                if not subtitle:
                                    description = title  
                                else:
                                    description = subtitle
                            try:
                                labelseasonepval = re.findall(r"(?:s|season)(\d{2})(?:e|x|episode|\n)(\d{2})", EpisodeNumber.lower(), re.I)
                                seasonNumber = int(labelseasonepval[0][0])
                                episodeNumber = int(labelseasonepval[0][1])
                            except Exception,e:
                                seasonNumber = 0
                                episodeNumber = 0

                            year, title, showtitle = getTitleYear(title) 
                            if dur > 3600:
                                type = 'movie'
                            else:
                                type = 'tvshow'
                      
                            if type == 'tvshow':
                                showtitle = title
                                episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ (subtitle)).replace('  ',' ')
                                if str(episodetitle[0:5]) == '00x00':
                                    episodetitle = episodetitle.split("- ", 1)[-1]
                                subtitle = episodetitle
                            
                            #Enable Enhanced Parsing for current and future shows only
                            includeMeta = self.includeMeta
                            if (title.lower() == 'paid programing' or subtitle.lower() == 'paid programing' or description.lower() == 'paid programing'):
                                includeMeta = False  
                                
                            dbid = str(dbid) +':'+ str(epid)
                            GenreLiveID = [genre,type,0,dbid,False,1,rating, False, False, 0.0, year]
                            tmpstr = self.makeTMPSTR(dur, showtitle, year, subtitle, description, GenreLiveID, setting2, startDate, includeMeta)
                            showList.append(tmpstr)
                            showcount += dur
                            self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(showcount/60/60),inc=int(((showcount/60/60) // limit) // self.enteredChannelCount))
        except Exception,e:
            self.log("fillLiveHDHRGuide failed! " + str(e), xbmc.LOGERROR)               
        return showList
        

    def fillLiveTVGuide(self, setting1, setting2, setting3, setting4, chname, limit):
        self.log("fillLiveTVGuide")    
        showList = []
        showcount = 0  
        try:
            # html = getRequest('http://comettv.com/watch-live/')
            # url = re.compile('file: "(.+?)"', re.DOTALL).search(html).group(1)

            now = datetime.datetime.now()                  
            d = datetime.datetime.utcnow()
            dnow = calendar.timegm(d.utctimetuple())
            #example setting3 = 'http://mobilelistings.tvguide.com/Listingsweb/ws/rest/airings/20405/start/1464292664/duration/20160?channelsourceids=74313%7C62.4&formattype=json'
            listing = setting3.split('/start/')[0] + '/start/' + str(dnow) + '/duration/' + setting3.split('/duration/')[1]   
            self.log("fillLiveTVGuide, listing = " + listing)                    

            a = json.loads(getRequest(listing))
            for b in a:
                if self.threadPause() == False:
                    del showList[:]
                    break
                              
                if showcount > limit:
                    break
   
                subtitle = ''
                type = 'tvshow'
                b = b['ProgramSchedule']    
                Stitle = b['Title']      
                subtitle = b['EpisodeTitle']
                stopDate = datetime.datetime.fromtimestamp(float(b['EndTime']))
                startDate = datetime.datetime.fromtimestamp(float(b['StartTime'])) 
                
                #skip old shows that have already ended
                if now > stopDate:
                    continue
       
                #adjust the duration of the current show
                if now >= startDate and now <= stopDate:
                    dur = ((stopDate - startDate).seconds) 
                
                #use the full duration for an upcoming show
                if now < startDate:
                    dur = ((stopDate - startDate).seconds) 

                if dur > 0:
                    if subtitle != '':  
                        try:
                            seasonNumber = b['TVObject'].get('SeasonNumber')
                            seasonNumber = int(seasonNumber)
                        except:
                            seasonNumber = 0
                        try:
                            episodeNumber = b['TVObject']['EpisodeNumber']
                            episodeNumber = int(episodeNumber)
                        except:
                            episodeNumber = 0
                            
                            episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ (subtitle)).replace('  ',' ')
                            if str(episodetitle[0:5]) == '00x00':
                                episodetitle = episodetitle.split("- ", 1)[-1]
                            subtitle = episodetitle
                    else:
                        subtitle = 'LiveTV'
                        if dur > 3600:
                            type = 'movie'
                        
                    description = (b['CopyText'] or Stitle)
                    rating = (b.get('Rating').split('@')[0] or 'NR')                 
                    year, title, showtitle = getTitleYear(Stitle, 0) 
                    
                    #Enable Enhanced Parsing for current and future shows only
                    includeMeta = self.includeMeta
                    if (showtitle.lower() == 'paid programing' or subtitle.lower() == 'paid programing' or description.lower() == 'paid programing'):
                        includeMeta = False  
                    
                    GenreLiveID = ['Unknown',type,0,0,False,1,rating, False, False, 0.0, year]
                    tmpstr = self.makeTMPSTR(dur, showtitle, year, subtitle, description, GenreLiveID, setting2, startDate, includeMeta)
                    showList.append(tmpstr)
                    showcount += dur
                    self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(showcount/60/60),inc=int(((showcount/60/60) // limit) // self.enteredChannelCount))
        except Exception,e:
            self.log("fillLiveTVGuide failed! " + str(e), xbmc.LOGERROR)               
        return showList
        
        
    def fillLiveTVXMLTV(self, setting1, setting2, setting3, setting4, chname, limit):
        self.log("fillLiveTVXMLTV")
        showList = []
        showcount = 0        
        try:
            # local or url xmltv file
            if setting3[0:4] == 'http':
                f = open_url(self.xmlTvFile)
            else:
                f = FileAccess.open(self.xmlTvFile, "r")
                
            context = ET.iterparse(f, events=("start", "end")) 
            context = iter(context)
            event, root = context.next()
            now = datetime.datetime.now()
            offset = 0
            for event, elem in context:
                if self.threadPause() == False:
                    del showList[:]
                    break
                              
                if showcount > limit:
                    break
   
                id = '0'
                dur = 0
                playcount = 0
                seasonNumber = 0
                episodeNumber = 0
                episodeName = ''
                episodeDesc = ''
                episodeGenre = ''
                dd_progid = ''
                type = ''
                LiveID = 'tvshow|0|0|False|1|NR|'
                thumburl = '0'
                includeMeta = self.includeMeta
                
                if event == "end":
                    if elem.tag == "programme":
                        channel = elem.get("channel")
                        if setting1 == channel:
                            self.log("fillLiveTVXMLTV, setting1 = " + setting1 + ', channel id = ' + channel)
                            stopDate = self.parseXMLTVDate(elem.get('stop'), offset)
                            startDate = self.parseXMLTVDate(elem.get('start'), offset)
                        
                            #skip old shows that have already ended
                            if now > stopDate:
                                continue

                            #adjust the duration of the current show
                            if now >= startDate and now <= stopDate:
                                dur = (stopDate - startDate).seconds
                            
                            #use the full duration for an upcoming show
                            if now < startDate:
                                dur = (stopDate - startDate).seconds
             
                            if dur > 0:
                                showtitle = uni(elem.findtext('title'))
                                description = uni(elem.findtext("desc"))
                                
                                icon = None
                                iconElement = uni(elem.find("icon"))
                                if iconElement is not None:
                                    icon = uni(iconElement.get("src"))
                                    if icon.startswith('http'):
                                        thumburl = encodeString(icon)
                                    elif icon.startswith('"photos"'):
                                        thumburl = encodeString(((cleanHTML(icon)).replace('"}]',"").replace("\/","//")).rsplit(':"', 1)[1])
                                    elif icon.startswith('&quot;photos&quot;:'):
                                        icon = (icon.split('&quot;photos&quot;:')[1]).replace('\/','/').replace('&quot;','')
                                        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(icon)
                                        for c in detail:
                                            if c.startswith('width:430,height:574,url:'):
                                                thumburl = encodeString(f.split('width:430,height:574,url:')[1])
                                                break
                                    
                                subtitle = uni(elem.findtext("sub-title"))
                                if not subtitle:                        
                                    subtitle = 'LiveTV'
                                if not description:
                                    if not subtitle:
                                        description = showtitle  
                                    else:
                                        description = subtitle

                                #Parse the category of the program
                                movie = False
                                genre = 'Unknown'
                                categories = ''
                                categoryList = uni(elem.findall("category"))
                                for cat in categoryList:
                                    categories += ', ' + cat.text
                                    if (cat.text).lower() == 'movie':
                                        movie = True
                                        genre = cat.text
                                    elif (cat.text).lower() == 'tvshow':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'sports':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'children':
                                        genre = 'Kids'
                                    elif (cat.text).lower() == 'kids':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'news':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'comedy':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'drama':
                                        genre = cat.text
                                
                                #Trim prepended comma and space (considered storing all categories, but one is ok for now)
                                categories = categories[2:]                           
                                #If the movie flag was set, it should override the rest (ex: comedy and movie sometimes come together)
                                if movie == True:
                                    type = 'movie'
                                else:
                                    type = 'tvshow'
                                        
                                # todo improve v-chip, mpaa ratings
                                HD = False
                                try:
                                    for HDLst in elem.findall('video'):
                                        if HDLst.find('quality').text == 'HDTV':
                                            HD = True
                                            break
                                except:
                                    HD = False
                                    
                                stars = 0.0
                                try:
                                    for StarLst in elem.findall('star-rating'):
                                        stars = convert_to_stars(convert_to_float((StarLst.find('value').text)))
                                        break
                                except:
                                    stars = 0.0

                                rating = 'NR'
                                try:
                                    for ratLst in elem.findall('rating'):
                                        rating = self.cleanRating(StarLst.find('value'))
                                        break
                                except:
                                    rating = 'NR'

                                CC = False
                                try:
                                    subtitles = elem.findtext("subtitles")
                                    if subtitles:           
                                        CC = True
                                except:
                                    CC = 'NR'
      
                                #Read the "new" boolean for this program
                                if elem.find("new") != None:
                                    playcount = 0
                                elif "*" in showtitle:
                                    playcount = 0
                                    showtitle = showtitle.split(" *")[0]
                                elif '(n)' in description:
                                    playcount = 0
                                elif '(repeat)' in description:
                                    playcount = 1
                                else:
                                    playcount = 1                        

                                year = 0
                                if type == 'movie':
                                    try:
                                        year = elem.findtext('date')[0:4]
                                    except:
                                        year = 0      

                                #Enable Enhanced Parsing for current and future shows only
                                if (showtitle.lower() == 'paid programing' or subtitle.lower() == 'paid programing' or description.lower() == 'paid programing'):
                                    includeMeta = False  
                                        
                                if includeMeta == True:
                                    if type == 'tvshow':
                                        #Decipher the TVDB ID by using the Zap2it ID in dd_progid
                                        episodeNumList = elem.findall("episode-num") 
                                        for epNum in episodeNumList:
                                            if epNum.attrib["system"] == 'dd_progid':
                                                dd_progid = epNum.text
                                        
                                        #The Zap2it ID is the first part of the string delimited by the dot
                                        #  Ex: <episode-num system="dd_progid">MV00044257.0000</episode-num>
                                        dd_progid = dd_progid.split('.',1)[0]
                                        self.log('fillLiveTVXMLTV, dd_progid = ' + dd_progid)
                                        id = self.getTVDBIDbyZap2it(dd_progid)

                                        #Find Episode info by air date.
                                        if id != '0':
                                            #Date element holds the original air date of the program
                                            airdateStr = elem.findtext('date')
                                            if airdateStr != None:
                                                self.log('fillLiveTVXMLTV, tvdbid by airdate')
                                                try:
                                                    #Change date format into the byAirDate lookup format (YYYY-MM-DD)
                                                    t = time.strptime(airdateStr, '%Y%m%d')
                                                    airDateTime = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                                                    airdate = airDateTime.strftime('%Y-%m-%d')
                                                    #Only way to get a unique lookup is to use TVDB ID and the airdate of the episode
                                                    episode = ET.fromstring(self.tvdbAPI.getEpisodeByAirdate(id, airdate))
                                                    episode = episode.find("Episode")
                                                    seasonNumber = episode.findtext("SeasonNumber")
                                                    episodeNumber = episode.findtext("EpisodeNumber")
                                                    episodeDesc = (episode.findtext("Overview") or '')
                                                    episodeName = (episode.findtext("EpisodeName") or '')
                                                    
                                                    if len(episodeName) > 0:
                                                        subtitle = episodeName
                                                    
                                                    if len(episodeDesc) > 0:
                                                        description = episodeDesc
                                                    
                                                    try:
                                                        int(seasonNumber)
                                                        int(episodeNumber)
                                                    except:
                                                        seasonNumber = 0
                                                        episodeNumber = 0
                                                        
                                                    if seasonNumber > 0:
                                                        seasonNumber = '%02d' % int(seasonNumber)
                                                    
                                                    if episodeNumber > 0:
                                                        episodeNumber = '%02d' % int(episodeNumber)
                                                except Exception,e:
                                                    self.log('fillLiveTVXMLTV, tvdbid by airdate Failed ' + str(e))
                                                    seasonNumber = 0
                                                    episodeNumber = 0
                                                    
                                if type == 'tvshow':
                                    episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ (subtitle)).replace('  ',' ')
                                    if str(episodetitle[0:5]) == '00x00':
                                        episodetitle = episodetitle.split("- ", 1)[-1]
                                    subtitle = episodetitle

                                managed =  False # todo check sickbeard/sonar/couchpotato
                                GenreLiveID = [genre,type,id,thumburl,managed,playcount,rating, HD, CC, stars, year]
                                tmpstr = self.makeTMPSTR(dur, showtitle, year, subtitle, description, GenreLiveID, setting2, startDate, includeMeta)
                                showList.append(tmpstr)
                                showcount += dur
                                self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(showcount/60/60),inc=int(((showcount/60/60) // limit) // self.enteredChannelCount))
                root.clear()
            f.close()                   
        except Exception,e:
            self.log("fillLiveTVXMLTV failed! " + str(e), xbmc.LOGERROR)
        return showList
        
            
    def fillLiveTVPVR(self, setting1, setting2, setting3, setting4, chname, limit):
        self.log("fillLiveTVPVR")
        showList = []
        showcount = 0
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetBroadcasts","params":{"channelid":%s,"properties":["title","plot","plotoutline","starttime","endtime","runtime","genre","episodename","episodenum","episodepart","firstaired","hastimer","parentalrating","thumbnail","rating"]}, "id": 1}' % setting1)
        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile("{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        now = self.parsePVRDate((str(datetime.datetime.utcnow())).split(".")[0])       
        try:
            for f in detail:
                if self.threadPause() == False:
                    del showList[:]
                    return
                                            
                if showcount > limit:
                    break   
                    
                includeMeta = self.includeMeta
                titles = re.search('"title" *: *"(.*?)"', f)
                if titles and len(titles.group(1)) > 0:
                    showtitle = titles.group(1)
                else:
                    try:
                        labels = re.search('"label" *: *"(.*?)"', f)
                        showtitle = labels.group(1)
                    except:
                        showtitle = chname
                                    
                startDates = re.search('"starttime" *: *"(.*?)",', f)
                stopDates = re.search('"endtime" *: *"(.*?)",', f)
                id = '0'
                dur = 0
                seasonNumber = 0
                episodeNumber = 0
                hd = False
                cc = False
                
                if startDates and len(startDates.group(1)) > 0 and stopDates and len(stopDates.group(1)) > 0:
                    startDate = self.parsePVRDate(startDates.group(1))
                    stopDate = self.parsePVRDate(stopDates.group(1))

                    #skip old shows that have already ended
                    if now > stopDate:
                        continue
                    
                    #adjust the duration of the current show
                    if now >= startDate and now <= stopDate:
                        runtimes = re.search('"runtime" *: *"(.*?)",', f)
                        if runtimes:
                            dur = int(runtimes.group(1)) * 60
                        else:
                            dur = ((stopDate - startDate).seconds) 
                    
                    #use the full duration for an upcoming show
                    if now < startDate:
                        runtimes = re.search('"runtime" *: *"(.*?)",', f)
                        if runtimes:
                            dur = int(runtimes.group(1)) * 60
                        else:
                            dur = ((stopDate - startDate).seconds)   
     
                    if dur > 0:
                        years = re.search('"year" *: *([\d.]*\d+)', f)
                        # if possible find year by title
                        try:
                            year = int(years.group(1))
                        except:
                            year = 0
                        
                        ratings = re.search('"parentalrating" *: *"(.*?)"', f)   
                        if ratings != None and len(ratings.group(1)) > 0:
                            rating = self.cleanRating(ratings.group(1))
                        else:
                            rating = 'NR'
                            
                        starss = re.search('"rating" *: *"(.*?)"', f)   
                        if starss != None and len(starss.group(1)) > 0:
                            stars = float(starss.group(1))
                        else:
                            stars = 0.0

                        movie = False
                        genres = re.search('"genre" *: *"(.*?)",', f)
                        if genres and len(genres.group(1)) > 0:
                            genre = genres.group(1)
                            if genre.lower() == 'movie':
                                movie = True
                        else:
                            genre = 'Unknown'

                        if movie == True:
                            type = 'movie'
                        else:
                            type = 'tvshow'

                        try:
                            test = showtitle.split(" *")[1]
                            showtitle = showtitle.split(" *")[0]
                            playcount = 0
                        except Exception,e:
                            playcount = 1

                        plots = re.search('"plot" *: *"(.*?)"', f)            
                        descriptions = re.search('"description" *: *"(.*?)",', f)
                        plotoutlines = re.search('"plotoutline" *: *"(.*?)",', f)
                        if plots and len(plots.group(1)) > 0:
                            theplot = (plots.group(1)).replace('\\','').replace('\n','')
                        elif descriptions and len(descriptions.group(1)) > 0:
                            theplot = (descriptions.group(1)).replace('\\','').replace('\n','')
                        elif plotoutlines and len(plotoutlines.group(1)) > 0:
                            theplot = (plotoutlines.group(1)).replace('\\','').replace('\n','')
                        else:
                            theplot = (titles.group(1)).replace('\\','').replace('\n','')
                        description = theplot
                        
                        thumbs = re.search('"thumbnail" *: *"(.*?)"', f)
                        if thumbs and len(thumbs.group(1)) > 0:
                            thumburl = encodeString(thumbs.group(1))
                        else:
                            thumburl = 0
                            
                        episodetitle = 'LiveTV'
                        subtitle = 'LiveTV'

                        # if type == 'tvshow':
                            # episodenames = re.search('"episodename" *: *"(.*?)"', f)
                            # if episodenames and len(episodenames) > 0:
                                # episodetitle = episodenames.group(1)
                            # else:
                                # episodetitle = 'LiveTV'
                                
                            # episodenums = re.search('"episodenum" *: *"(.*?)"', f)
                            # if episodenums and len(episodenums) > 0:
                                # episodenum = episodenums.group(1) 
                            # else:
                                # episodenum = 0 
                                
                            # episodeparts = re.search('"episodepart" *: *"(.*?)"', f)
                            # if episodeparts and len(episodeparts) > 0:
                                # episodepart = episodeparts.group(1)
                            # else:
                                # episodepart = 0 
                        # else:
                            # subtitle = 'LiveTV'
    
                        if seasonNumber > 0:
                            seasonNumber = '%02d' % int(seasonNumber)
                        
                        if episodeNumber > 0:
                            episodeNumber = '%02d' % int(episodeNumber)

                        if type == 'tvshow':
                            episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ (subtitle)).replace('  ',' ')
                            if str(episodetitle[0:5]) == '00x00':
                                episodetitle = episodetitle.split("- ", 1)[-1]
                            subtitle = episodetitle
                                                 
                        #Enable Enhanced Parsing for current and future shows only
                        if (showtitle.lower() == 'paid programing' or subtitle.lower() == 'paid programing' or description.lower() == 'paid programing'):
                            includeMeta = False     
                            
                        managed =  False     
                        GenreLiveID = [genre,type,id,thumburl,managed,playcount,rating,hd,cc,stars, year]
                        tmpstr = self.makeTMPSTR(dur, showtitle, year, subtitle, description, GenreLiveID, setting2, startDate, includeMeta)
                        showList.append(tmpstr)
                        showcount += dur
                        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(showcount/60/60),inc=int(((showcount/60/60) // limit) // self.enteredChannelCount))  
        except Exception,e:
            self.log("fillLiveTVPVR failed! " + str(e), xbmc.LOGERROR) 
        return showList

        
    def buildInternetTVFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log('buildInternetTVFileList')
        showList = []
        showcount = 0
        dur = 0
        title = setting3
        description = setting4
        if not description:
            description = title
        # setting2 = (tidy(setting2)).replace(',', '')
        if len(setting1) > 0:
            dur = setting1
        else:
            dur = 5400  #90 minute default
                
        GenreLiveID = ['Unknown','other',0,0,False,1,'NR',False, False, 0.0, 0]
        tmpstr = self.makeTMPSTR(dur, title, 0, "InternetTV", description, GenreLiveID, setting2, timestamp=None, includeMeta=False)
        for i in range(limit):         
            if self.threadPause() == False:
                del showList[:]
                break
            showList.append(tmpstr)
        return showList

        
    def createYoutubeFilelist(self, setting1, setting2, setting3, setting4, limit):
        self.log("createYoutubeFilelist")
        showList = []
        showcount = 0
        self.YT_VideoCount = 0
        self.YT_showList = []
        YTMSG = setting1
        if self.youtube_player != 'False':
            limit = int(limit)
            if setting2 == '1':
                YTMSG = 'Channel ' + setting1
                showList = self.getYoutubeVideos(1, setting1, '', limit, YTMSG)
            elif setting2 == '2':
                YTMSG = 'Playlist ' + setting1
                showList = self.getYoutubeVideos(2, setting1, '', limit, YTMSG)
            elif setting2 == '5':
                YTMSG = 'Search Querys'
                showList = self.getYoutubeVideos(5, setting1, '', limit, YTMSG)
            elif setting2 == '7':
                YTMSG = 'MultiTube Playlists'
                showList = self.BuildMultiYoutubeChannelNetwork(setting1, setting2, setting3, setting4, limit)
            elif setting2 == '8':
                YTMSG = 'MultiTube Channels'
                showList = self.BuildMultiYoutubeChannelNetwork(setting1, setting2, setting3, setting4, limit)
            elif setting2 == '31':
                YTMSG = 'Seasons Channel'
                showList = self.BuildseasonalYoutubeChannel(setting1, setting2, setting3, setting4, limit)    
        return showList

        
    def BuildseasonalYoutubeChannel(self, setting1, setting2, setting3, setting4, limit):
        self.log("BuildseasonalYoutubeChannel")
        showList = []
        linesLST = []
        genre_filter = [setting1.lower()]
        Playlist_List = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_seasonal.ini'
        linesLST = read_url_cached(Playlist_List, return_type='readlines')
        if linesLST:
            for i in range(len(linesLST)):
                try:
                    line = str(linesLST[i]).replace("\n","").replace('""',"")
                    line = line.split("|")
                
                    #If List Formatting is bad return
                    if len(line) == 7:  
                        genre = line[0]
                        chtype = line[1]
                        setting1 = (line[2]).replace(",","|")
                        setting2 = line[3]
                        setting3 = line[4]
                        setting4 = line[5]
                        channel_name = line[6]
                        CHname = channel_name
                        if genre.lower() in genre_filter:
                            channelList = setting1.split('|')              
                            for n in range(len(channelList)):
                                showList.extend(self.createYoutubeFilelist(channelList[n], '2', setting3, setting4, limit))
                except:
                    pass
        # cleanup   
        del linesLST[:]
        return showList
    
    
    def BuildMultiYoutubeChannelNetwork(self, setting1, setting2, setting3, setting4, limit):
        self.log("BuildMultiYoutubeChannelNetwork")
        tmpstr = ''
        showList = []  
        channelList = setting1.split('|')
        if setting2 == '7':
            for n in range(len(channelList)):
                Pluginvalid = self.youtube_ok(channelList[n], '2')
                if Pluginvalid != False:
                    self.YT_VideoCount = 0
                    nlimit = int(limit/len(channelList))
                    tmpstr = self.createYoutubeFilelist(channelList[n], '2', setting3, setting4, nlimit)
                    showList.extend(tmpstr)     
        else:
            for n in range(len(channelList)):
                Pluginvalid = self.youtube_ok(channelList[n], '1')
                if Pluginvalid != False:
                    self.YT_VideoCount = 0
                    nlimit = int(limit/len(channelList))
                    tmpstr = self.createYoutubeFilelist(channelList[n], '1', setting3, setting4, nlimit)
                    showList.extend(tmpstr)
        random.shuffle(showList)
        return showList[:limit]
    
    
    def getYoutubeDetails(self, YTID):
        self.log('getYoutubeDetails')
        try:
            YT_URL_Video = ('https://www.googleapis.com/youtube/v3/videos?key=%s&id=%s&part=id,snippet,contentDetails,statistics' % (YT_API_KEY, YTID))
            details = re.compile("},(.*?)}", re.DOTALL ).findall(read_url_cached(YT_URL_Video))
        except:
            details = ''
        return details

        
    def getYoutubeChname(self, YTID):
        self.log('getYoutubeChname')
        if YTID.startswith('UC'):
            YT_URL_Video = ('https://www.googleapis.com/youtube/v3/channels?part=snippet%2CcontentDetails%2Cstatistics&id='+YTID+'&key='+YT_API_KEY)
        else:
            YT_URL_Video = ('https://www.googleapis.com/youtube/v3/search?part=snippet&q='+YTID+'&type=channel&key='+YT_API_KEY)
        detail = re.compile("},(.*?)}", re.DOTALL ).findall(read_url_cached(YT_URL_Video))
        for f in detail:
            try:
                Titles = re.search('"title" *: *"(.*?)",', f)
                channelTitles = re.search('"channelTitle" *: *"(.*?)",', f)
                if Titles:
                    return Titles.group(1)
                if channelTitles:
                    return channelTitles.group(1)
            except:
                pass
        return YTID
    
    
    def getYoutubeDuration(self, YTID):
        self.log('getYoutubeDuration')
        detail = self.getYoutubeDetails(YTID)
        for f in detail:
            try:
                durations = re.search('"duration" *: *"(.*?)",', f)
                if durations:
                    return self.parseYoutubeDuration(durations.group(1))
            except:
                pass
        return 0
        
        
    def parseYoutubeDuration(self, duration):
        try:
            dur = 0
            """ Parse and prettify duration from youtube duration format """
            DURATION_REGEX = r'P(?P<days>[0-9]+D)?T(?P<hours>[0-9]+H)?(?P<minutes>[0-9]+M)?(?P<seconds>[0-9]+S)?'
            NON_DECIMAL = re.compile(r'[^\d]+')
            duration_dict = re.search(DURATION_REGEX, duration).groupdict()
            converted_dict = {}
            # convert all values to ints, remove nones
            for a, x in duration_dict.iteritems():
                if x is not None:
                    converted_dict[a] = int(NON_DECIMAL.sub('', x))
            x = time.strptime(str(timedelta(**converted_dict)).split(',')[0],'%H:%M:%S')
            dur = int(self.__total_seconds__(datetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec)))
            self.log('parseYoutubeDuration, dur = ' + str(dur))
        except Exception,e:
            pass
        return dur
    
    
    def getYoutubeUserID(self, YTid):
        self.log("getYoutubeUserID, IN = " + YTid)
        YT_ID = 'UC'
        try:
            region = 'US' #todo
            lang = xbmc.getLanguage(xbmc.ISO_639_1)
            youtubeApiUrl = 'https://www.googleapis.com/youtube/v3/'
            youtubeChannelsApiUrl = (youtubeApiUrl + 'channels?key=%s&chart=mostPopular&regionCode=%s&hl=%s&' % (YT_API_KEY, region, lang))
            requestParametersChannelId = (youtubeChannelsApiUrl + 'forUsername=%s&part=id' % (YTid))
            f = read_url_cached(requestParametersChannelId)
            YT_IDS = re.search('"id" *: *"(.*?)"', f)
            if YT_IDS:
                YT_ID = YT_IDS.group(1)
            self.log("getYoutubeUserID, OUT = " + YT_ID)
        except Exception,e:
            self.log('getYoutubeUserID, failed! ' + str(e), xbmc.LOGERROR)
        return YT_ID
            
            
    def getYoutubeVideos(self, YT_Type, YT_ID, YT_NextPG, limit, YTMSG):
        self.log("getYoutubeVideos, YT_Type = " + str(YT_Type) + ', YT_ID = ' + YT_ID) 
        region = 'US' #todo
        lang = xbmc.getLanguage(xbmc.ISO_639_1)
        Last_YT_NextPG = YT_NextPG      
        youtubeApiUrl = 'https://www.googleapis.com/youtube/v3/'
        youtubeChannelsApiUrl = (youtubeApiUrl + 'channels?key=%s&chart=mostPopular&regionCode=%s&hl=%s&' % (YT_API_KEY, region, lang))
        youtubeSearchApiUrl = (youtubeApiUrl + 'search?key=%s&chart=mostPopular&regionCode=%s&hl=%s&' % (YT_API_KEY, region, lang))
        youtubePlaylistApiUrl = (youtubeApiUrl + 'playlistItems?key=%s&chart=mostPopular&regionCode=%s&hl=%s&' % (YT_API_KEY, region, lang))
        requestChannelVideosInfo = (youtubeSearchApiUrl + 'channelId=%s&part=id&order=date&pageToken=%s&maxResults=50' % (YT_ID, YT_NextPG))
        requestPlaylistInfo = (youtubePlaylistApiUrl+ 'part=snippet&maxResults=50&playlistId=%s&pageToken=%s' % (YT_ID, YT_NextPG))
    
        if YT_Type == 5:
            try:
                safesearch, YT_ID = YT_ID.split('|')
            except:
                safesearch = 'none'
            requestSearchVideosInfo = (youtubeSearchApiUrl + 'safeSearch=%s&q=%s&part=snippet&order=date&pageToken=%s&maxResults=50' % (safesearch.lower(), YT_ID.replace(' ','%20'), YT_NextPG))
            
    # https://www.googleapis.com/youtube/v3/search?part=snippet&q=movies&type=channel&key=AIzaSyAnwpqhAmdRShnEHnxLiOUjymHlG4ecE7c movie channels
    # https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId=UCczhp4wznQWonO7Pb8HQ2MQ&key=AIzaSyAnwpqhAmdRShnEHnxLiOUjymHlG4ecE7c
    
        if YT_Type == 1:
            if YT_ID[0:2] != 'UC':
                YT_ID = self.getYoutubeUserID(YT_ID)
                return self.getYoutubeVideos(YT_Type, YT_ID, YT_NextPG, limit, YTMSG)  
            else:
                YT_URL_Search = requestChannelVideosInfo
                self.log("getYoutubeVideos, requestChannelVideosInfo = " + YT_URL_Search) 
        elif YT_Type == 2:
            YT_URL_Search = requestPlaylistInfo
            self.log("getYoutubeVideos, requestPlaylistInfo = " + YT_URL_Search) 
            
        elif YT_Type == 5:
            YT_URL_Search = requestSearchVideosInfo
            self.log("getYoutubeVideos, requestSearchVideosInfo = " + YT_URL_Search) 
            
        try:
            detail = re.compile( "{(.*?)}", re.DOTALL ).findall(read_url_cached(YT_URL_Search))  
                            
            for f in detail:
                if self.threadPause() == False:
                    del self.YT_showList[:]
                    break
                try:
                    VidIDS = re.search('"videoId" *: *"(.*?)"', f)
                    YT_NextPGS = re.search('"nextPageToken" *: *"(.*?)"', f)
                    if YT_NextPGS:
                        YT_NextPG = YT_NextPGS.group(1)
                        
                    if VidIDS:
                        YTID = VidIDS.group(1)
                        dur = self.getYoutubeDuration(YTID)
                        
                        # Use adv. channel rule to filter unwanted content by duration
                        if dur < self.durFilter:
                            self.log("getYoutubeVideos, ignoring duration; "+str(dur)+" less than " + str(self.durFilter))
                            dur = 0
                            
                        if dur > 0:                
                            GenreLiveID = ['Unknown','youtube',0,YTID,False,1,'NR',False, False, 0.0, 0]
                            tmpstr = self.makeTMPSTR(dur, '', 0, 'Youtube', '', GenreLiveID, self.youtube_player + YTID)   
                            self.YT_showList.append(tmpstr)
                            self.YT_VideoCount += 1
                            self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(self.YT_VideoCount),inc=int(((self.YT_VideoCount) // limit) // self.enteredChannelCount))
                            if self.YT_VideoCount >= limit:
                                return self.YT_showList
                except:
                    pass
        except Exception,e:
            self.log('getYoutubeVideos, Failed!, ' + str(e))
                        
        if YT_NextPG == Last_YT_NextPG:
            return self.YT_showList
        else:
            if YT_NextPG and self.YT_VideoCount < limit:
                self.YT_showList += self.getYoutubeVideos(YT_Type, YT_ID, YT_NextPG, limit, YTMSG)
        return self.YT_showList
        
    
    def createRSSFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log("createRSSFileList")
        fileList = []
        filecount = 0        
        feed = feedparser.parse(setting1)
        
        for i in range(len(feed['entries'])):   
            if self.threadPause() == False:
                del fileList[:]
                break
            try:
                showtitle = feed.channel.title
                eptitle = feed.entries[i].title
                # if 'author_detail' in feed.entries[i]:
                    # studio = feed.entries[i].author_detail['name']  
                # elif 'itunes:author' in feed.entries[i]:
                    # studio = feed.entries[i]['author']
                # else:
                    # self.log("createRSSFileList, Invalid author_detail")  

                try:
                    # todo parse itune:image
                    if 'media_thumbnail' in feed.entries[i]:
                        thumburl = encodeString(feed.entries[i].media_thumbnail[0]['url'])       
                    elif 'itunes:image' in feed.entries[i]:
                        thumburl = encodeString(feed.entries[i].itunes_image[0]['url'])
                    else:
                        raise Exception()
                except:
                    thumburl = 0
                    
                try:
                    epdesc = feed.channel.subtitle
                except Exception,e:
                    epdesc = ''
                
                if not epdesc:
                    epdesc = feed.entries[i]['subtitle']
                if not epdesc:
                    if feed.entries[i].summary_detail.value:
                        epdesc = feed.entries[i]['summary_detail']['value']
                    else:
                        epdesc = feed.entries[i]['blip_puredescription']      
                if not epdesc:
                    epdesc = showtitle + " - " + eptitle

                if 'media_content' in feed.entries[i]:
                    url = feed.entries[i].media_content[0]['url']
                else:
                    url = feed.entries[i].links[1]['href']
                
                try:
                    runtimex = feed.entries[i]['itunes_duration']
                except Exception,e:
                    runtimex = 0
                if runtimex == 0:
                    try:
                        runtimex = feed.entries[i]['blip_runtime']
                    except Exception,e:
                        runtimex = 0
                self.log("createRSSFileList, runtimex = " + str(runtimex)) 
                
                if feed.channel.has_key("tags"):
                    genre = feed.channel.tags[0]['term']
                    genre = uni(genre)
                else:
                    genre = "Unknown"

                try:
                    time = (str(feed.entries[i].published_parsed)).replace("time.struct_time", "")                        
                    showseason = [word for word in time.split() if word.startswith('tm_mon=')]
                    showseason = str(showseason)
                    showseason = showseason.replace("['tm_mon=", "")
                    showseason = showseason.replace(",']", "")
                    showepisodenum = [word for word in time.split() if word.startswith('tm_mday=')]
                    showepisodenum = str(showepisodenum)
                    showepisodenum = showepisodenum.replace("['tm_mday=", "")
                    showepisodenum = showepisodenum.replace(",']", "")
                    showepisodenuma = [word for word in time.split() if word.startswith('tm_hour=')]
                    showepisodenuma = str(showepisodenuma)
                    showepisodenuma = showepisodenuma.replace("['tm_hour=", "")
                    showepisodenuma = showepisodenuma.replace(",']", "")  
                    try:
                        hours, minutes, seconds = map(int, runtimex.split(':'))
                    except ValueError:
                        hours = 0
                        minutes, seconds = map(int, runtimex.split(':'))
                    runtime = (hours*3600) + (minutes*60) + seconds                    
                    self.log("createRSSFileList, runtime = " + str(runtime)) 
                except Exception,e:
                    pass
                
                if runtime == 0:
                    runtime = 800
                duration = int(runtime)
                url = url.replace("&amp;amp;feature=youtube_gdata", "").replace("http://www.youtube.com/watch?hd=1&v=", self.youtube_player).replace("http://www.youtube.com/watch?v=", self.youtube_player)
                GenreLiveID = [genre,'rss',0,thumburl,False,1,'NR',False, False, 0.0, 0]
                tmpstr = self.makeTMPSTR(duration, eptitle, 0, "RSS - " + showtitle, epdesc, GenreLiveID, url)
                fileList.append(tmpstr)
                filecount += 1 
                self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(filecount),inc=int(((filecount) // limit) // self.enteredChannelCount))

                if filecount > limit:
                    break
            except Exception,e:
                pass
        return fileList
     
        
    def isXMLTVCurrent(self, xmlfle):
        self.log("isXMLTVCurrent, xmlfle = " + xmlfle)
        isCurrent = False
        now = datetime.datetime.now()
        try:
            # local or url xmltv file
            if xmlfle[0:4] == 'http':
                f = open_url(xmlfle)
            else:
                f = FileAccess.open(xmlfle, "r")
                
            # check if xmltv uses utc time
            if xmlfle.lower() in UTC_XMLTV:                      
                offset = ((time.timezone / 3600) - 5 ) * -1     
            else:
                offset = 0
                
            context = ET.iterparse(f, events=("start", "end")) 
            context = iter(context)
            event, root = context.next()

            for event, elem in context:
                try:
                    if event == "end":
                        if elem.tag == "programme":
                            if xmlfle.lower() in ['ptvlguide']:
                                stopDate = self.parseUTCXMLTVDate(elem.get('stop'))
                                startDate = self.parseUTCXMLTVDate(elem.get('start'))
                            else:
                                stopDate = self.parseXMLTVDate(elem.get('stop'), offset)
                                startDate = self.parseXMLTVDate(elem.get('start'), offset)
                            if (((now > startDate and now <= stopDate) or (now < startDate))):
                                isCurrent = True
                except:
                    pass
        except Exception,e:
            self.log("isXMLTVCurrent, failed! " + str(e))
        self.log("isXMLTVCurrent, isCurrent = " + str(isCurrent))
        return isCurrent
                
                
    def xmltv_ok(self, path):
        self.log("xmltv_ok")
        if path[0:4] == 'http':
            self.xmlTvFile = path
            return self.url_ok(path)
        elif path.lower() in ['pvr','hdhomerun','ustvnow']:
            return True
        elif len(path) > 0:
            self.xmlTvFile = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('xmltvLOC'), str(path) +'.xml'))
            if FileAccess.exists(self.xmlTvFile):
                return True          
        return False
           
           
    def Valid_ok(self, url):
        self.log("Valid_ok")
        #plugin check  
        if url[0:6] == 'plugin':  
            return self.plugin_ok(url) 
        #upnp check
        elif url[0:4] == 'upnp':
            return self.upnp_ok(url)
        #pvr/udp check
        elif url[0:3] in ['pvr','udp']:
            return True
        #Override Check# 
        elif REAL_SETTINGS.getSetting('Override_ok') == "true":
            return True 
        #rtmp/rtsp check
        elif url[0:4] in ['rtmp','rtsp']:
            return self.rtmpDump(url)  
        #http check     
        elif url[0:4] == 'http':
            return self.url_ok(url)
        #strm check  
        elif url[-4:] == 'strm':         
            return self.strm_ok(url)
        else:
            return True
  
      
    def rtmpDump(self, stream):
        rtmpValid = False    
        try:
            url = urllib.unquote(stream)
            RTMPDUMP = xbmc.translatePath(REAL_SETTINGS.getSetting('rtmpdumpPath'))
            self.log("rtmpDump, RTMPDUMP = " + RTMPDUMP)
            assert os.path.isfile(RTMPDUMP)
            if FileAccess.exists(RTMPDUMP) == False:
                raise Exception()
            
            if "playpath" in url:
                url = re.sub(r'playpath',"-y playpath",url)
                self.log("rtmpDump, playpath url = " + str(url))
                command = [RTMPDUMP, '-B 1', '-m 2', '-r', url,'-o','test.flv']
            else:
                command = [RTMPDUMP, '-B 1', '-m 2', '-r', url,'-o','test.flv']
            self.log("rtmpDump, RTMPDUMP command = " + str(command))
            CheckRTMP = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
            output = CheckRTMP.communicate()[0]
            
            if "INFO: Connected..." in output:
                self.log("rtmpDump, INFO: Connected...")
                rtmpValid = True
        except Exception,e:
            rtmpValid = True
            self.log('rtmpDump, failed! ' + str(e))
        self.log("rtmpDump, rtmpValid = " + str(rtmpValid))
        return rtmpValid
        
                
    def url_ok(self, url):
        urlValid = False
        try:
            urllib2.urlopen(url)
            urlValid = True
        except urllib2.HTTPError, e:
            self.log("url_ok, failed! HTTPError " + str((e.code)))
        except urllib2.URLError, e:
            self.log("url_ok, failed! URLError " + str((e.args)))
        self.log("url_ok, urlValid = " + str(urlValid))
        return urlValid
        

    def plugin_ok(self, plugin):
        status = isPlugin(plugin)
        self.log("plugin_ok, plugin = " + plugin + ' ,installed = ' + str(status))
        return status
        
        
    def youtube_ok(self, YTtype, YTid):
        # todo finish valid youtube channel/playlist check
        if self.youtube_player != 'False':
            return True

            
    def vimeo_player_ok(self):
        try:
            return self.vimeo_player
        except:
            self.log("vimeo_player_ok")
            if self.plugin_ok('plugin.video.vimeo') == True:
                self.vimeo_player = 'plugin://plugin.video.vimeo/play/?video_id='
            else:
                self.vimeo_player = 'False'
            self.log("vimeo_player_ok = " + str(self.vimeo_player))
            return self.vimeo_player

            
    def youtube_player_ok(self):
        try:
            return self.youtube_player
        except:
            self.log("youtube_player_ok")
            if self.plugin_ok('plugin.video.youtube') == True:
                self.youtube_player = 'plugin://plugin.video.youtube/?action=play_video&videoid='
            else:
                self.youtube_player = 'False'
            self.log("youtube_player_ok = " + str(self.youtube_player))
            return self.youtube_player
           

    def upnp_ok(self, url):
        self.log("upnp_ok, " + str(url))
        upnpID = (url.split('/')[2:-1])[0]
        dirs, files = FileAccess.listdir(os.path.join('upnp://',''))
        if upnpID in dirs:
            return True
        else:
            return False
  
  
    def strm_ok(self, url):
        self.log("strm_ok, " + str(url))
        strmValid = False
        lines = ''
        try:
            f = FileAccess.open(url, "r")
            linesLST = f.readlines()
            self.log("strm_ok.Lines = " + str(linesLST))
            f.close()

            for i in range(len(set(linesLST))):
                lines = linesLST[i]
                strmValid = self.Valid_ok(lines)
                if strmValid == True:
                    return strmValid             
        except Exception,e:
            pass
        # if strmValid == False:
            # self.writeStrm_ok(url)
        return strmValid   

        
    def writeStrm_ok(self, url, fallback=INTRO_TUBE):
        self.log("writeStrm_ok, " + str(url))
        try:
            f = FileAccess.open(url, "w")
            for i in range(len(linesLST)):
                lines = linesLST[i]
                if lines != fallback:
                    f.write(lines + '\n')
                self.log("strm_ok, file write lines = " + str(lines))
            f.write(fallback)
            f.close()         
        except Exception,e:
            pass

        
    def durationAdjust(self, dur):
        self.log("durationAdjust")
        if dur in [1500,1800]:
            return 1320 #22min runtime
        elif dur == 3600:
            return 3600 - 1080 #42min runtime
        else:
            return dur
        
        
    def durationInSeconds(self, dur):
        self.log("durationInSeconds")
        if len(str(dur)) in [1,2]:
            return dur * 60
        elif len(str(dur)) == 3:
            ndur = dur * 60
            if ndur > MAXFILE_DURATION:
                return dur
            else:
                return ndur
        return dur
           
     
    def getDuration(self, filename):
        filesize = getSize(filename)
        self.log('getDuration, filename = ' + ascii(filename) + ', filesize = ' + str(filesize))
        if CACHE_ENABLED == True:
            try:
                result = durationCache.cacheFunction(self.getDuration_NEW, filename, filesize)
                if result == 0:
                    raise
            except:
                result = self.getDuration_NEW(filename, filesize)
        else:
            result = self.getDuration_NEW(filename, filesize)
        if not result:
            result = 0
        return result  
        
        
    def getDuration_NEW(self, filename, filesize):
        self.log("getDuration_NEW")
        try:
            duration = self.videoParser.getVideoLength(filename)
        except:
            duration = 0
        if duration == 0:
            duration = self.getffprobeLength(filename)
        return duration
        
        
    def getffprobeLength(self, filename):
        try:
            result = subprocess.Popen([xbmc.translatePath(REAL_SETTINGS.getSetting('ffprobePath')), xbmc.translatePath(filename)],stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            x = ([x[12:23].split(':') for x in result.stdout.readlines() if "Duration" in x])
            duration = int(x[0][0])* 60 * 60 + int(x[0][1])* 60 + int(x[0][2].split('.')[0])
        except:
            duration = 0
        self.log("getffprobeLength, duration = " + str(duration))
        return duration

        
    def insertBCT(self, chtype, channel, fileList, type):
        self.log("insertBCT, channel = " + str(channel))
        newFileList = []
        try:
            chname = self.getChannelName(chtype, channel, ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1'))
            #Bumpers & Ratings
            BumperLST = []
            BumpersType = REAL_SETTINGS.getSetting("bumpers")      
            if BumpersType != "0" and type != 'movies': 
                BumperLST = self.getBumperList(BumpersType, chname)

                if REAL_SETTINGS.getSetting('bumperratings') == 'true':
                    fileList = self.getRatingList(chtype, chname, channel, fileList)

                # #3D, insert "put glasses on" for 3D and use 3D ratings if enabled. todo
                # if BumpersType!= "0" and type == 'movies' and REAL_SETTINGS.getSetting('bumper3d') == 'true':
                    # fileList = self.get3DList(chtype, chname, channel, fileList)
                    
            #Commercial
            CommercialLST = []
            CommercialsType = REAL_SETTINGS.getSetting("commercials") 
            if CommercialsType != '0' and type != 'movies':
                CommercialLST = self.getCommercialList(CommercialsType, chname)

            #Trailers
            try:
                if type == 'movies' and REAL_SETTINGS.getSetting('Movietrailers') == 'false':
                    raise Exception()
                    
                TrailerLST = []
                TrailersType = REAL_SETTINGS.getSetting("trailers")
                if TrailersType != '0':
                    TrailerLST = self.getTrailerList(chtype, chname)
            except:
                pass

            # Inject BCTs into filelist          
            for i in range(len(fileList)):
                newFileList.append(fileList[i])
                if len(BumperLST) > 0:  
                    random.shuffle(BumperLST)              
                    for n in range(int(REAL_SETTINGS.getSetting("numbumpers")) + 1):
                        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Bumpers")
                        newFileList.append(random.choice(BumperLST))#random fill

                if len(CommercialLST) > 0:
                    random.shuffle(CommercialLST)                
                    for n in range(int(REAL_SETTINGS.getSetting("numcommercials")) + 1):
                        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Commercials")
                        newFileList.append(random.choice(CommercialLST))#random fill
                        
                if len(TrailerLST) > 0:
                    random.shuffle(TrailerLST)                
                    for n in range(int(REAL_SETTINGS.getSetting("numtrailers")) + 1):
                        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Trailers")
                        newFileList.append(random.choice(TrailerLST))#random fill
                random.shuffle(newFileList)
                
            # cleanup   
            del fileList[:]
            del BumperLST[:]
            del CommercialLST[:]
            del TrailerLST[:]
            return newFileList
        except:
            del newFileList[:]
            return fileList
        
        
    def getBumperList(self, BumpersType, chname):
        self.log("getBumperList")
        BumperLST = []
        BumperTMPstrLST = []
        
        #Local
        if BumpersType == "1":  
            self.log("getBumperList, Local - " + chname)
            PATH = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('bumpersfolder'),chname,''))
            self.log("getBumperList, Local - PATH = " + PATH)
            BumperLST.extend(self.createDirectoryPlaylist(PATH, 100, 1, 100)) 
            
        #Internet
        elif BumpersType == "2":
            self.log("getBumperList - Internet - " + chname)
            Bumper_List = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/bumpers.ini'
            linesLST = read_url_cached(Bumper_List, return_type='readlines')
            for i in range(len(Bumper_List)): 
                self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="querying %i Internet Bumpers"%i)                    
                try:                 
                    ChannelName,BumperNumber,BumperSourceID = (str(linesLST[i]).replace('\n','').replace('\r','').replace('\t','')).split('|')
                    BumperSource,BumperID = BumperSourceID.split('_')
                    
                    if chname.lower() == ChannelName.lower():
                        if BumperSource.lower() == 'vimeo':
                            if self.vimeo_player != 'False':
                                GenreLiveID = ['Bumper', 'bct', 0, 0 , False, 1, 'NR', False, False, 0.0, 0]
                                BumperTMPstrLST.append(self.makeTMPSTR(self.getVimeoMeta(BumperID)[2], chname, 0, 'Bumper', 'Bumper', GenreLiveID, self.vimeo_player + BumperID))
                                
                        elif BumperSource.lower() == 'youtube':
                            if self.youtube_player != 'False':           
                                GenreLiveID = ['Bumper', 'bct', 0, 0 , False, 1, 'NR', False, False, 0.0, 0]
                                BumperTMPstrLST.append(self.makeTMPSTR(self.getYoutubeDuration(BumperID), chname, 0, 'Bumper', 'Bumper', GenreLiveID, self.youtube_player + BumperID, includeMeta=False))        
                except: 
                    pass
            BumperLST.extend(BumperTMPstrLST)      
        # cleanup   
        del BumperTMPstrLST[:]
        return random.shuffle(BumperLST)    
        
        
    def getRatingList(self, chtype, chname, channel, fileList, ddd=False):
        self.log("getRatingList")
        newFileList = []
        Ratings = (['NR','qlRaA8tAfc0'],['R','s0UuXOKjH-w'],['NC-17','Cp40pL0OaiY'],['PG-13','lSg2vT5qQAQ'],['PG','oKrzhhKowlY'],['G','QTKEIFyT4tk'],['18','g6GjgxMtaLA'],['16','zhB_xhL_BXk'],['12','o7_AGpPMHIs'],['6','XAlKSm8D76M'],['0','_YTMglW0yk'])
        Ratings_3D = [] # todo 3d ratings
                       
        if self.youtube_player != 'False': 
            for i in range(len(fileList)):
                if self.threadPause() == False:
                    del newFileList[:]
                    break  
                try:
                    newFileList.append(fileList[i])
                    lineLST = (fileList[i]).split('movie|')[1]
                    mpaa = (lineLST.split('\n')[0]).split('|')[4]
                    self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Ratings: " + str(mpaa))
                    
                    for i in range(len(Ratings)):
                        ID = 'qlRaA8tAfc0'
                        rating = Ratings[i]        
                        if mpaa.lower() == rating[0].lower():
                            ID = rating[1]
                            break

                    GenreLiveID = ['Rating', 'bct', 0, 0, False, 1, mpaa, False, False, 0.0, 0]
                    newFileList.append(self.makeTMPSTR(self.getYoutubeDuration(ID), chname, 0, 'Rating', 'Rating', GenreLiveID, self.youtube_player + ID, includeMeta=False))
                except:
                    pass
            # cleanup   
            del fileList[:]
            return newFileList
        else:
            return fileList
        
    
    def getCommercialList(self, CommercialsType, chname):  
        self.log("getCommercialList") 
        CommercialLST = []       

        #Local
        if CommercialsType == '1':
            self.log("getCommercialList, Local - " + chname)
            PATH = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('commercialsfolder'),chname,''))
            self.log("getCommercialList, Local - PATH = " + PATH)
            CommercialLST.extend(self.createDirectoryPlaylist(PATH, 100, 1, 100)) 
                    
        #Youtube
        elif CommercialsType == '2':   
            #Youtube - As Seen On TV
            if REAL_SETTINGS.getSetting('AsSeenOn') == 'true':
                self.log("getCommercialList, AsSeenOn") 
                CommercialLST.extend(self.createYoutubeFilelist('PL_ikfJ-FJg77ioZ9nPuhJxuMe9GKu7plT|PL_ikfJ-FJg774gky7eu8DroAqCR_COS79|PL_ikfJ-FJg75N3Gn6DjL0ZArAcfcGigLY|PL_ikfJ-FJg765O5ppOPGTpQht1LwXmck4|PL_ikfJ-FJg75wIMSXOTdq0oMKm63ucQ_H|PL_ikfJ-FJg77yht1Z6Xembod33QKUtI2Y|PL_ikfJ-FJg77PW8AJ3yk5HboSwWatCg5Z|PL_ikfJ-FJg75v4dTW6P0m4cwEE4-Oae-3|PL_ikfJ-FJg76zae4z0TX2K4i_l5Gg-Flp|PL_ikfJ-FJg74_gFvBqCfDk2E0YN8SsGS8|PL_ikfJ-FJg758W7GVeTVZ4aBAcCBda63J', '7', '200', '1', '200'))
            self.log("getCommercialList, Youtube") 
            CommercialLST.extend(self.createYoutubeFilelist(REAL_SETTINGS.getSetting('commercialschannel'), '2', '200', '2', '200'))
        
        #Internet
        elif CommercialsType == '3':
            self.log("getCommercialList, Internet") 
            CommercialLST.extend(self.InternetCommercial())
        return random.shuffle(CommercialLST) 
   
        
    def InternetCommercial(self):
        self.log("InternetCommercial")
        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Internet Commercials")     
        CommercialLST = []
        #todo add plugin parsing...
        if len(CommercialLST) > 0:
            random.shuffle(CommercialLST)
        return CommercialLST       

    
    def getTrailerList(self, chtype, chname):
        self.log("getTrailerList")
        TrailerLST = [] 
        TrailerTMPstrLST = []
        GenreChtype = False
        if chtype == '3' or chtype == '4' or chtype == '5':
            GenreChtype = True

        #Local
        if TrailersType == '1': 
            PATH = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('trailersfolder'),''))
            self.log("getTrailerList, Local - PATH = " + PATH)
            
            if FileAccess.exists(PATH):
                LocalFLE = ''
                LocalTrailer = ''
                LocalLST = self.walk(PATH)        
                for i in range(len(LocalLST)): 
                    try:   
                        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Local Trailers")
                        LocalFLE = LocalLST[i]
                        if '-trailer' in LocalFLE:
                            duration = self.getDuration(LocalFLE)
                            if duration > 0:
                                GenreLiveID = ['Trailer', 'bct', 0, 0, False, 1, 'NR', False, False, 0.0, 0]
                                TrailerTMPstrLST.append(self.makeTMPSTR(duration, chname, 0, 'Trailer', 'Trailer', GenreLiveID, LocalFLE, includeMeta=False))   
                        TrailerLST.extend(TrailerTMPstrLST)                                
                    except Exception,e:
                        self.log("getTrailerList failed! " + str(e), xbmc.LOGERROR)
                        
        #Kodi Library
        # if TrailersType == '2':
            # self.log("getTrailerList, Kodi Library")
            # json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":["genre","trailer","runtime"]}, "id": 1}')
            # json_detail = self.sendJSON(json_query)
            
            # if REAL_SETTINGS.getSetting('trailersgenre') == 'true' and GenreChtype == True:
                # JsonLST = ascii(json_detail.split("},{"))
                # match = [s for s in JsonLST if chname in s]
                
                # for i in range(len(match)):    
                    # self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Library Genre Trailers")
                    # duration = 120
                    # json = (match[i])
                    # trailer = json.split(',"trailer":"',1)[-1]
                    # if ')"' in trailer:
                        # trailer = trailer.split(')"')[0]
                    # else:
                        # trailer = trailer[:-1]
                    
                    # if trailer != '' or trailer != None or trailer != '"}]}':
                        # if 'http://www.youtube.com/watch?hd=1&v=' in trailer:
                            # trailer = trailer.replace("http://www.youtube.com/watch?hd=1&v=", self.youtube_player).replace("http://www.youtube.com/watch?v=", self.youtube_player)
                        # JsonTrailer = (str(duration) + ',' + trailer)
                        # if JsonTrailer != '120,':
                            # JsonTrailerLST.append(JsonTrailer)
                # TrailerLST.extend(JsonTrailerLST)
            
            # if self.youtube_player != 'False':

                # try:
                    # self.log('getTrailerList, json_detail using cache')


                    # else:
                        # JsonLST = (json_detail.split("},{"))
                        # match = [s for s in JsonLST if 'trailer' in s]
                        # for i in range(len(match)):                  
                            # self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Library Trailers")
                            # duration = 120
                            # json = (match[i])
                            # trailer = json.split(',"trailer":"',1)[-1]
                            # if ')"' in trailer:
                                # trailer = trailer.split(')"')[0]
                            # else:
                                # trailer = trailer[:-1]
                            # if trailer != '' or trailer != None or trailer != '"}]}':
                                # if 'http://www.youtube.com/watch?hd=1&v=' in trailer:
                                    # trailer = trailer.replace("http://www.youtube.com/watch?hd=1&v=", self.youtube_player).replace("http://www.youtube.com/watch?v=", self.youtube_player)
                                # JsonTrailer = (str(duration) + ',' + trailer)
                                # if JsonTrailer != '120,':
                                    # JsonTrailerLST.append(JsonTrailer)
                        # TrailerLST.extend(JsonTrailerLST)     
                # except Exception,e:
                    # self.log("getTrailerList failed! " + str(e), xbmc.LOGERROR)
                    
        # #Youtube
        # if TrailersType == '3':
            # self.log("getTrailerList, Youtube")
            # try:
                # YoutubeLST = self.createYoutubeFilelist(REAL_SETTINGS.getSetting('trailerschannel'), '2', '200', '2', '200')
                
                # for i in range(len(YoutubeLST)):    
                    # self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Youtube Trailers")
                    # Youtube = YoutubeLST[i]
                    # duration = Youtube.split(',')[0]
                    # trailer = Youtube.split('\n', 1)[-1]
                    
                    # if trailer != '' or trailer != None:
                        # YoutubeTrailer = (str(duration) + ',' + trailer)
                        # YoutubeTrailerLST.append(YoutubeTrailer)
                # TrailerLST.extend(YoutubeTrailerLST)
            # except Exception,e:
                # self.log("getTrailerList failed! " + str(e), xbmc.LOGERROR)
                
        # #Internet
        # if TrailersType == '4':
            # self.log("getTrailerList, Internet")
            # try:   
                # self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding Internet Trailers")
                # TrailerLST = self.InternetTrailer()
            # except Exception,e:
                # self.log("getTrailerList failed! " + str(e), xbmc.LOGERROR)
        # cleanup   
        del LocalTrailerLST[:]
        del JsonTrailerLST[:]
        del YoutubeTrailerLST[:]
        return TrailerLST
        
      
    def InternetTrailer(self, Cinema=False):
        self.log("InternetTrailer, Cinema = " + str(Cinema))
        TrailerLST = []
        duration = 0
        TrailersCount = 0
        
        if Cinema == 1:
            TRes = '720p'
            Ttype = 'coming_soon'
            Tlimit = 90
        elif Cinema == 2:
            TRes = '720p'
            Ttype = 'opening'
            Tlimit = 90
        else:
            TResNum = {}
            TResNum['0'] = '480p'
            TResNum['1'] = '720p'
            TResNum['2'] = '1080p'
            TRes = (TResNum[REAL_SETTINGS.getSetting('trailersResolution')])

            Ttypes = {}
            Ttypes['0'] = 'latest'
            Ttypes['1'] = 'most_watched'
            Ttypes['2'] = 'coming_soon'
            Ttype = (Ttypes[REAL_SETTINGS.getSetting('trailersHDnetType')])

            T_Limit = [15,30,90,180,270,360]
            Tlimit = T_Limit[int(REAL_SETTINGS.getSetting('trailersTitleLimit'))]
        
        try:
            InternetTrailersLST1 = []
            limit = Tlimit
            loop = int(limit/15)
            global page
            page = None
            movieLST = []
            source = Ttype
            resolution = TRes
            n = 0
            
            if source == 'latest':
                page = 1

                for i in range(loop):
                    movies, has_next_page = HDTrailers.get_latest(page=page)
                    if has_next_page:
                        page = page + 1

                        for i, movie in enumerate(movies):
                            movie_id = movie['id']
                            movieLST.append(movie_id)
                    else:
                        break

            elif source == 'most_watched':
                movies, has_next_page = HDTrailers.get_most_watched()
            elif source == 'coming_soon':
                movies, has_next_page = HDTrailers.get_coming_soon()
            elif source == 'opening':
                movies, has_next_page = HDTrailers.get_opening_this_week()

            if source != 'latest':
                for i, movie in enumerate(movies):
                    if n >= loop:
                        break
                    movie_id=movie['id']
                    movieLST.append(movie_id)
                    n += 1

            for i in range(len(movieLST)):
                movie, trailers, clips = HDTrailers.get_videos(movieLST[i])
                videos = []
                videos.extend(trailers)
                items = []

                for i, video in enumerate(videos):
                    if resolution in video.get('resolutions'):
                        source = video['source']
                        url = video['resolutions'][resolution]

                        if not 'http://www.hd-trailers.net/yahoo-redir.php' in url:
                            playable_url = HDTrailers.get_playable_url(source, url)
                            playable_url = playable_url.replace('plugin://plugin.video.youtube/?action=play_video&videoid=', self.youtube_player)
                            try:
                                tubeID = playable_url.split('videoid=')[1]
                                duration = self.getYoutubeDuration(tubeID)
                            except:
                                duration = 120
                            InternetTrailers = (str(duration) + ',' + str(playable_url))
                            TrailerLST.append(InternetTrailers)  
                            TrailersCount += 1
                            self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="querying %s Internet Trailers"%str(TrailersCount))
        except Exception,e:
            self.log("InternetTrailer failed! " + str(e))

        TrailerLST = sorted_nicely(TrailerLST)
        if TrailerLST and len(TrailerLST) > 0:
            random.shuffle(TrailerLST)
        return TrailerLST
    
    
    # Adapted from Ronie's screensaver.picture.slideshow * https://github.com/XBMC-Addons/screensaver.picture.slideshow/blob/master/resources/lib/utils.py    
    def walk(self, path, types=MEDIA_TYPES):     
        self.log("walk " + path + ' ,' + str(types))
        video = []
        folders = []
        # multipath support
        if path.startswith('multipath://'):
            # get all paths from the multipath
            paths = path[12:-1].split('/')
            for item in paths:
                folders.append(urllib.unquote_plus(item))
        else:
            folders.append(os.path.join(path,''))
        for folder in folders:
            if FileAccess.exists(xbmc.translatePath(folder)):
                # get all files and subfolders
                dirs,files = FileAccess.listdir(folder)
                print dirs, files
                # natural sort
                convert = lambda text: int(text) if text.isdigit() else text
                alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
                files.sort(key=alphanum_key)
                for item in files:
                    # filter out all video
                    if os.path.splitext(item)[1].lower() in types:
                        video.append(os.path.join(folder,item))
                for item in dirs:
                    # recursively scan all subfolders
                    video += self.walk(os.path.join(folder,item)) # make sure paths end with a slash
        # cleanup   
        del folders[:]
        return video
        
        
    #Parse Plugin, return essential information. Not tmpstr
    def PluginInfo(self, path):
        self.log("PluginInfo") 
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","properties":["genre","runtime","description"]},"id":1}' % path)
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        Detail = ''
        DetailLST = []
        PluginName = os.path.split(path)[0]

        #run through each result in json return
        for f in (file_detail):
            filetype = re.search('"filetype" *: *"(.*?)"', f)
            label = re.search('"label" *: *"(.*?)"', f)
            genre = re.search('"genre" *: *"(.*?)"', f)
            runtime = re.search('"runtime" *: *([0-9]*?),', f)
            description = re.search('"description" *: *"(.*?)"', f)
            file = re.search('"file" *: *"(.*?)"', f)

            #if core values have info, proceed
            if filetype and file and label:
                filetype = filetype.group(1)
                title = (label.group(1)).replace(',',' ')
                file = file.group(1)

                try:
                    genre = genre.group(1)
                except:
                    genre = 'Unknown'
                    pass

                if genre == '':
                    genre = 'Unknown'

                try:
                    runtime = runtime.group(1)
                except:
                    runtime = 0
                    pass

                if runtime == 0 or runtime == '':
                    runtime = 1800

                try:
                    description = (description.group(1)).replace(',',' ')
                except:
                    description = PluginName
                    pass

                if description == '':
                    description = PluginName

                if title != '':
                    Detail = ((filetype + ',' + title + ',' + genre + ',' + str(runtime) + ',' + description + ',' + file)).replace(',,',',')
                    DetailLST.append(Detail)                    
        return DetailLST

        
    # Run rules for a channel
    def runActions(self, action, channel, parameter):
        self.log("runActions " + str(action) + " on channel " + str(channel))
        if channel < 1:
            return

        self.runningActionChannel = channel
        index = 0

        for rule in self.channels[channel - 1].ruleList:
            if rule.actions & action > 0:
                self.runningActionId = index
                self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="processing rule " + str(index + 1))
                parameter = rule.runAction(action, self, parameter)
            index += 1
        
        self.runningActionChannel = 0
        self.runningActionId = 0
        return parameter


    def threadPause(self):
        if threading.activeCount() > 1:
            while self.threadPaused == True and self.myOverlay.isExiting == False:
                time.sleep(self.sleepTime)
                
            # This will fail when using config.py
            try:
                if self.myOverlay.isExiting == True:
                    self.log("IsExiting")
                    return False
            except Exception,e:
                pass
        return True


    def escapeDirJSON(self, dir_name):
        mydir = uni(dir_name)
        if (mydir.find(":")):
            mydir = mydir.replace("\\", "\\\\")
        return mydir


    def getSmartPlaylistType(self, dom):
        self.log('getSmartPlaylistType')

        try:
            pltype = dom.getElementsByTagName('smartplaylist')
            return pltype[0].attributes['type'].value
        except Exception,e:
            self.log("Unable to get the playlist type.", xbmc.LOGERROR)
            return ''

     
    def readXMLTV(self, filename):
        self.log('readXMLTV')  
        readXMLTV = []
        # try:
        if filename[0:4] == 'http':
            self.log("findZap2itID, filename http = " + filename)
            f = open_url(filename)
        else:              
            self.log("findZap2itID, filename local = " + filename)
            f = FileAccess.open(filename, "r")
            f.seek(0,0)
            
        context = ET.iterparse(f, events=("start", "end"))
        context = iter(context)
        event, root = context.next()
        for event, elem in context:
            if event == "end":
                if elem.tag == "channel":
                    id = ascii(elem.get("id"))
                    for title in elem.findall('display-name'):
                        name = ascii(title.text.replace('<display-name>','').replace('</display-name>','').replace('-DT','DT').replace(' DT','DT').replace('DT','').replace('-HD','HD').replace(' HD','HD').replace('HD','').replace('-SD','SD').replace(' SD','SD').replace('SD','').replace("'",'').replace(')',''))
                        readXMLTV.append(name+' : '+id)
        f.close()
        return readXMLTV
        # except Exception,e:
            # f.close()
            # try:
                # for key in xmltv.read_channels(FileAccess.open(filename, 'r')):
                    # name = map(itemgetter(0), key['display-name'])
                    # id   = key['id']
                    # name = name[0]
                    # readXMLTV.append(name+' : '+id)
                # return readXMLTV
            # except Exception,e:
                # pass
        # self.log("readXMLTV, failed! " + str(e))
        # return ['XMLTV ERROR : IMPROPER FORMATING']

                
    def findZap2itID(self, CHname, xmlflename):
        self.log("findZap2itID, CHname = " + CHname)
        orgCHname = CHname
        fuzzyCHname = (CHname.upper()).replace('HD','')
        CHmatchLST = [CHname, fuzzyCHname, orgCHname]
        
        if xmlflename.startswith('http://mobilelistings.tvguide.com'):
            return CHname, CHname
        
        elif xmlflename in ['pvr','hdhomerun','ustvnow']:
            NameLst = []
            if xmlflename == 'pvr':
                if not self.PVRList:
                    self.fillPVR()
                NameLst, PathLst, IconLst = self.PVRList
            elif xmlflename == 'hdhomerun':
                if not self.HDHRList:
                    self.fillHDHR()
                NameLst, PathLst, IconLst = self.HDHRList
            elif xmlflename == 'ustvnow':
                if not self.USTVList:
                    self.fillUSTV()
                NameLst, PathLst, IconLst = self.USTVList
            
            for i in range(len(NameLst)):
                CHid, dnameID = (self.cleanLabels(NameLst[i])).split(' - ')
                if CHname.lower() == dnameID.lower():
                    return CHname, CHid
          
        else:        
            XMLTVMatchlst = []
            sorted_XMLTVMatchlst = []
            found = False

                    
            try:
                show_busy_dialog()
                XMLTVMatchlst = self.readXMLTV(xmlflename)
                try:
                    CHnum = int(CHname.split(' ')[0])
                    CHname = (CHname.split(' ')[1]).upper()
                except:
                    CHnum = 0
                
                CHname = CHname.replace('-DT','DT').replace(' DT','DT').replace('DT','').replace('-HD','HD').replace(' HD','HD').replace('HD','').replace('-SD','SD').replace(' SD','SD').replace('SD','')
                matchLST = [CHname, 'W'+CHname, CHname+'HD', CHname+'DT', str(CHnum)+' '+CHname, orgCHname.upper(), 'W'+orgCHname.upper(), orgCHname.upper()+'HD', orgCHname.upper()+'DT', str(CHnum)+' '+orgCHname.upper(), orgCHname]
                self.log("findZap2itID, Cleaned CHname = " + CHname)
                
                sorted_XMLTVMatchlst = sorted_nicely(XMLTVMatchlst)
                for n in range(len(sorted_XMLTVMatchlst)):
                    try:
                        CHid = '0'
                        found = False
                        dnameID = sorted_XMLTVMatchlst[n]
                        dname = dnameID.split(' : ')[0]
                        CHid = dnameID.split(' : ')[1]

                        if dname.upper() in matchLST: 
                            found = True
                            hide_busy_dialog()
                            return orgCHname, CHid
                    except:
                        hide_busy_dialog()
                        
                if not found:
                    hide_busy_dialog()
                    XMLTVMatchlst = []

                    for s in range(len(sorted_XMLTVMatchlst)):
                        try:
                            dnameID = sorted_XMLTVMatchlst[s]
                            dname = dnameID.split(' : ')[0]
                            CHid = dnameID.split(' : ')[1]
                                            
                            try:
                                CHid = CHid.split(', icon')[0]
                            except:
                                pass
                                
                            line = '[COLOR=blue][B]'+dname+'[/B][/COLOR] : ' + CHid
                            if dname[0:3] != 'en':
                                XMLTVMatchlst.append(line)
                        except:
                            hide_busy_dialog()
                            pass
                            
                    if XMLTVMatchlst:
                        select = selectDialog(XMLTVMatchlst, 'Select matching id to [B]%s[/B]' % orgCHname)
                        if select != -1:
                            dnameID = self.cleanString(XMLTVMatchlst[select])
                            CHid = dnameID.split(' : ')[1]
                            dnameID = dnameID.split(' : ')[0]
                            return dnameID, CHid
                        else:
                            return CHname, '0'
            except Exception,e:
                hide_busy_dialog()
                self.log("findZap2itID, failed! " + str(e))
            
            
    def ListTuning(self, type, url, Random=False):
        # todo write proper parsers for m3u,xml,plx
        self.log('ListTuning')
        show_busy_dialog()
        SortIPTVList = []
        TMPIPTVList = []
        IPTVNameList = []
        IPTVPathList = []
        lst = []
        
        try:
            if url[0:4] == 'http':
                f = force_url(url)
                lst = f.readlines()
            else:
                f = FileAccess.open(url, "r")
                lst = f.readlines()
            f.close()
        except:
            pass
                
        if len(lst) == 0:
            return 
        lst = removeStringElem(PLXlst)

        if type == 'M3U':
            TMPIPTVList = self.IPTVtuning(lst)
        elif type == 'XML':
            TMPIPTVList = self.LSTVtuning(lst)
        elif type == 'PLX':
            TMPIPTVList = self.PLXtuning(lst)
        
        if len(TMPIPTVList) == 0:
            SortIPTVList = ['This list is empty or unavailable@#@ ']
        elif Random == True:
            SortIPTVList = TMPIPTVList
            random.shuffle(SortIPTVList)
        else:
            SortIPTVList = sorted_nicely(TMPIPTVList)

        for n in range(len(SortIPTVList)):
            if SortIPTVList[n] != None:
                IPTVNameList.append((SortIPTVList[n]).split('@#@')[0])   
                IPTVPathList.append((SortIPTVList[n]).split('@#@')[1])
        
        hide_busy_dialog()
        # cleanup   
        del SortIPTVList[:]
        del TMPIPTVList[:]
        return IPTVNameList, IPTVPathList

   
    def IPTVtuning(self, IPTVlst):
        self.log('IPTVtuning')   
        IPTVlist = ['M3U ERROR!! List Empty or Malformed!@#@ ']
        for iptv in range(len(IPTVlst)):
            if IPTVlst[iptv].startswith('#EXTINF:'):
                try:
                    title = (IPTVlst[iptv].split(',',1)[1]).replace('\r','').replace('\t','').replace('\n','')
                    link = (IPTVlst[iptv + 1]).replace('\r','').replace('\t','').replace('\n','')
                    channelid = title
                    title = title + ' IPTV'

                    if link[0:4] != 'http' and link[0:4] != 'rtmp' and link[0:4] != 'rtsp' and link[0:6] != 'plugin':
                        raise
                    IPTVlist.append(title+'@#@'+link)
                except:
                    pass
        return IPTVlist
        

    def LSTVtuning(self, LSTVlst):
        self.log('LSTVtuning') 
        LSTVlist = ['XML ERROR!! List Empty or Malformed!@#@ ']
        for lstv in range(len(LSTVlst)):
            if LSTVlst[lstv].startswith('<title>'):
                try:
                    title = (LSTVlst[lstv]).replace('\r','').replace('\t','').replace('\n','').replace('<title>','').replace('</title>','')
                    title = title + ' XML'

                    if LSTVlst[lstv+1].startswith('<link>'):
                        link = (LSTVlst[lstv+1]).replace('\r','').replace('\t','').replace('\n','').replace('<link>','').replace('</link>','')

                        if link[0:4] != 'http' and link[0:4] != 'rtmp' and link[0:4] != 'rtsp' and link[0:6] != 'plugin':
                            raise

                        if LSTVlst[lstv+2].startswith('<thumbnail>'):
                            logo = (LSTVlst[lstv+2]).replace('\r','').replace('\t','').replace('\n','').replace('<thumbnail>','').replace('</thumbnail>','')
                            
                            if logo[0:4] == 'http':
                                GrabLogo(logo, title)
                    LSTVlist.append(title+'@#@'+link)
                except:
                    pass
        return LSTVlist
    

    def PLXtuning(self, PLXlst):
        self.log('PLXtuning')
        PLXlist = ['PLX ERROR!! List Empty or Malformed!@#@ ']
        for PLX in range(len(PLXlst)):
            if 'name=' in PLXlst[PLX]:
                try:
                    title = (str(PLXlst[PLX])).replace('\r','').replace('\t','').replace('\n','').replace('name=','')
                    try:
                        title = title.split('  ')[0]
                    except:
                        pass
                    title = title + ' PLX'
                    
                    if 'thumb=' in PLXlst[PLX+1]:
                        logo = (PLXlst[PLX + 1]).replace('\r','').replace('\t','').replace('\n','').replace('thumb=','')
                        
                        if logo[0:4] == 'http':
                            GrabLogo(logo, title)
                            
                    if 'URL=' in PLXlst[PLX+2]:
                        link = (PLXlst[PLX + 2]).replace('\r','').replace('\t','').replace('\n','').replace('URL=','')
                        if link[0:4] != 'http' and link[0:4] != 'rtmp' and link[0:4] != 'rtsp':
                            raise
                    PLXlist.append(title+'@#@'+link)
                except:
                    pass
        return PLXlist

        
    def fillPluginList(self):
        self.log('fillPluginList')
        json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.addon.video","properties":["name","path","thumbnail"]}, "id": 1 }')
        json_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        pluginNameList = []
        pluginPathList = []
        pluginIconList = []
        try:
            for f in detail:
                names = re.search('"name" *: *"(.*?)",', f)
                paths = re.search('"addonid" *: *"(.*?)",', f)
                thumbs = re.search('"thumbnail" *: *"(.*?)",', f)
                if names and paths:
                    name = self.cleanLabels(names.group(1))
                    path = paths.group(1)
                    thumb = thumbs.group(1)
                    if name.lower() not in GETADDONS_FILTER:
                        pluginNameList.append(name)  
                        pluginPathList.append(path)  
                        pluginIconList.append(thumb)  
            self.pluginList = [pluginNameList, pluginPathList, pluginIconList]
        except Exception,e:
            self.log("fillPluginList, failed! " + str(e))
        if len(self.pluginList) == 0:
            self.pluginList = ['No Kodi plugins unavailable!']
    

    def getPVRChannels(self):
        self.log("getPVRChannels")
        Channels = []
        json_detail = self.sendJSON('{"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":"alltv","properties":["thumbnail","channel"]},"id":2}')
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        for f in file_detail:
            try:
                CHids = re.search('"channelid" *: *(.*?),', f)
                if CHids and len(CHids.group(1)) > 0:
                    CHnames = re.search('"label" *: *"(.*?)"', f)
                    CHthmbs = re.search('"thumbnail" *: *"(.*?)"', f)
                    Channels.append([CHids.group(1),CHnames.group(1),(unquote(CHthmbs.group(1))).replace("image://",'')])
            except:
                pass
        return Channels
        
        
    def getPVRLink(self, channel):
        self.log('getPVRLink')
        try:
            if getXBMCVersion() < 14:
                PVRverPath = "pvr://channels/tv/All TV channels/"
            else:
                PVRverPath = "pvr://channels/tv/All channels/"   
            PVRPath = FileAccess.listdir(PVRverPath)
            return os.path.join(PVRverPath,PVRPath[1][channel])
        except:
            pass
            
  
  
    def fillPVR(self):
        self.log('fillPVR')
        PVRNameList = []
        PVRPathList = []
        PVRIconList = []
        PVRChannels = self.getPVRChannels()
        for i in range(len(PVRChannels)):
            PVRNameList.append(('[COLOR=blue][B]%s[/B][/COLOR] - %s') % (PVRChannels[i][0], self.cleanLabels(PVRChannels[i][1])))
            PVRPathList.append(self.getPVRLink(i))
            PVRIconList.append(PVRChannels[i][2])
        if len(PVRNameList) == 0:
            PVRNameList = ['Kodi PVR is empty or unavailable!']
        self.PVRList = [PVRNameList, PVRPathList, PVRIconList]

        
    def getUSTVChannels(self):
        self.log('getUSTVChannels')
        Channels = []
        detail = uni(self.requestList('plugin://'+isUSTVnow()+'/?mode=live'))
        for ustv in detail:
            files = re.search('"file" *: *"(.*?)",', ustv)
            filetypes = re.search('"filetype" *: *"(.*?)",', ustv)
            labels = re.search('"label" *: *"(.*?)",', ustv)
            icons = re.search('"thumbnail" *: *"(.*?)",', ustv)
            if filetypes and labels and files:
                Channels.append([(self.cleanLabels(labels.group(1))).split(' - ')[0],(files.group(1).replace("\\\\", "\\")),(unquote(icons.group(1))).replace("image://",'')])
        return Channels
        
        
    def fillUSTV(self):
        self.log('fillUSTV')
        USTVNameList = []
        USTVPathList = []
        USTVIconList = []
        USTVChannels = self.getUSTVChannels()
        for i in range(len(USTVChannels)):
            USTVNameList.append(('[COLOR=blue][B]%s[/B][/COLOR] - %s') % (USTVChannels[i][0], self.cleanLabels(USTVChannels[i][0])))
            USTVPathList.append(USTVChannels[i][1])
            USTVIconList.append(USTVChannels[i][2])
        if len(USTVNameList) == 0:
            USTVNameList = ['USTVnow is empty or unavailable!']
        self.USTVList = [USTVNameList, USTVPathList, USTVIconList]

              
    def fillFavourites(self):
        self.log('fillFavourites')
        json_query = ('{"jsonrpc":"2.0","method":"Favourites.GetFavourites","params":{"properties":["path","thumbnail"]},"id":1}')
        json_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        TMPfavouritesList = []
        FavouritesNameList = []
        FavouritesPathList = []
        try:
            for f in detail:
                paths = re.search('"path" *: *"(.*?)",', f)
                names = re.search('"title" *: *"(.*?)",', f)
                types = re.search('"type" *: *"(.*?)"', f)
                if types != None and len(types.group(1)) > 0:
                    type = types.group(1)
                    if names and paths:
                        name = self.cleanLabels(names.group(1))
                        if type.lower() == 'media':
                            path = paths.group(1)
                            TMPfavouritesList.append(name+'@#@'+path) 
            SortedFavouritesList = sorted_nicely(TMPfavouritesList)
            for i in range(len(SortedFavouritesList)):  
                # append as string element for quick sorting; todo dict, sort using keys.
                FavouritesNameList.append((SortedFavouritesList[i]).split('@#@')[0])  
                FavouritesPathList.append((SortedFavouritesList[i]).split('@#@')[1])          
        except Exception,e:
            self.log("fillFavourites, failed! " + str(e))

        if len(TMPfavouritesList) == 0:
            FavouritesNameList = ['Kodi Favorites is empty or unavailable!']
        self.FavouritesList = [FavouritesNameList, FavouritesPathList]
        
        
    def fillExternalList(self, type, source='', list='Community', Random=False):
        self.log('fillExternalList')
        if isCompanionInstalled == True:
            try:
                fillLST = eval(getProperty("PTVL.%s.%s.fillLst" %(list, source)))
                if Random == True:
                    shuffle(fillLST)
            except:
                fillLST = []
            return fillLST

            
    def getHDHRChannels(self, favorite=False):
        self.log("getHDHRChannels")
        DupChk = []
        Channels = []
        FavChannels = []
        list = ''
        devices = hdhr.discover()
        for i in range(len(devices)):
            url = (str(devices[i]).split(':url=')[1]).replace('>','')
            try:
                list = list + open_url(url).read()
            except:
                pass
            file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(list)
            for f in file_detail:
                fav = False
                drm = False
                try:
                    match = re.search('"GuideName" *: *"(.*?)",', f)    
                    if match and len(match.group(1)) > 0:
                        chname = match.group(1)
                        links = re.search('"URL" *: *"(.*?)"', f)
                        chnums = re.search('"GuideNumber" *: *"([\d.]*\d+)"', f)
                        favs = re.search('"Favorite" *: *([\d.]*\d+)', f)
                        drms = re.search('"DRM" *: *([\d.]*\d+)', f)

                        if links != None and len(links.group(1)) > 0:
                            link = links.group(1)

                        if chnums != None and len(chnums.group(1)) > 0:
                            chnum = chnums.group(1)

                        if favs != None and len(favs.group(1)) > 0:
                            fav = bool(favs.group(1))
                            
                        if drms != None and len(drms.group(1)) > 0:
                            drm = bool(drms.group(1))
                                        
                        if fav == True and chname not in DupChk:
                            DupChk.append(chname)
                            FavChannels.append([chnum,chname,fav,drm,link])
                        Channels.append([chnum,chname,fav,drm,link])
                except:
                    pass
        del DupChk[:]
        if favorite == True:
            return FavChannels
        else:
            return Channels
         
                    
    def fillHDHR(self,favorite=False):
        self.log("fillHDHR")
        Favlist = []
        HDHRNameList = []
        HDHRPathList  = []
        HDHRIconList = []
        HDHRChannels = self.getHDHRChannels(favorite)
        HDHRChannelList = hdhr.getChannelList()
        for i in range(len(HDHRChannels)):
            chnum = HDHRChannels[i][0]
            chname = self.cleanLabels(HDHRChannels[i][1])
            fav = HDHRChannels[i][2]
            drm = HDHRChannels[i][3]
            link = HDHRChannels[i][4]
            chid = link.split('/v')[1]
            
            for n in HDHRChannelList:
                if chid == n['chid']:
                    if len(n['chname']) > 0:
                        chname = n['chname']
                    icon  = n['chlogo']
                    break
                    
            if fav == True:
                chname = chname+'[COLOR=gold] [Favorite][/COLOR]'
            if drm == True:
                chname = chname+'[COLOR=red] [DRM][/COLOR]' 
            chname = '[COLOR=blue][B]'+chnum+'[/B][/COLOR] - ' + chname
            
            HDHRNameList.append(chname)
            HDHRPathList.append(link)
            HDHRIconList.append(icon)
            
        # cleanup
        del HDHRChannels[:]
        del HDHRChannelList[:]
        self.HDHRList = [HDHRNameList, HDHRPathList, HDHRIconList]

        
    def sbManaged(self, tvdbid):
        self.log("sbManaged")
        sbManaged = False
        if REAL_SETTINGS.getSetting('sickbeard.enabled') == "true":
            try:
                sbManaged = self.sbAPI.isShowManaged(tvdbid)
            except Exception,e:
                self.log("sbManaged, failed! " + str(e))
        return sbManaged


    def cpManaged(self, title, imdbid):
        self.log("cpManaged")
        cpManaged = False
        if REAL_SETTINGS.getSetting('couchpotato.enabled') == "true":
            try:
                r = str(self.cpAPI.getMoviebyTitle(title))
                r = r.split("u'")
                match = [s for s in r if imdbid in s][1]
                if imdbid in match:
                    cpManaged = True
            except Exception,e:
                self.log("cpManaged, failed! " + str(e))
        return cpManaged
        
        
    def getTVDBIDbyZap2it(self, dd_progid):
        try:
            tvdbid = self.tvdbAPI.getIdByZap2it(dd_progid)
        except Exception,e:
            tvdbid = '0'
            self.log("getTVDBIDbyZap2it, failed! " + str(e))
        self.log("getTVDBIDbyZap2it, tvdbid = " + tvdbid)
        return tvdbid
        

    def getVimeoMeta(self, VMID):
        self.log('getVimeoMeta')
        api = 'http://vimeo.com/api/v2/video/%s.xml' % VMID
        title = ''
        description = ''
        duration = 0
        thumburl = 0
        try:
            dom = parseString(read_url_cached(api))
            xmltitle = dom.getElementsByTagName('title')[0].toxml()
            title = xmltitle.replace('<title>','').replace('</title>','')
            xmldescription = dom.getElementsByTagName('description')[0].toxml()
            description = xmldescription.replace('<description>','').replace('</description>','')
            xmlduration = dom.getElementsByTagName('duration')[0].toxml()
            duration = int(xmlduration.replace('<duration>','').replace('</duration>',''))
            thumbnail_large = dom.getElementsByTagName('thumbnail_large')[0].toxml()
            thumburl = thumbnail_large.replace('<thumbnail_large>','').replace('</thumbnail_large>','')
            dbid = encodeString(thumburl)
        except:
            pass
        return title, description, duration, dbid

            
    def getYoutubeMeta(self, stars, year, duration, description, title, SEtitle, id, genre, rating, playcount, hd, cc):
        self.log('getYoutubeMeta ' + id)
        detail = self.getYoutubeDetails(id)
        for f in detail:
            cats = {0 : 'NR',
                    1 : 'Film & Animation',
                    2 : 'Autos & Vehicles',
                    10 : 'Music',
                    15 : 'Pets & Animals',
                    17 : 'Sports',
                    18 : 'Short Movies',
                    19 : 'Travel & Events',
                    20 : 'Gaming',
                    21 : 'Videoblogging',
                    22 : 'People & Blogs',
                    23 : 'Comedy',
                    24 : 'Entertainment',
                    25 : 'News & Politics',
                    26 : 'Howto & Style',
                    27 : 'Education',
                    28 : 'Science & Technology',
                    29 : 'Nonprofits & Activism',
                    30 : 'Movies',
                    31 : 'Anime/Animation',
                    32 : 'Action/Adventure',
                    33 : 'Classics',
                    34 : 'Comedy',
                    35 : 'Documentary',
                    36 : 'Drama',
                    37 : 'Family',
                    38 : 'Foreign',
                    39 : 'Horror',
                    40 : 'Sci-Fi/Fantasy',
                    41 : 'Thriller',
                    42 : 'Shorts',
                    43 : 'Shows',
                    44 : 'Trailers'}
            try:
                contentDetail = re.search('"contentDetails" *:', f)
                if contentDetail:
                    durations = re.search('"duration" *: *"(.*?)",', f)
                    definitions = re.search('"definition" *: *"(.*?)",', f)
                    captions = re.search('"caption" *: *"(.*?)",', f)
                    duration = self.parseYoutubeDuration((durations.group(1) or duration))
                    
                    if definitions and len(definitions.group(1)) > 0:
                        hd = (definitions.group(1)) == 'hd'
                        
                    if captions and len(captions.group(1)) > 0:
                        cc = (captions.group(1)) == 'true'

                categoryIds = re.search('"categoryId" *: *"(.*?)",', f)
                if categoryIds and len(categoryIds.group(1)) > 0:
                    genre = cats[int(categoryIds.group(1))]
                        
                chname = ''
                channelTitles = re.search('"channelTitle" *: *"(.*?)",', f)
                if channelTitles and len(channelTitles.group(1)) > 0:
                    chname = channelTitles.group(1)

                items = re.search('"items" *:', f)
                if items:
                    titles = re.search('"title" *: *"(.*?)",', f)
                    descriptions = re.search('"description" *: *"(.*?)",', f)
                    publisheds = re.search('"publishedAt" *: *"(.*?)",', f)

                    if titles and len(titles.group(1)) > 0:
                        title = (titles.group(1) or title)
                    if descriptions and len(descriptions.group(1)) > 0:
                        description = ((descriptions.group(1) or description).split('http')[0]).replace('\\n',' ')
                    if publisheds and len(publisheds.group(1)) > 0:
                        published = (publisheds.group(1) or '')
                        
                        if year == 0:
                            year = int(published[0:4])

                    if not description:
                        description = title

                statistics = re.search('"statistics" *:', f)
                if statistics:
                    if stars == 0.0:
                        try:
                            viewCounts = re.search('"viewCount" *: *"(.*?)",', f)
                            likeCounts = re.search('"likeCount" *: *"(.*?)",', f)
                            dislikeCounts = re.search('"dislikeCount" *: *"(.*?)",', f)
                            likeCount = int(likeCounts.group(1) or '0')
                            dislikeCount = int(dislikeCounts.group(1) or '0')
                            V = likeCount + dislikeCount
                            R = likeCount - dislikeCount
                            stars = float((((V * R)) / (V))/100)/5
                        except:
                            stars = 0.0
            except Exception,e:
                self.log('getYoutubeMeta, failed! ' + str(e))

        self.log("getYoutubeMeta, return")
        return stars, year, duration, description, title, 'Youtube - ' + chname, id, genre, rating, playcount, hd, cc
        
        
    def getMovieMeta(self, stars, year, duration, plot, title, tagline, imdb_id, genre, rating, playcount):
        self.log("getMovieMeta")
        if ENHANCED_DATA == True: 
            try:
                meta = metaget.get_meta('movie', title, str(year))
                year     = int(year                                 or (meta['year']               or '0'))
                duration = int(duration                             or (meta['duration']           or ''))
                plot     = uni(plot                                 or (meta['plot']               or ''))
                title    = uni(title                                or (meta['title']              or ''))
                tagline  = uni(tagline                              or (meta['tagline']            or ''))
                imdb_id  = uni(meta['imdb_id']                      or imdb_id                     or '0')
                playcount= int(playcount                            or (meta['playcount']          or '1'))
                stars    = float(meta['rating']                     or stars                       or '0.0')
                genre    = uni(meta['genre'].split(',')[0]          or genre                       or 'Unknown')
                rating   = uni(meta['mpaa']                         or rating                      or 'NR')
            except:
                pass
        self.log("getMovieMeta, return = " + str(stars) +','+ str(year) +','+ str(duration) +','+ plot +','+ title +','+ tagline +','+ imdb_id +','+ genre +','+ rating +','+ str(playcount))
        return stars, year, duration, plot, title, tagline, imdb_id, genre, rating, playcount
        
        
    def getTVmeta(self, stars, year, duration, plot, title, tagline, tvdb_id, genre, rating, playcount):
        self.log("getTVmeta")
        if ENHANCED_DATA == True: 
            try:
                meta = metaget.get_meta('tvshow', title, str(year))
                year     = int(year                                 or (meta['year']               or '0'))
                duration = int(duration                             or (meta['duration']           or ''))
                plot     = uni(plot                                 or (meta['plot']               or ''))
                title    = uni(title                                or (meta['title']              or ''))
                tvdb_id  = uni(meta['tvdb_id']                      or tvdb_id                     or '0')
                playcount= int(playcount                            or (meta['playcount']          or '1'))
                stars    = float(meta['rating']                     or stars                       or '0.0')
                genre    = uni(meta['genre'].split(',')[0]          or genre                       or 'Unknown')
                rating   = uni(meta['mpaa']                         or rating                      or 'NR')
            except:
                pass
        self.log("getTVmeta, return = " + str(stars) +','+ str(year) +','+ str(duration) +','+ plot +','+ title +','+ tagline +','+ tvdb_id +','+ genre +','+ rating +','+ str(playcount))
        return stars, year, duration, plot, title, tagline, tvdb_id, genre, rating, playcount

            
    def getActivePlayer(self):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        id = 1
        for f in detail:
            playerid  = re.search('"playerid" *: *([0-9]*?),', f)
            if playerid:
                try:
                    id = int(playerid.group(1))
                except:
                    id = 1
        self.log("getActivePlayer, id = " + str(id)) 
        return id
    
            
    def requestItem(self, file, fletype='video'):
        self.log("requestItem") 
        json_query = ('{"jsonrpc":"2.0", "method": "Player.GetItem", "params": {"playerid":%d,"properties":["thumbnail","fanart","title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid","rating"]}, "id": 1}' %self.getActivePlayer())
        json_folder_detail = self.sendJSON(json_query)
        print re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        return re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
           
           
    def requestList(self, path, fletype='video'):
        self.log("requestList") 
        json_query = ('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "properties":["thumbnail","fanart","title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid","rating"]}, "id": 1}' % (self.escapeDirJSON(path), fletype))
        json_folder_detail = self.sendJSON(json_query)
        return re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)      
 
 
    # filelist cache may be redundant to m3u
    def getFileListCache(self, chtype, channel, purge=False):
        cachetype = str(chtype) + ':' + str(channel)
        try:
            if chtype <= 7 or chtype == 12:
                life = SETTOP_REFRESH
            elif chtype == 8:
                life = LIVETV_MAXPARSE
            else:
                life = PLUGIN_REFRESH
            life = (((float(life - 900)/60)/60))
            #Set Life of cache in hours, value needs to expire before hourly refresh.
            self.FileListCache = StorageServer.StorageServer(("plugin://script.pseudotv.live/%s" % cachetype),life)
            self.log("getFileListCache, cachetype = " + cachetype + ', life = ' + str(life) + ', purge = ' + str(purge))
            if purge == True:
                self.FileListCache.delete("%")
        except:
            self.FileListCache = ''

         
    def clearFileListCache(self, chtype=9999, channel=9999):
        self.log("clearFileListCache")
        if chtype == 9999 and channel == 9999:
            for n in range(CHANNEL_LIMIT):
                for i in range(NUMBER_CHANNEL_TYPES):
                    try:
                        self.getFileListCache(i+1, n+1, True)
                    except:
                        pass
            return True
        else:
            self.getFileListCache(chtype, channel, True)
            return True
            

    def getFileList(self, file_detail, channel, limit, excludeLST=[]):
        self.log('getFileList')
        # if CACHE_ENABLED == True:
            # try:
                # result = self.FileListCache.cacheFunction(self.getFileList_NEW, file_detail, channel, limit, excludeLST)
            # except:
                # result = self.getFileList_NEW(file_detail, channel, limit, excludeLST)
        # else:
        result = self.getFileList_NEW(file_detail, channel, limit, excludeLST)
        return result  
        
        
    def getFileList_NEW(self, file_detail, channel, limit, excludeLST=[]):
        self.log("getFileList_NEW, channel = " + str(channel) + " ,limit = " + str(limit) + " ,excludeLST = " + str(excludeLST))
        fileList = []
        seasoneplist = []
        dirlimit = limit

        #listitems return parent items during error, catch repeat list and return.
        if file_detail == self.file_detail_CHK:
            return
        else:
            self.file_detail_CHK = file_detail
        
        for f in file_detail:
            if self.threadPause() == False:
                del fileList[:]
                break
                                                                 
            if self.filecount >= limit:
                break
                   
            try:
                tmpstr = ''
                durParsed = False
                files = re.search('"file" *: *"(.*?)",', f)               
                if files:
                    if not files.group(1).startswith(("plugin", "upnp")) and (files.group(1).endswith("/") or files.group(1).endswith("\\")):
                        fileList.extend(self.getFileList(files.group(1), channel, limit, excludeLST))
                    else:
                        f = self.runActions(RULES_ACTION_JSON, channel, f)
                        filetypes = re.search('"filetype" *: *"(.*?)",', f)
                        labels = re.search('"label" *: *"(.*?)",', f)
                        
                        #if core variables, proceed
                        if filetypes and labels:
                            filetype = filetypes.group(1)
                            file = (files.group(1).replace("\\\\", "\\"))
                            label = self.cleanLabels(labels.group(1))

                            if label and label.lower() not in excludeLST:
                                self.log("getFileList_NEW, label = " + label)
                                self.log("getFileList_NEW, file = " + ascii(file))
                                if file.startswith('plugin://plugin.program.super.favourites'):
                                    file = urllib.unquote('plugin://plugin'+file.split('plugin')[4]).replace('",return)','')
                                            
                                if filetype == 'file' and self.filecount < limit:
                                    runtime  = re.search('"runtime" *: *([0-9]*?),', f)
                                    duration = re.search('"duration" *: *([0-9]*?),', f)
                                    
                                    # If duration, else 0
                                    try:
                                        dur = int(duration.group(1))
                                        self.log('getFileList_NEW, using duration = ' + str(dur))
                                    except Exception,e:
                                        self.log('getFileList_NEW, no duration found! ' + str(e))
                                        dur = 0
                                       
                                    if dur == 0:
                                        # Less accurate duration
                                        try:
                                            dur = int(runtime.group(1))
                                            self.log('getFileList_NEW, using runtime = ' + str(dur))
                                        except Exception,e:
                                            self.log('getFileList_NEW, no runtime found! ' + str(e))
                                            dur = 0

                                    if dur == 0:
                                        self.log('getFileList_NEW, parsing for accurate duration')
                                        if not file.startswith(("plugin", "upnp")):
                                            dur = self.getDuration(file)
                                            durParsed = True
                                            
                                    if dur == 0 and (file.startswith(("plugin", "upnp")) or file[-4:].lower() == 'strm'):
                                        #add a static duration rather then ignore content.
                                        self.log('getFileList_NEW, plugin/upnp/strm setting default duration')
                                        dur = 3600
                                        
                                    # Remove any file types that we don't want (ex. IceLibrary, ie. Strms)
                                    if self.incIceLibrary == False and file[-4:].lower() == 'strm':
                                        self.log("getFileList_NEW, ignoring strm")
                                        dur = 0
                                    
                                    # Use adv. channel rule to filter unwanted content by duration
                                    if dur < self.durFilter:
                                        self.log("getFileList_NEW, ignoring duration; "+str(dur)+" less than " + str(self.durFilter))
                                        dur = 0
                                        
                                    self.log("getFileList_NEW, dur = " + str(dur))
                                    if dur > 0:
                                        self.filecount += 1
                                        seasonval = -1
                                        epval = -1
                                        self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="adding %s Videos" % str(self.filecount),inc=int(((self.filecount) // limit) // self.enteredChannelCount))
                                        self.log('getFileList_NEW, filecount = ' + str(self.filecount) +'/'+ str(limit))
                                        
                                        titles = re.search('"label" *: *"(.*?)",', f)
                                        showtitles = re.search('"showtitle" *: *"(.*?)",', f)
                                        plots = re.search('"plot" *: *"(.*?)",', f)
                                        plotoutlines = re.search('"plotoutline" *: *"(.*?)",', f)
                                        years = re.search('"year" *: *([\d.]*\d+)', f)
                                        genres = re.search('"genre" *: *\[(.*?)\],', f)
                                        playcounts = re.search('"playcount" *: *([\d.]*\d+),', f)
                                        imdbnumbers = re.search('"imdbnumber" *: *"(.*?)",', f)
                                        ratings = re.search('"mpaa" *: *"(.*?)",', f)
                                        starss = re.search('"rating" *: *([\d.]*\d+),', f)
                                        descriptions = re.search('"description" *: *"(.*?)",', f)
                                        # streamdetails = re.search('"streamdetails" *: *{(.*?)},', f)

                                        #tvshow check
                                        if showtitles != None and len(showtitles.group(1)) > 0:
                                            type = 'tvshow'
                                            dbids = re.search('"tvshowid" *: *([\d.]*\d+),', f)
                                            epids = re.search('"id" *: *([\d.]*\d+),', f)
                                        else:
                                            type = 'movie'
                                            dbids = re.search('"id" *: *([\d.]*\d+),', f)  
                                            epids = None
                                        
                                        # if possible find year by title
                                        try:
                                            year = int(years.group(1))
                                        except:
                                            year = 0

                                        if genres != None and len(genres.group(1)) > 0:
                                            genre = ((genres.group(1).split(',')[0]).replace('"',''))
                                        else:
                                            genre = 'Unknown'
                                            
                                        if playcounts != None and len(playcounts.group(1)) > 0:
                                            playcount = int(playcounts.group(1))
                                        else:
                                            playcount = 1                             
                                        
                                        if ratings != None and len(ratings.group(1)) > 0:
                                            rating = self.cleanRating(ratings.group(1))
                                        else:
                                            rating = 'NR'
                                            
                                        if starss != None and len(starss.group(1)) > 0:
                                            stars = "%.1f" % round(float(starss.group(1)))
                                        else:
                                            stars = 0.0 
                                            
                                        hd = False
                                        # if widths != None and len(widths.group(1)) > 0:
                                            # self.log("getFileList, width = " + str(widths.group(1)))
                                            # if int(widths.group(1)) >= 720:
                                                # hd = True
                                        # self.log("getFileList, hd = " + str(hd)) 

                                        if imdbnumbers != None and len(imdbnumbers.group(1)) > 0:
                                            imdbnumber = imdbnumbers.group(1)
                                        else:
                                            imdbnumber = '0'

                                        if epids != None and len(epids.group(1)) > 0:
                                            epid = int(epids.group(1))
                                        else:
                                            epid = 0
                                        
                                        if dbids != None and len(dbids.group(1)) > 0:
                                            dbid = int(dbids.group(1))
                                        else:
                                            dbid = 0
                                        
                                        if plots and len(plots.group(1)) > 0:
                                            theplot = (plots.group(1)).replace('\\','').replace('\n','')
                                        elif descriptions and len(descriptions.group(1)) > 0:
                                            theplot = (descriptions.group(1)).replace('\\','').replace('\n','')
                                        elif plotoutlines and len(plotoutlines.group(1)) > 0:
                                            theplot = (plotoutlines.group(1)).replace('\\','').replace('\n','')
                                        else:
                                            theplot = (titles.group(1)).replace('\\','').replace('\n','')
                                        description = theplot
                                        
                                        # TVshow
                                        if type == 'tvshow':
                                            season = re.search('"season" *: *([0-9]*?),', f)
                                            episode = re.search('"episode" *: *([0-9]*?),', f)
                                            swtitle = (titles.group(1)).replace('\\','')
                                            swtitle = (swtitle.split('.', 1)[-1]).replace('. ','')
                                            dbid = str(dbid) +':'+ str(epid)
                                            
                                            try:
                                                seasonval = int(season.group(1))
                                                epval = int(episode.group(1))
                                            except Exception,e:
                                                try:  
                                                    labelseasonepval = re.findall(r"(?:s|season)(\d{2})(?:e|x|episode|\n)(\d{2})", label.lower(), re.I)
                                                    seasonval = int(labelseasonepval[0][0])
                                                    epval = int(labelseasonepval[0][1])
                                                except Exception,e:
                                                    seasonval = -1
                                                    epval = -1
                                                    
                                            if seasonval != -1 and epval != -1:
                                                try:
                                                    eptitles = swtitle.split(' - ')[1]
                                                except:
                                                    try:
                                                        eptitles = swtitle.split('.')[1]
                                                    except:
                                                        try:
                                                            eptitles = swtitle.split('. ')[1]
                                                        except:
                                                            eptitles = swtitle
                                                subtitle = (('0' if seasonval < 10 else '') + str(seasonval) + 'x' + ('0' if epval < 10 else '') + str(epval) + ' - ' + (eptitles)).replace('  ',' ')
                                            else:
                                                subtitle = swtitle.replace(' . ',' - ')

                                            if len(showtitles.group(1)) > 0:
                                                showtitle = showtitles.group(1)
                                            else:
                                                showtitle = labels.group(1)
                                        else: # Movie            
                                            album = re.search('"album" *: *"(.*?)"', f)
                                            if not album or len(album.group(1)) == 0:
                                                dbid = str(dbid)
                                                
                                                if len(titles.group(1)) > 0:
                                                    showtitle = titles.group(1)
                                                else:
                                                    showtitle = labels.group(1)
                                                    
                                                taglines = re.search('"tagline" *: *"(.*?)"', f)
                                                if taglines and len(taglines.group(1)) > 50:
                                                    subtitle = ''
                                                    if description and len(description) < 50:
                                                        description = (taglines.group(1)).replace('\\','')
                                                elif taglines and len(taglines.group(1)) > 0:
                                                    subtitle = (taglines.group(1)).replace('\\','')
                                                else:
                                                    subtitle = ''# todo customize missing taglines by media type  
                                            else: #Music
                                                type = 'music'
                                                if album != None and len(album.group(1)) > 0:
                                                    albumTitle = album.group(1)
                                                else:
                                                    albumTitle = label.group(1)
                                                    
                                                artist = re.search('"artist" *: *"(.*?)"', f)
                                                if artist != None and len(artist.group(1)) > 0:
                                                    artistTitle = artist.group(1)
                                                else:
                                                    artistTitle = ''
                                                showtitle = artistTitle
                                                subtitle = albumTitle
                                                description = albumTitle
                                        
                                        if file.startswith('plugin'):
                                            #Remove PlayMedia to keep link from launching
                                            try:
                                                file = ((file.split('PlayMedia("'))[1]).replace('")','')
                                            except:
                                                pass      

                                        # convert minutes to seconds when needed / correct local tvshow runtimes
                                        if file.startswith(("plugin", "upnp")):
                                            if (len(str(dur)) < 3 or len(str(dur)) > 5):
                                                dur = self.durationInSeconds(dur)
                                            
                                        if durParsed == True:
                                            if type == 'movie':
                                                setKodiRuntime(type,dbid,dur)
                                            elif type in ['episode','tvshow']:
                                                setKodiRuntime(type,epid,dur)
                                            
                                        #Enable Enhanced Parsing
                                        includeMeta = self.includeMeta            
                                        # accurate real-time scheduling does not apply to chtypes <= 7, only chtype = 8. Doesn't hurt to keep track of it anyway, future feature for realtime mode?
                                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.startDate))
                                        self.startDate += dur
            
                                        managed =  False # todo check sickbeard/sonar/couchpotato
                                        cc = False # todo check subs or teltext?
                                        GenreLiveID = [genre, type, imdbnumber, dbid, managed, playcount, rating, hd, cc, stars, year]
                                        tmpstr = self.makeTMPSTR(dur, showtitle, year, subtitle, description, GenreLiveID, file, timestamp, includeMeta)      
                                        
                                        if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
                                            seasoneplist.append([seasonval, epval, tmpstr])
                                        else:
                                            # Filter 3D Media.
                                            if self.isMedia3D(file) == True:
                                                if type == 'movie':
                                                    self.movie3Dlist.append(tmpstr)
                                            else:
                                                fileList.append(tmpstr)     
                                
                                elif filetype == 'directory' and (self.filecount < limit and self.dircount < dirlimit):
                                    self.log('getFileList_NEW, directory')
                                    self.setBackgroundStatus("Initializing: Loading Channel " + str(self.settingChannel),string2="searching Directory - %s" % label)
                                    fileList.extend(self.getFileList(self.requestList(file), channel, limit, excludeLST))
                                    self.dircount += 1
                                    self.log('getFileList_NEW, dircount = ' + str(self.dircount) +'/'+ str(dirlimit))
                            else:
                                self.log('getFileList_NEW, ' + label.lower() + ' in excludeLST')                                        
            except Exception,e:
                self.log('getFileList_NEW, failed...' + str(e))
                self.log(traceback.format_exc(), xbmc.LOGERROR)
        if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
            self.log('getFileList_NEW, MODE_ORDERAIRDATE')
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])
            for seepitem in seasoneplist:
                fileList.append(seepitem[2])

        # Stop playback when called during plugin parsing.
        if self.background == False and xbmc.Player().isPlaying():
            json_query = ('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"stop"},"id":1}')
            self.sendJSON(json_query);  
                                                                              
        self.log("getFileList_NEW, fileList cnt = " + str(len(fileList)))    

        # cleanup  
        del seasoneplist[:]                 
        return fileList

        
    def getStreamDetails(self, mediapath):
        self.log('getStreamDetails') 

        
    def setChannelChanged(self, channel, changed=True):
        self.log('setChannelChanged, channel = ' + str(channel))
        self.channels[channel - 1].hasChanged = changed

        
    def setBackgroundStatus(self, string1, progress=None, inc=0.5, string2=None, string3=None):
        if self.background == False:
            self.myOverlay.setBackgroundStatus(string1, progress, inc, string2, string3)
            
            
    def dict2tmpstr(self, dList):
        self.log('dict2tmpstr')
        filelist = []
        self.startDate = self.startTime
        for i in range(dList):
            dict = dList[i]
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.startDate))
            self.startDate += int(dict['duration'])
            GenreLiveID = [dict['genre'], dict['type'], dict['id'], dict['thumburl'], False, 1, dict['rating'], dict['hd'], dict['cc'], dict['stars'], dict['year']]
            filelist.append(self.makeTMPSTR(dict['duration'], dict['title'], dict['year'], dict['subtitle'], dict['description'], GenreLiveID, dict['link'], timestamp))
        return filelist