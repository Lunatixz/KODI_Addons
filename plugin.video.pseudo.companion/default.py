#   Copyright (C) 2016 Kevin S. Graer
#
#
# This file is part of PseudoCompanion.
#
# PseudoCompanion is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoCompanion is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoCompanion.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, re, sys, time, zipfile, requests, random, traceback
import urllib, urllib2,cookielib, base64, fileinput, shutil, socket, httplib, urlparse, HTMLParser
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon
import time, _strptime, string, datetime, ftplib, hashlib, smtplib, feedparser, imp, operator

from pyfscache import *
from xml.etree import ElementTree as ET
from xml.dom.minidom import parse, parseString
from datetime import timedelta
from metahandler import metahandlers
from utils import *
      
if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
  
def fillPseudoNetworks(): 
    getLBchannels()
    getExternalChannels('YouTube','Networks')
      
def getLBchannels(limit=100):
    log("getLBchannels") 
    try:
        data = getJson('https://api-public.guidebox.com/v1.43/US/'+GBOX_API_KEY+'/' + ('leanback/%s/0/%d' %('all',limit)))
        rtItems = data["results"]
        for i in range(len(rtItems)):
            Item = rtItems[i]
            title = Item["title"]
            thumb = Item["artwork_448x252"]
            chid = str(Item["id"])
            addDir(title,'',chid,'getLBchannels',3010,thumb,thumb)
    except:
        return
      
def getLBchannelsItems(id, limit=100):
    log("getLBchannelsItems")
    try:        
        data = getJson('https://api-public.guidebox.com/v1.43/US/'+GBOX_API_KEY+'/' + ('leanback/%s/0/%d' % (str(id),limit)))
        rtItems = data["results"]
        channelItem = []
        for i in range(len(rtItems)):
            Item = rtItems[i]
            content_type = Item["content_type"].replace('Episode Clip','episode')
            title = cleanLabels(Item["title"])
            thumb = uni(Item["thumbnail_400x225"])
            link = uni(youtube_player_ok + Item["free_web_sources"][0]['link'].replace('https://www.youtube.com/watch?v=',''))
            Description = cleanLabels(Item["overview"].replace("\n",' ').replace("\'",'')).split('http:')[0]
            
            infoList = {}
            infoList['mediatype']     = content_type
            infoList['Duration']      = int(Item["duration"])
            infoList['Title']         = title
            infoList['Plot']          = Description
            infoList['Season']        = int(Item["season_number"] or '0')
            infoList['Episode']       = int(Item["episode_number"] or '0')
            infoArt = {}
            infoArt['thumb']        = thumb
            infoArt['poster']       = thumb
            infoArt['landscape']    = thumb
            addLink(title,Description,link,'getLBchannelsItems',5001,thumb,thumb,infoList=infoList,infoArt=infoArt,total=len(rtItems))
    except:
        return
        
def getSources():
    log('getSources')
    STATE = getProperty('PseudoCompanion.STATE') == 'true'
    STATUS = getProperty('PseudoCompanion.STATUS')
    if STATE == True:
        getOnline()
    else:
        getOffline()
        
def getOffline():
    log('getOffline')
    addDir('Channel Tools','','','',9001)
    getOnlineMedia()
    addDir('PseudoLibrary','','','',9003)
        
def getOnline():
    log('getOnline')
    getNowWatching()
    getChannelGuide()
    getSidebar()
    getMiscs()
    addDir('Scheduled Reminders','Coming Soon','','',4,PTVL_ICON,PTVL_ICON)
    addDir('Scheduled Recordings','Coming Soon','','',5,PTVL_ICON,PTVL_ICON)
    addDir('Recorded TV','Coming Soon','','',6,PTVL_ICON,PTVL_ICON)
      
def getMisc():
    getStatus()
    getNotice()
    getPlayer()
    getDEBUG()
    getError()
     
def getStatus():
    title = getProperty('PTVL.STATUS_LOG')
    debug_icon = os.path.join(ADDON_PATH,'resources','images','debug.png')
    label = 'STATUS:'
    content_type = 'movie'
    infoList = {}
    infoList['mediatype']     = content_type
    infoList['TVShowTitle']   = label
    infoList['Genre']         = title
    infoList['Title']         = label
    infoList['Studio']        = label
    infoList['Year']          = '0'
    addLink('1', title,'','getMisc',-1,debug_icon,debug_icon,'',infoList,total=1)
    
def getNotice():
    title = getProperty('PTVL.NOTIFY_LOG')
    debug_icon = os.path.join(ADDON_PATH,'resources','images','debug.png')
    label = 'NOTICE:'
    content_type = 'movie'
    infoList = {}
    infoList['mediatype']     = content_type
    infoList['TVShowTitle']   = label
    infoList['Genre']         = title
    infoList['Title']         = label
    infoList['Studio']        = label
    infoList['Year']          = '0'
    addLink('2', title,'','getMisc',-1,debug_icon,debug_icon,'',infoList,total=1)
                
def getPlayer():
    title = getProperty('PTVL.PLAYER_LOG')
    debug_icon = os.path.join(ADDON_PATH,'resources','images','debug.png')
    label = 'PLAYER:'
    content_type = 'movie'
    infoList = {}
    infoList['mediatype']     = content_type
    infoList['TVShowTitle']   = label
    infoList['Genre']         = title
    infoList['Title']         = label
    infoList['Studio']        = label
    infoList['Year']          = '0'
    addLink('3', title,'','getMisc',-1,debug_icon,debug_icon,'',infoList,total=1)
        
def getDEBUG(): 
    title = getProperty('PTVL.DEBUG_LOG')
    debug_icon = os.path.join(ADDON_PATH,'resources','images','debug.png')
    label = 'DEBUG:'
    content_type = 'movie'
    infoList = {}
    infoList['mediatype']     = content_type
    infoList['TVShowTitle']   = label
    infoList['Genre']         = title
    infoList['Title']         = label
    infoList['Studio']        = label
    infoList['Year']          = '0'
    addLink('4', title,'','getMisc',-1,debug_icon,debug_icon,'',infoList,total=1)
         
def getError():
    title = getProperty('PTVL.ERROR_LOG')
    debug_icon = os.path.join(ADDON_PATH,'resources','images','debug.png')
    label = 'ERROR:'
    content_type = 'movie'
    infoList = {}
    infoList['mediatype']     = content_type
    infoList['TVShowTitle']   = label
    infoList['Genre']         = title
    infoList['Title']         = label
    infoList['Studio']        = label
    infoList['Year']          = '0'
    addLink('5', title,'','getMisc',-1,debug_icon,debug_icon,'',infoList,total=1)
   
def getLibrary():
    addDir('Browse Local','','','getMedia',7003)
    addDir('Browse Strms','','','getMedia',7005)
    
def getTools():
    addDir('Channel Manager','','','getTools',8001)
    
def getMedia():
    log('getMedia')
    addDir('BCT Sources','','','getMedia',7000)
    addDir('PseudoCinema','','','getMedia',7002,PC_ICON,PC_ICON)
    addDir('Popcorn Movies','','genres','getMedia',3001,POPCORN_ICON,POPCORN_ICON)

def getOnlineMedia():
    addDir('PseudoNetworks','','','getOnlineMedia',3000,WORLD_ICON,WORLD_ICON)
    
def getStrms():
    comingsoon()
    
def getLocal():
    log('getLocal') 
    addDir('Local Video','','video','',6000)
    addDir('Local Music','','music','',6000)
    addDir('Plugin Video ','','video','',6001)
    addDir('Plugin Music','','music','',6001)
    addDir('PVR Backend','','pvr://','',6002)
    addDir('UPNP Servers','','upnp://','',6002)

def getReminders():
    log('getReminders')
    try:
        ReminderLst = eval(getProperty("PTVL.ReminderLst"))
        if ReminderLst and len(ReminderLst) > 0:
            for n in range(len(ReminderLst)):
                lineLST = ReminderLst[n]
                record  =  lineLST['Record'] == 'True'
                chtype  =  lineLST['Chtype']
                tmpDate =  lineLST['TimeStamp']
                title   =  lineLST['Title']
                SEtitle =  lineLST['SEtitle']
                chnum   =  lineLST['Chnum']
                chname  =  lineLST['Chname']
                poster  =  lineLST['poster']
                fanart  =  lineLST['fanart']
                chlogo  =  lineLST['LOGOART']
                Notify_Time, epochBeginDate = cleanReminderTime(tmpDate)          
                now = time.time()
                if epochBeginDate > now:
                    label = ('[B]%s[/B] on channel [B]%s[/B] at [B]%s[/B]'%(title, chnum, str(Notify_Time)))
                    content_type = 'tvshow'
                    infoList = {}
                    infoList['mediatype']     = content_type
                    infoList['TVShowTitle']   = str(Notify_Time)
                    infoList['Genre']         = str(Notify_Time)
                    infoList['Title']         = title
                    infoList['Studio']        = 'chname'
                    infoList['Year']          = int(chnum or '0')
                    
                    infoArt = {}
                    infoArt['thumb']        = poster
                    infoArt['poster']       = poster
                    infoArt['fanart']       = fanart
                    infoArt['landscape']    = fanart
                    infoList['icon']        = chlogo
                    addDir(label, Notify_Time, str(chnum),'getReminders',10000,poster,chlogo,fanart,infoList,infoArt,content_type)
        else:
            raise Exception()
    except Exception,e:
        addDir('No Reminders Set','','','','',PTVL_ICON,PTVL_ICON)
            
def ChannelGuide():
    log('ChannelGuide') 
    try:
        GuideLst = eval(getProperty("OVERLAY.ChannelGuide"))
        GuideLst.sort(key=lambda x:x['Chnum'])
        
        for i in range(len(GuideLst)):
            GuideLstItem = GuideLst[i]
            content_type = 'episode'
            chnum  = GuideLstItem['Chnum']
            chname = GuideLstItem['Chname']
            chtype = GuideLstItem['Chtype']
            chtypeLabel = GuideLstItem['ChtypeLabel']
            chlogo = GuideLstItem['LOGOART']
            label  = GuideLstItem['Label']
            
            infoList = {}
            infoList['mediatype']     = content_type
            infoList['title']         = chname
            infoList['tvshowtitle']   = chtypeLabel
            infoList['season']        = 0
            infoList['episode']       = chnum
            addDir(label,'',str(chnum),'ChannelGuide',10000,chlogo,chlogo,chlogo,infoList,False,content_type)
    except:
        addDir('Try Again Later','','','',PTVL_ICON,PTVL_ICON)
        
def OnNow(next=False):
    log('OnNow')
    try:
        if next == True:
            previous = 'OnNext'
            OnNowLst = eval(getProperty("OVERLAY.OnNextLst"))
            OnNextLst = []
        else:
            previous = 'OnNow'
            OnNowLst = eval(getProperty("OVERLAY.OnNowLst"))
            OnNextLst = eval(getProperty("OVERLAY.OnNextLst"))
       
        OnNowLst.sort(key=lambda x:x['Chnum'])
        OnNextLst.sort(key=lambda x:x['Chnum'])
        
        for i in range(len(OnNowLst)):
            OnNowLine = OnNowLst[i]
            OnNextLine = OnNextLst[i]
            
            content_type = 'tvshow'
            type         = OnNowLine['content_type']
            title        = OnNowLine['Title']
            rating       = OnNowLine['Rating']
            nextTitle    = OnNextLine['Title']
            SEtitle      = OnNowLine['SEtitle']
            nextSEtitle  = OnNextLine['SEtitle']
            tagline      = OnNowLine['Tagline']
            nexttagline  = OnNextLine['Tagline']
            chname       = OnNowLine['Chname']
            chnum        = OnNowLine['Chnum']
            chtype       = OnNowLine['Chtype']
            season       = OnNowLine['Season']
            episode      = OnNowLine['Episode'] 
            playcount    = OnNowLine['Playcount']
            description  = OnNowLine['Description']
            poster       = OnNowLine['poster']
            fanart       = OnNowLine['fanart']
            chlogo       = OnNowLine['LOGOART']
            label        = ('%d| %s' %(chnum, title))
            
            # if type in ['tvshow','episode']:
                # title = ('%s - %s' % (title,SEtitle))
                
            # setup infoList
            infoList = {}
            infoList['mediatype']     = content_type
            infoList['MPAA']          = rating
            infoList['TVShowTitle']   = 'Next: ' + nextTitle
            infoList['Genre']         = 'Next: ' + nextTitle
            infoList['Title']         = title
            infoList['Studio']        = chname
            infoList['Year']          = int(chnum or '0')
            infoList['Season']        = int(season or '0')
            infoList['Episode']       = int(episode or '0')
            infoList['playcount']     = int(playcount or '0')
            # setup infoArt
            infoArt = {}
            infoArt['thumb']        = poster
            infoArt['poster']       = poster
            infoArt['fanart']       = fanart
            infoArt['landscape']    = fanart
            infoList['icon']        = chlogo
            url = str({'content_type': content_type, 'Rating': rating, 'Description': description, 'Title': title, 'Chname': chname, 'Chname': chname, 'Chnum': chnum, 'Season': season, 'Episode': episode, 'playcount': playcount, 'poster': poster, 'fanart': fanart, 'chlogo': chlogo})
            addDir(label,OnNowLine['Description'],str(chnum),previous,10000,poster,chlogo,fanart,infoList,infoArt,content_type)
    except:
        addDir('Try Again Later','','','',PTVL_ICON,PTVL_ICON)
     
def PreviewChannel(name, url, previous):
    log('PreviewChannel')
    PreviewLine = eval(url)
    content_type = 'tvshow' 
    infoList = {}
    infoList['mediatype']     = PreviewLine['content_type']
    infoList['MPAA']          = PreviewLine['Rating']
    infoList['TVShowTitle']   = PreviewLine['Description']
    infoList['Genre']         = PreviewLine['Description']
    infoList['Title']         = PreviewLine['Title']
    infoList['Studio']        = PreviewLine['Chname']
    infoList['Year']          = int(PreviewLine['Chnum'] or '0')
    infoList['Season']        = int(PreviewLine['Season'] or '0')
    infoList['Episode']       = int(PreviewLine['Episode'] or '0')
    infoList['playcount']     = int(PreviewLine['playcount'] or '0')
    infoArt = {}
    infoArt['thumb']        = PreviewLine['poster']
    infoArt['poster']       = PreviewLine['poster']
    infoArt['fanart']       = PreviewLine['fanart']
    infoArt['landscape']    = PreviewLine['fanart']
    infoList['icon']        = PreviewLine['chlogo']   
    addDir(name,PreviewLine['Description'],str(PreviewLine['Chnum']),previous,10000,PreviewLine['poster'],PreviewLine['chlogo'],PreviewLine['fanart'],infoList,infoArt,content_type)
        
def InputChannel(channel, previous):
    log('InputChannel = ' + str(channel))
    for n in range(len(str(channel))):   
        json_query = ('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"number%s"},"id":2}') % (str(channel)[n])
        sendJSON(json_query)
    back(previous)
    
def sendJSON(command, previous=None):
    log('utils: sendJSON, command = ' + command)
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))
    back(previous)
    return uni(data)
       
def sendClick(id, previous):
    log('sendClick, id = ' + str(id))
    window_id = xbmcgui.getCurrentWindowDialogId()
    window = xbmcgui.Window(window_id)
    # trigger sidebar
    if id in [1000,1001,1002,1003,1004,1005,1006,1007,1008,1009,1010,1011]:
        showInfo()
        xbmc.sleep(1000)
        goLeft()
        xbmc.sleep(1000)
    window.setFocusId(id)
    xbmc.sleep(1000)
    xbmc.executebuiltin("SendClick(%d,%d)" %(window_id,int(id)))
    back(previous)

def getNowWatching():
    log('NowWatching')
    infoList = {}
    infoList['mediatype']     = 'tvshow'
    infoList['Genre']         = 'Next: ' + getProperty("OVERLAY.NEXT.Title")
    infoList['Title']         = 'Now: ' + getProperty("OVERLAY.PLAYING.Title")
    infoList['Studio']        = getProperty("OVERLAY.PLAYING.Chname")
    infoList['Year']          = int(getProperty("OVERLAY.PLAYING.Chnum") or '0')
    infoArt = {}
    infoArt['thumb']        = (getProperty("OVERLAY.PLAYING.poster") or PTVL_ICON)
    infoArt['fanart']       = (getProperty("OVERLAY.PLAYING.landscape") or getProperty("OVERLAY.PLAYING.fanart") or PTVC_FANART)
    addDir('1','','','getOnline',1,infoList=infoList,infoArt=infoArt)
        
def getChannelGuide():
    infoList = {}
    infoList['mediatype']     = 'video'
    infoList['Title']         = 'Channel Guide'
    infoArt = {}
    infoArt['thumb']        = PTVL_ICON
    infoArt['fanart']       = PTVC_FANART
    addDir('2','','','getOnline',3,infoList=infoList,infoArt=infoArt)
    
def getOnNow():
    infoList = {}
    infoList['mediatype']     = 'video'
    infoList['Title']         = 'On Now'
    infoArt = {}
    infoArt['thumb']        = PTVL_ICON
    infoArt['fanart']       = PTVC_FANART
    addDir('3','','','getOnline',1,infoList=infoList,infoArt=infoArt)
        
def getSidebar():
    infoList = {}
    infoList['mediatype']     = 'video'
    infoList['Title']         = 'Sidebar'
    infoArt = {}
    infoArt['thumb']        = PTVL_ICON
    infoArt['fanart']       = PTVC_FANART
    addDir('4','','','getOnline',7,infoList=infoList,infoArt=infoArt)
    
def getMiscs():
    infoList = {}
    infoList['mediatype']     = 'video'
    infoList['Title']         = 'Misc.'
    infoArt = {}
    infoArt['thumb']        = PTVL_ICON
    infoArt['fanart']       = PTVC_FANART
    addDir('8','','','getOnline',8,infoList=infoList,infoArt=infoArt)
        
def getLocalVideo():
    comingsoon()
    
def comingsoon():
    addDir('ComingSoon','','','','')
        
def getPTVLManager():
    log('getPTVLManager')
    comingsoon()
    
def getControls():
    log('getControls')
    comingsoon()
    
def export(name,url,previous):
    log('export')
    print name,url,previous

def getPTVLGuide():
    log('getPTVLGuide')
    comingsoon()
    
def getRecordings():
    log('getRecordings')
    comingsoon()
    
def getRecorded():
    log('getRecorded')
    comingsoon()
    
def getBCTs():
    log('getBCTs')
    comingsoon()

def getCinema():
    log('getCinema')
    addDir('Cinema Theme: Default','','1','getCinema',12000,PC_ICON,PC_ICON)
    addDir('Cinema Theme: IMAX','','2','getCinema',12000,PC_ICON,PC_ICON)

def fillCE(theme):
    log('fillCE')
    CE_THEME = ['Default','IMAX'][theme]
    
    CE_INTRO = line[0]
    Thumb = "http://i.ytimg.com/vi/"+CE_INTRO+"/mqdefault.jpg"
    Url = youtube_player_ok + CE_INTRO
    addLink('1: '+CE_THEME+' Intro','CE_INTRO',Url,'fillCE',5001,Thumb,Thumb)
    
    CE_CELL = (((line[6])).split(','))[theme]
    Thumb = "http://i.ytimg.com/vi/"+CE_CELL+"/mqdefault.jpg"
    Url = youtube_player_ok + CE_CELL
    addLink('2: '+CE_THEME+' Quiet','CE_CELL',Url,'fillCE',5001,Thumb,Thumb)

    CE_COMING_SOON = (((line[3])).split(','))[theme]
    Thumb = "http://i.ytimg.com/vi/"+CE_COMING_SOON+"/mqdefault.jpg"
    Url = youtube_player_ok + CE_COMING_SOON
    addLink('3: '+CE_THEME+' Coming Soon','CE_COMING_SOON',Url,'fillCE',5001,Thumb,Thumb)
    
    CE_PREMOVIE = (((line[5])).split(','))[theme]
    Thumb = "http://i.ytimg.com/vi/"+CE_PREMOVIE+"/mqdefault.jpg"
    Url = youtube_player_ok + CE_PREMOVIE
    addLink('3: '+CE_THEME+' PreMovie','CE_PREMOVIE',Url,'fillCE',5001,Thumb,Thumb)
        
    CE_FEATURE_PRESENTATION = (((line[4])).split(','))[theme]
    Thumb = "http://i.ytimg.com/vi/"+CE_FEATURE_PRESENTATION+"/mqdefault.jpg"
    Url = youtube_player_ok + CE_FEATURE_PRESENTATION
    addLink('4: '+CE_THEME+' Feature Presentation','CE_FEATURE_PRESENTATION',Url,'fillCE',5001,Thumb,Thumb)
        
    CE_3D = line[1]
    Thumb = "http://i.ytimg.com/vi/"+CE_3D+"/mqdefault.jpg"
    Url = youtube_player_ok + CE_3D
    addLink('5: '+CE_THEME+' 3D Glasses','CE_3D',Url,'fillCE',5001,Thumb,Thumb)

    CE_INTERMISSION = line[2]
    Thumb = "http://i.ytimg.com/vi/"+CE_INTERMISSION+"/mqdefault.jpg"
    Url = youtube_player_ok + CE_INTERMISSION
    addLink('6: '+CE_THEME+' Intermission','CE_INTERMISSION',Url,'fillCE',5001,Thumb,Thumb)

def back(parent):
    log('back')
    if parent == 'Main':
        addDir('-Back to Main Menu','','','',None)
    elif parent == 'Online':
        addDir('-Back to PTVL Menu','','','',9000,PTVL_ICON,PTVL_ICON)
    elif parent == 'Tools':
        addDir('-Back to PTVL Menu','','','',8000,PTVL_ICON,PTVL_ICON)
    elif parent == 'Local':
        addDir('-Back to PTVL Menu','','','',7003,PTVL_ICON,PTVL_ICON)
    elif parent == 'ChannelGuide':
        ChannelGuide()
    elif parent == 'OnNow':
        OnNow()
    elif parent == 'OnNext':
        OnNow(next=True)
    elif parent == 'getSideBar':
        getSideBar()
    elif parent == 'getReminders':
        getReminders()
        
def playURL(url):
    log('playURL')
    # if getProperty('PseudoTVRunning') == "True":
        # setProperty('PTVL.DIRECT_PLAY','true')
        # setProperty('PTVL.DIRECT_URL',url)
    # else:
    setProperty('PTVL.DIRECT_PLAY','false')
    item = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

def getURL(par):
    log('getURL')
    try:
        url = par.split('?url=')[1]
        url = url.split('&mode=')[0]
    except:
        url = None
    return url
    
def get_params():
    log('get_params')
    param=[]
    paramstring=sys.argv[2]
    log('paramstring = ' + paramstring)
    if len(paramstring)>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]
    log('param = ' + str(param))
    return param
 
params=get_params()

try:
    url=urllib.unquote_plus(params["url"]).decode('utf-8')
except:
    url=getURL(sys.argv[2])
try:
    name=urllib.unquote_plus(params["name"])
    log("Name: "+str(name))
except:
    name=''
try:
    previous=urllib.unquote_plus(params["previous"])
    log("Previous: "+str(previous))
except:
    previous = None
try:
    mode=int(params["mode"])
    log("Mode: "+str(mode))
except:
    mode=None
    
if not url is None:
    log("URL: "+str(url.encode('utf-8')))

if mode == None: getSources()

elif mode == -1: print 'null'

#getOnline
elif mode == 0: getNowWatching()
elif mode == 1: OnNow()
elif mode == 2: OnNow(next=True)
elif mode == 3: ChannelGuide()
elif mode == 4: getReminders()
elif mode == 5: getRecordings()
elif mode == 6: getRecorded()
elif mode == 7: getSideBar()
elif mode == 8: getMisc()

elif mode == 200: fillPluginItems(url, strm=True, strm_path=previous, strm_name=name, strm_type=getType())

elif mode == 2000: getExternalChannel(url)
elif mode == 2001: getExternalChannels('YouTube','Networks')

#getOnlineMedia
elif mode == 3000: fillPseudoNetworks()
elif mode == 3010: getLBchannelsItems(int(url))

#sidebar
elif mode == 4000: getLocal()
elif mode == 4001: showSearch()
elif mode == 4002: mute()
elif mode == 4003: showOSD()

#misc
elif mode == 5000: getPTVLGuide()
elif mode == 5001: playURL(url)

#getLocal
elif mode == 6000: getLocalVideo()
elif mode == 6001: fillPlugins(url)
elif mode == 6002: fillPluginItems(url)

#getMedia
elif mode == 7000: getBCTs()
elif mode == 7002: getCinema()
elif mode == 7003: getLocal()
elif mode == 7004: getOnlineMedia()
elif mode == 7005: getStrms()

#getTools
elif mode == 8000: getMedia()
elif mode == 8001: getPTVLManager()

#getSources
elif mode == 9000: getOnline()
elif mode == 9001: getTools()
elif mode == 9003: getLibrary()

elif mode == 9998: sendClick(int(url),previous)
elif mode == 9999: sendJSON(url,previous)

#PTVL Channel Input
elif mode == 10000: InputChannel(int(url),previous)

#PTVL Pre-Channel Input
elif mode == 10001: PreviewChannel(name,url,previous)

#PTVL Export to PTVL
elif mode == 10002: export(name,url,previous)

elif mode == 10003: getYoutubePlaylist(url)

elif mode == 10004: REAL_SETTINGS.openSettings()
elif mode == 10005: PTVL_SETTINGS.openSettings()


elif mode == 12000: fillCE(url)

# if mode in [0,1,2,3,4,5,6]: back('Online')                      # Return to Online Menu
# elif mode in [9995,9999]: back('Main')                        # Return to Main Menu

# xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_NONE )
xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL )
xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=False) # End List
