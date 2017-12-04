#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoCompanion.
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

# -*- coding: utf-8 -*-
import os, re, sys, time, zipfile, requests, random, traceback, threading
import urllib, urllib2,cookielib, base64, fileinput, shutil, socket, httplib, urlparse, HTMLParser
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon
import time, _strptime, string, datetime, ftplib, hashlib, smtplib, feedparser, imp, operator

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
    
from pyfscache import *
from xml.etree import ElementTree as ET
from xml.dom.minidom import parse, parseString

# Plugin Info
ADDON_ID = 'plugin.video.pseudo.companion'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name').decode('utf-8')
ADDON_PATH = REAL_SETTINGS.getAddonInfo('path')
ADDON_SETTINGS = REAL_SETTINGS.getAddonInfo('profile')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')

# PTVL Settings Info
PTVL_ID = 'script.pseudotv.live'
PTVL_SETTINGS = xbmcaddon.Addon(id=PTVL_ID)
YT_API_KEY = PTVL_SETTINGS.getSetting('YT_API_KEY')
LOGODB_API_KEY = PTVL_SETTINGS.getSetting('LOGODB_API_KEY')
TMDB_API_KEY = PTVL_SETTINGS.getSetting("TMDB_API_KEY")
GBOX_API_KEY = PTVL_SETTINGS.getSetting("GBOX_API_KEY")
SETTINGS_LOC = PTVL_SETTINGS.getAddonInfo('profile').decode('utf-8')
CHANNELS_LOC = os.path.join(SETTINGS_LOC, 'cache','') #LOCKED
REQUESTS_LOC = xbmc.translatePath(os.path.join(CHANNELS_LOC, 'requests','')) #LOCKED
LOCK_LOC = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache',''))
XMLTV_CACHE_LOC = xbmc.translatePath(os.path.join(LOCK_LOC, 'xmltv',''))
PTVL_RUNNING = xbmcgui.Window(10000).getProperty('PseudoTVRunning') == "True"
MEDIA_LIMIT = 200

# PC Settings Info
SETTINGS2_LOC = xbmc.translatePath(os.path.join(ADDON_SETTINGS,'settings2.xml'))
STRM_LOC = REAL_SETTINGS.getSetting('STRM_LOC')
Path_Type = REAL_SETTINGS.getSetting('Path_Type')
Clear_Strms = REAL_SETTINGS.getSetting('Clear_Strms') == 'true'
Automatic_Update = REAL_SETTINGS.getSetting('Automatic_Update')
Automatic_Update_Delay = REAL_SETTINGS.getSetting('Automatic_Update_Delay')
Automatic_Update_Run = REAL_SETTINGS.getSetting('Automatic_Update_Run')

# Globals
PTVC_ICON = os.path.join(ADDON_PATH, 'icon.png')
PTVC_FANART = os.path.join(ADDON_PATH, 'fanart.jpg')
PTVL_ICON = os.path.join(ADDON_PATH,'resources','images','icon.png')
PTVL_ICON_GRAY = os.path.join(ADDON_PATH,'resources','images','icon_gray.png')
PC_ICON = os.path.join(ADDON_PATH,'resources','images','pseudocinema.jpg')
PTVLXML = os.path.join(XMLTV_CACHE_LOC, 'ptvlguide.xml')
PTVLXMLZIP = os.path.join(LOCK_LOC, 'ptvlguide.zip')
DEBUG = REAL_SETTINGS.getSetting('Enable_Debugging') == "true"
youtube_player_ok = 'plugin://plugin.video.youtube/?action=play_video&videoid='

try:
    from metahandler import metahandlers
    metaget = metahandlers.MetaData(preparezip=False, tmdb_api_key=TMDB_API_KEY)
    ENHANCED_DATA = True                
except Exception,e:  
    ENHANCED_DATA = False
    xbmc.log("script.pseudotv.live-ChannelList: metahandler Import failed! " + str(e))    

    
# pyfscache globals
cache_daily = FSCache(REQUESTS_LOC, days=1, hours=0, minutes=0)
cache_weekly = FSCache(REQUESTS_LOC, days=7, hours=0, minutes=0)
cache_monthly = FSCache(REQUESTS_LOC, days=28, hours=0, minutes=0)

# Thumbs
POPCORN_ICON = 'http://www.brocode.com/wp-content/uploads/2012/01/popcorn-movie-tickets.jpg'
NEWR_ICON = 'http://static1.squarespace.com/static/52d95e01e4b04d4af95761e6/t/53838eb2e4b0476310fdcd8c/1401130675361/newreleases.png'
MMOVIE_ICON = 'http://static.timefor.tv/imgs/epg/logos/movies4men1_big.png'
ACTION_ICON = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/A/Action.png'
CLASSIC_ICON = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/C/C%20Cinema%20Classic.png'
COMEDY_ICON = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/C/Comedy%20Movies%20(2).png'
DRAMA_ICON = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/D/Drama%20Movies%20(3).png'
HORROR_ICON = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/H/Horror%20Movies.png'
SCIFI_ICON = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/S/Sci-Fi%20Movies.png'
THRILLER_ICON = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/T/Thriller%20Movies.png'
WESTERN_ICON = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/W/Western%20Movies.png'
WORLD_ICON = 'http://s3.amazonaws.com/rv-wp/directvdealscom/uploads/2014/08/universal-sports.jpg'

def log(msg, level = xbmc.LOGDEBUG):
    if DEBUG != True and level == xbmc.LOGDEBUG:
        return
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + uni(msg), level)

def Comingsoon():
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Coming Soon", 1000, PTVC_ICON) )
    
def Unavailable():
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Unavailable", 1000, PTVC_ICON) )
    
def TryAgain():
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Try Again Later...", 1000, PTVC_ICON) )

def show_busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialog)')

def hide_busy_dialog():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    while xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        xbmc.sleep(100)
        
def encodeString(string):
    return (string.encode('base64')).replace('\n','').replace('\r','').replace('\t','')
    
def decodeString(string):
    return string.decode('base64')
    
def removeNonAscii(s): return "".join(filter(lambda x: ord(x)<128, s))
    
def utf(string, encoding = 'utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode):
            string = unicode(string, encoding, 'ignore')
    return string
  
def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('ascii', 'ignore')
    return string
    
def uni(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('utf-8', 'ignore' )
    return string
    
def removeStringElem(lst,string=''):
    return ([x for x in lst if x != string])
    
def replaceStringElem(lst,old='',new=''):
    return ([x.replace(old,new) for x in lst])
           
def sorted_nicely(lst): 
    log('utils: sorted_nicely')
    list = set(lst)
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(list, key = alphanum_key)
        
def replaceAll(file,searchExp,replaceExp):
    log('utils: script.pseudotv.liveutils: replaceAll')
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp,replaceExp)
        sys.stdout.write(line)
    
def cleanStrms( text, format=''):
    text = uni(text)
    text = text.replace('Full Episodes', '')
    if format == 'title':
        text = text.title().replace("'S","'s")
    elif format == 'upper':
        text = text.upper()
    elif format == 'lower':
        text = text.lower()
    else:
        text = text
    return text
    
def cleanString(string):
    newstr = uni(string)
    newstr = newstr.replace('&', '&amp;')
    newstr = newstr.replace('>', '&gt;')
    newstr = newstr.replace('<', '&lt;')
    return uni(newstr)

def uncleanString(string):
    newstr = uni(string)
    newstr = newstr.replace('&amp;', '&')
    newstr = newstr.replace('&gt;', '>')
    newstr = newstr.replace('&lt;', '<')
    return uni(newstr)

def cleanRating(rating):
    log("cleanRating")
    rating = uni(rating)
    rating = cleanLabels(rating,'upper')
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

def cleanLabels(text, format=''):
    text = uni(text)
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
    text = uncleanString(text.strip())
    return text  

def CleanCHname(text):
    text = text.replace("AE", "A&E")
    text = text.replace(" (uk)", "")
    text = text.replace(" (UK)", "")
    text = text.replace(" (us)", "")
    text = text.replace(" (US)", "")
    text = text.replace(" (ca)", "")
    text = text.replace(" (CA)", "")
    text = text.replace(" (en)", "")
    text = text.replace(" (EN)", "")
    text = text.replace(" hd", "")
    text = text.replace(" HD", "")
    text = text.replace(" PVR", "")
    text = text.replace(" LiveTV", "") 
    text = text.replace(" USTV", "")
    text = text.replace(" USTVnow", "")  
    text = text.replace(" USTVNOW", "") 
    return text
  
def fillGithubItems(url, ext=None, removeEXT=False):
    log("utils: fillGithubItems, url = " + url)
    Sortlist = []
    # show_busy_dialog()
    try:
        list = []
        catlink = re.compile('title="(.+?)">').findall(read_url_cached(url))
        for i in range(len(catlink)):
            link = catlink[i]
            name = (catlink[i]).lower()
            if ext != None:
                if ([x.lower for x in ext if name.endswith(x)]):
                    if removeEXT == True:
                        link = os.path.splitext(os.path.basename(link))[0]
                    list.append(link.replace('&amp;','&'))
            else:
                list.append(link.replace('&amp;','&'))
        Sortlist = sorted_nicely(list) 
        log("utils: fillGithubItems, found %s items" % str(len(Sortlist)))
    except Exception,e:
        pass
    # hide_busy_dialog()
    return Sortlist

def CleanCHnameSeq(text):
    # try removing number from channel ie NBC2 = NBC, or 5 FOX = FOX
    return (''.join(i for i in text if not i.isdigit())).lstrip()

def FindLogo(chname):
    log('utils: FindLogo')
    FindLogoThread = threading.Timer(0.5, FindLogo_Thread, [chname])
    FindLogoThread.name = "FindLogoThread"
    if FindLogoThread.isAlive():
        FindLogoThread.cancel()
        FindLogoThread.join()
    FindLogoThread.start()
    xbmc.sleep(10)
         
def FindLogo_Thread(chname):
    log('utils: FindLogo_Thread')
    url = PTVC_ICON
    Cchname = CleanCHname(chname)
    url = FindLogo_URL(Cchname)
    if not url:
        url = FindLogo_URL(CleanCHnameSeq(Cchname))
    setProperty('PC.CHLOGO_%s' % (chname.lower()),(url or PTVC_ICON))
           
def FindLogo_URL(chname):
    # thelogodb search
    url = ''
    user_region = PTVL_SETTINGS.getSetting('limit_preferred_region')
    user_type = PTVL_SETTINGS.getSetting('LogoDB_Type')
    useMix = PTVL_SETTINGS.getSetting('LogoDB_Fallback') == "true"
    useAny = PTVL_SETTINGS.getSetting('LogoDB_Anymatch') == "true"
    url = findLogodb(chname, user_region, user_type, useMix, useAny)
    if url:
        return url
        
    url = findGithubLogo(chname)
    if url:
        return url

def findLogodb(chname, user_region, user_type, useMix=True, useAny=True):
    try:
        urlbase = 'http://www.thelogodb.com/api/json/v1/%s/tvchannel.php?s=' % PTVL_SETTINGS.getSetting('LOGODB_API_KEY')
        chanurl = (urlbase+chname).replace(' ','%20')
        typelst =['strLogoSquare','strLogoSquareBW','strLogoWide','strLogoWideBW','strFanart1']
        user_type = typelst[int(user_type)]
        detail = re.compile("{(.*?)}", re.DOTALL ).findall(read_url_cached(chanurl))
        MatchLst = []
        mixRegionMatch = []
        mixTypeMatch = []
        image = ''
        for f in detail:
            try:
                regions = re.search('"strCountry" *: *"(.*?)"', f)
                channels = re.search('"strChannel" *: *"(.*?)"', f)
                if regions:
                    region = regions.group(1)
                if channels:
                    channel = channels.group(1)
                    for i in range(len(typelst)):
                        types = re.search('"'+typelst[i]+'" *: *"(.*?)"', f)
                        if types:
                            type = types.group(1)
                            if channel.lower() == chname.lower():
                                if typelst[i] == user_type:
                                    if region.lower() == user_region.lower():
                                        MatchLst.append(type.replace('\/','/'))
                                    else:
                                        mixRegionMatch.append(type.replace('\/','/'))
                                else:
                                    mixTypeMatch.append(type.replace('\/','/'))
            except Exception,e:
                pass
                
        if len(MatchLst) == 0:
            if useMix == True and len(mixRegionMatch) > 0:
                random.shuffle(mixRegionMatch)
                image = mixRegionMatch[0]
                log('utils: findLogodb, Logo NOMATCH useMix: ' + str(image))
            if not image and useAny == True and len(mixTypeMatch) > 0:
                random.shuffle(mixTypeMatch)
                image = mixTypeMatch[0]
                log('utils: findLogodb, Logo NOMATCH useAny: ' + str(image))
        else:
            random.shuffle(MatchLst)
            image = MatchLst[0]
            log('utils: findLogodb, Logo Match: ' + str(image))
        
        # cleanup
        del MatchLst[:]
        del mixRegionMatch[:]
        del mixTypeMatch[:]      
        return image 
    except Exception,e:
        log("utils: findLogodb, Failed! " + str(e))
         
def findGithubLogo(chname): 
    log("utils: findGithubLogo, chname = " + chname)
    url = ''
    baseurl='https://github.com/PseudoTV/PseudoTV_Logos/tree/master/%s' % (chname[0]).upper()
    Studiolst = fillGithubItems(baseurl, '.png', removeEXT=True)
    if not Studiolst:
        miscurl='https://github.com/PseudoTV/PseudoTV_Logos/tree/master/0'
        Misclst = fillGithubItems(miscurl, '.png', removeEXT=True)
        for i in range(len(Misclst)):
            Studio = Misclst[i]
            if uni((Studio).lower()) == uni(chname.lower()):
                url = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/0/'+((Studio+'.png').replace('&','&amp;').replace(' ','%20'))
                log('utils: findGithubLogo, Logo Match: ' + Studio.lower() + ' = ' + (Misclst[i]).lower())
                break
    else:
        for i in range(len(Studiolst)):
            Studio = Studiolst[i]
            if uni((Studio).lower()) == uni(chname.lower()):
                url = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/'+chname[0]+'/'+((Studio+'.png').replace('&','&amp;').replace(' ','%20'))
                log('utils: findGithubLogo, Logo Match: ' + Studio.lower() + ' = ' + (Studiolst[i]).lower())
                break
    return url
           
def cleanReminderTime(tmpDate):
    try:#sloppy fix, for threading issue with strptime.
        t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
    except:
        t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
    Notify_Time = time.strftime('%I:%M%p, %A', t)
    epochBeginDate = time.mktime(t)
    return Notify_Time, epochBeginDate   
    
@cache_monthly
def getJson(url):
    log("getJson, url = " + url) 
    response = urllib2.urlopen(url)
    return json.load(response)
 
def sendJSON(command, previous=None):
    log('utils: sendJSON, command = ' + command)
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))
    return uni(data)
        
def showOSD():
    xbmc.executebuiltin("ActivateWindow(videoosd)")

def showSearch():
    xbmc.executebuiltin("XBMC.RunScript(script.skin.helper.service,action=videosearch)")
        
def mute():
    xbmc.executebuiltin("Mute()")
        
def showInfo():
    log('showInfo')
    json_query = ('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"info"},"id":2}')
    sendJSON(json_query)
    
def goLeft():
    log('goLeft')
    json_query = ('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"left"},"id":2}')
    sendJSON(json_query)
    
def goRight():
    log('goRight')
    json_query = ('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"right"},"id":2}')
    sendJSON(json_query)
        
def getProperty(str):
    return xbmcgui.Window(10000).getProperty(str)

def setProperty(str1, str2):
    xbmcgui.Window(10000).setProperty(str1, str2)

def clearProperty(str):
    xbmcgui.Window(10000).clearProperty(str)
    
def selectDialog(list, header=ADDON_NAME, autoclose=0):
    if len(list) > 0:
        select = xbmcgui.Dialog().select(header, list, autoclose)
        return select

def getType():
    Types = ['TV','Episodes','Movies','Other','Custom']
    select = selectDialog(Types,'Select Media Type')
    if select >= 0:
        if Types[select] == 'Custom':
            retval = xbmcgui.Dialog().input('Enter Folder Name', type=xbmcgui.INPUT_ALPHANUM)
            if retval and len(retval) > 0:
                return retval
        else:
            return Types[select]
         
def addDir(name,description,url,previous,mode,thumb=PTVC_ICON,ic=PTVC_ICON,fan=PTVC_FANART,infoList=False,infoArt=False,content_type='video',showcontext=False):
    log('utils: addDir')
    liz = xbmcgui.ListItem(name)
    liz.setArt({'thumb': ic, 'fanart': fan})
    liz.setProperty('IsPlayable', 'false')
    
    # if showcontext == True:
        # c=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(200)+"&name="+urllib.quote_plus(name)+"&previous="+urllib.quote_plus(path)
        # contextMenu = []
        # contextMenu.append(('Create Strms','XBMC.RunPlugin(%s)'%(c)))
        # liz.addContextMenuItems(contextMenu)

    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&previous="+urllib.quote_plus(previous)
    if infoList == False:
        liz.setInfo(type="Video", infoLabels={ "Title": name, "Plot": description, "mediatype": content_type})
    else:
        liz.setInfo(type="Video", infoLabels=infoList)
        
    if infoArt != False:
        liz.setArt(infoArt) 
        
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
      
def addLink(name,description,url,previous,mode,thumb=PTVC_ICON,ic=PTVC_ICON,fan=PTVC_FANART,infoList=False,infoArt=False,content_type='video',showcontext=False,total=0):
    log('utils: addLink') 
    liz = xbmcgui.ListItem(name)
    liz.setArt({'thumb': ic, 'fanart': fan})
    liz.setProperty('IsPlayable', 'true')
    
    # if showcontext == True:
        # c=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(200)+"&name="+urllib.quote_plus(name)
        # contextMenu = []
        # contextMenu.append(('Create Strms','XBMC.RunPlugin(%s)'%(c)))
        # liz.addContextMenuItems(contextMenu)
                 
    u = url
    if infoList == False:
        liz.setInfo(type="Video", infoLabels={ "Title": name, "Plot": description})
    else:
        liz.setInfo(type="Video", infoLabels=infoList)
    
    if infoArt != False:
        liz.setArt(infoArt) 
        
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,totalItems=total)

def getVimeoMeta(VMID):
    log('getVimeoMeta')
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
    except:
        pass
    return title, description, duration, thumburl
        
def getYoutubeChname(YTID):
    log('getYoutubeChname')
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

def getYoutubeDetails(YTID):
    log('getYoutubeDetails')
    YT_URL_Video = ('https://www.googleapis.com/youtube/v3/videos?key=%s&id=%s&part=id,snippet,contentDetails,statistics' % (YT_API_KEY, YTID))
    return re.compile("},(.*?)}", re.DOTALL ).findall(read_url_cached(YT_URL_Video))

def getYoutubeMeta(id):
    log('getYoutubeMeta ' + id)
    detail = getYoutubeDetails(id)
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
                duration = parseYoutubeDuration((durations.group(1) or 0))
                
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
                    title = (titles.group(1))
                description = ''
                if descriptions and len(descriptions.group(1)) > 0:
                    description = ((descriptions.group(1)).split('http')[0]).replace('\\n',' ')
                if publisheds and len(publisheds.group(1)) > 0:
                    published = (publisheds.group(1))
                    year = int(published[0:4])

                if not description:
                    description = title
        except Exception,e:
            log('getYoutubeMeta, failed! ' + str(e))

    log("getYoutubeMeta, return")
    return year, duration, description, title, chname, id, genre, hd, cc
    
def getYoutubeDuration(YTID):
    log('getYoutubeDuration')
    detail = getYoutubeDetails(YTID)
    for f in detail:
        durations = re.search('"duration" *: *"(.*?)",', f)
        if durations:
            return parseYoutubeDuration(durations.group(1))
    return 0

def parseYoutubeDuration(duration):
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
        x = time.strptime(str(datetime.timedelta(**converted_dict)).split(',')[0],'%H:%M:%S')
        dur = int(__total_seconds__(datetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec)))
        log('parseYoutubeDuration, dur = ' + str(dur))
    except Exception,e:
        pass
    return dur

def getYoutubeUserID( YTid):
    log("getYoutubeUserID, IN = " + YTid)
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
        log("getYoutubeUserID, OUT = " + YT_ID)
    except Exception,e:
        log('getYoutubeUserID, failed! ' + str(e), xbmc.LOGERROR)
    return YT_ID

def getYoutubeVideos(content_type, previous, YT_Type, YT_ID, YT_NextPG, limit, YTMSG):
    log("getYoutubeVideos, YT_Type = " + str(YT_Type) + ', YT_ID = ' + YT_ID) 
    cnt = 0
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
            YT_ID = getYoutubeUserID(YT_ID)
            return getYoutubeVideos(content_type, previous, YT_Type, YT_ID, YT_NextPG, limit, YTMSG)  
        else:
            YT_URL_Search = requestChannelVideosInfo
            log("getYoutubeVideos, requestChannelVideosInfo = " + YT_URL_Search) 
    elif YT_Type == 2:
        YT_URL_Search = requestPlaylistInfo
        log("getYoutubeVideos, requestPlaylistInfo = " + YT_URL_Search) 
        
    elif YT_Type == 5:
        YT_URL_Search = requestSearchVideosInfo
        log("getYoutubeVideos, requestSearchVideosInfo = " + YT_URL_Search) 
        
    try:
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(read_url_cached(YT_URL_Search))

        for f in detail:
            if cnt >= MEDIA_LIMIT:
                break
            VidIDS = re.search('"videoId" *: *"(.*?)"', f)
            YT_NextPGS = re.search('"nextPageToken" *: *"(.*?)"', f)
            if YT_NextPGS:
                YT_NextPG = YT_NextPGS.group(1)
                
            if VidIDS:
                VidID = VidIDS.group(1)
                year, duration, description, title, chname, id, genre, hd, cc = getYoutubeMeta(VidID)

                Stitle = cleanLabels(title)
                year, title, showtitle = getTitleYear(Stitle, year)           
                
                if type == 'movie':
                    Stitle = showtitle
                else:
                    Stitle = title
                         
                desc = cleanLabels(description)
                genre = cleanLabels(genre)
                
                # setup infoList
                infoList = {}
                infoList['mediatype']     = content_type
                infoList['Duration']      = int(duration)
                infoList['Title']         = uni(Stitle)
                infoList['Year']          = int(year or '0')
                infoList['Genre']         = uni(genre)
                infoList['Plot']          = uni(desc)
                infoList['Studio']        = uni(chname)
                
                # setup infoArt
                infoArt = {}
                infoArt['thumb']          = ("http://i.ytimg.com/vi/"+VidID+"/mqdefault.jpg")
                infoArt['poster']         = ("http://i.ytimg.com/vi/"+VidID+"/mqdefault.jpg")

                if content_type in ['movie']:
                    meta = metaget.get_meta(content_type, title, str(year)) 
                    desc = uni(meta['plot']    or description)
                    infoList['Plot']      = desc
                    infoList['Genre']     = uni(meta['genre']   or genre)
                    infoArt['thumb']      = (meta['cover_url']  or "http://i.ytimg.com/vi/"+VidID+"/mqdefault.jpg")
                    infoArt['poster']     = (meta['cover_url']  or "http://i.ytimg.com/vi/"+VidID+"/mqdefault.jpg") 

                cnt += 1
                addLink(showtitle,desc,youtube_player_ok + VidID,'previous',5001,infoList=infoList,infoArt=infoArt,total=len(detail))
    except Exception,e:
        log('getYoutubeVideos, Failed!, ' + str(e))
                    
# *Thanks sphere, adapted from plugin.video.ted.talks
# People still using Python <2.7 201303 :(
def __total_seconds__(delta):
    try:
        return delta.total_seconds()
    except AttributeError:
        return int((delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10 ** 6)) / 10 ** 6
      
def requestItem(file, fletype='video'):
    log("requestItem") 
    json_query = ('{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":1,"properties":["thumbnail","fanart","title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid"]}, "id": 1}')
    json_folder_detail = sendJSON(json_query)
    return re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
          
def requestList(path, fletype='video'):
    log("requestList, path = " + path) 
    json_query = ('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "properties":["thumbnail","fanart","title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid"]}, "id": 1}'%(path,fletype))
    json_folder_detail = sendJSON(json_query)
    return re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)      
   
def fillPluginItems(url, media_type='video', file_type=False, strm=False, strm_path='', strm_name='', strm_type='Other'):
    log('utils: fillPluginItems')
    if not file_type:
        detail = uni(requestList(url, media_type))
    else:
        detail = uni(requestItem(url, media_type))
    for f in detail:
        files = re.search('"file" *: *"(.*?)",', f)
        filetypes = re.search('"filetype" *: *"(.*?)",', f)
        labels = re.search('"label" *: *"(.*?)",', f)
        thumbnails = re.search('"thumbnail" *: *"(.*?)",', f)
        fanarts = re.search('"fanart" *: *"(.*?)",', f)
        descriptions = re.search('"description" *: *"(.*?)",', f)
        
        if filetypes and labels and files:
            filetype = filetypes.group(1)
            label = cleanLabels(labels.group(1))
            file = (files.group(1).replace("\\\\", "\\"))
            
            if not descriptions:
                description = ''
            else:
                description = cleanLabels(descriptions.group(1))
                
            thumbnail = (removeNonAscii(thumbnails.group(1)) or PTVC_ICON)
            fanart = (removeNonAscii(fanarts.group(1)) or PTVC_FANART)
                        
            if strm_type.lower() in ['tv','tvshows','tvshow']:
                if filetype == 'directory':
                    strm_name = label
                path = os.path.join('TV',strm_name)
                filename = strm_name + ' - ' + label
            elif strm_type.lower() in ['episodes','episode']:
                path = os.path.join('TV',strm_name)
                filename = strm_name + ' - ' + label
            elif strm_type.lower() in ['movie','movies']:
                path = os.path.join('Movie',label)
                filename = label
            else:
                path = os.path.join('Other',strm_name)
                filename = strm_name + ' - ' + label
                
            if filetype == 'file':
                if strm:
                    writeSTRM(cleanStrms(path), cleanStrms(filename) ,filetype, file)
                else:
                    addLink(label,description,file,'',5001,thumb=thumbnail,ic=thumbnail,fan=fanart,total=len(detail))
            else:
                if strm:
                    fillPluginItems(file, media_type, file_type, strm, path, label, strm_type)
                else:
                    addDir(label,description,file,'',6002,thumb=thumbnail,ic=thumbnail,fan=fanart)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
def fillPlugins(type='video'):
    log('utils: fillPlugins, type = ' + type)
    json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.addon.%s","properties":["name","path","thumbnail","description","fanart","summary"]}, "id": 1 }'%type)
    json_detail = sendJSON(json_query)
    detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
    for f in detail:
        names = re.search('"name" *: *"(.*?)",', f)
        paths = re.search('"addonid" *: *"(.*?)",', f)
        thumbnails = re.search('"thumbnail" *: *"(.*?)",', f)
        fanarts = re.search('"fanart" *: *"(.*?)",', f)
        descriptions = re.search('"description" *: *"(.*?)",', f)
        if not descriptions:
            descriptions = re.search('"summary" *: *"(.*?)",', f)
        if descriptions:
            description = cleanLabels(descriptions.group(1))
        else:
            description = ''
        if names and paths:
            name = cleanLabels(names.group(1))
            path = paths.group(1)
            if type == 'video' and path.startswith('plugin.video') and not path.startswith('plugin.video.pseudo.companion'):
                thumbnail = (removeNonAscii(thumbnails.group(1)) or PTVC_ICON)
                fanart = (removeNonAscii(fanarts.group(1)) or PTVC_FANART)
                addDir(name,description,'plugin://'+path,'',6002,thumb=thumbnail,ic=thumbnail,fan=fanart)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
def getChanTypeLabel(chantype):
    if chantype == 0:
        return "Custom Playlist"
    elif chantype == 1:
        return "TV Network"
    elif chantype == 2:
        return "Movie Studio"
    elif chantype == 3:
        return "TV Genre"
    elif chantype == 4:
        return "Movie Genre"
    elif chantype == 5:
        return "Mixed Genre"
    elif chantype == 6:
        return "TV Show"
    elif chantype == 7:
        return "Directory"
    elif chantype == 8:
        return "LiveTV"
    elif chantype == 9:
        return "InternetTV"
    elif chantype == 10:
        return "Youtube"
    elif chantype == 11:
        return "RSS"
    elif chantype == 12:
        return "Music (Coming Soon)"
    elif chantype == 13:
        return "Music Videos (Coming Soon)"
    elif chantype == 14:
        return "Extra"
    elif chantype == 15:
        return "Plugin"
    elif chantype == 16:
        return "UPNP"
    elif chantype == 9999:
        return "None"
    return ''
          
def remove_duplicates(values):
    try:
        output = []
        seen = set()
        for value in values:
            # If value has not been encountered yet,
            # ... add it to both list and set.
            if value not in seen:
                output.append(value)
                seen.add(value)
        return output
    except:
        return values
          
def infoDialog(message, header=ADDON_NAME, show=True, sound=False, time=1000, ic=PTVC_ICON):
    setProperty('PTVL.NOTIFY_LOG', message)
    log('utils: infoDialog: ' + message)
    if show == True:
        try: 
            xbmcgui.Dialog().notification(header, message, ic, time, sound=False)
        except Exception,e:
            log("utils: infoDialog Failed! " + str(e))
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, PTVC_ICON))
      
def SyncXMLTV(force=False):
    try:
        if isDon() == True: 
            SyncXMLTVtimer = threading.Timer(0.1, SyncXMLTV_NEW, [force])
            SyncXMLTVtimer.name = "SyncXMLTVtimer"     
            if SyncXMLTVtimer.isAlive():
                SyncXMLTVtimer.cancel()
            SyncXMLTVtimer.start()
    except Exception,e:
        log('utils: SyncXMLTV_NEW, Failed!, ' + str(e)) 
        
def SyncXMLTV_NEW(force=False):
    log('utils: SyncXMLTV_NEW, force = ' + str(force))
    now  = datetime.datetime.today()
    REAL_SETTINGS.setSetting("SyncPTV_ChckRun",str(now))   
    # try:
    try:
        SyncPTV_LastRun = REAL_SETTINGS.getSetting('SyncPTV_NextRun')
        if not SyncPTV_LastRun or xbmcvfs.exists(PTVLXML) == False or force == True:
            raise exception()
    except:
        REAL_SETTINGS.setSetting("SyncPTV_NextRun","1970-01-01 23:59:00.000000")
        SyncPTV_LastRun = REAL_SETTINGS.getSetting('SyncPTV_NextRun')

    try:
        SyncPTV = datetime.datetime.strptime(SyncPTV_LastRun, "%Y-%m-%d %H:%M:%S.%f")
    except:
        SyncPTV = datetime.datetime.strptime(SyncPTV_LastRun, "%Y-%m-%d %H:%M:%S.%f")
        
    if now > SyncPTV:         
        REAL_SETTINGS.setSetting("SyncPTV_LastRun",str(now))
        #Remove old file before download
        if xbmcvfs.exists(PTVLXML):
            try:
                xbmcvfs.delete(PTVLXML)
                log('utils: SyncXMLTV, Removed old PTVLXML')
            except:
                log('utils: SyncXMLTV, Removing old PTVLXML Failed!')
                
        if retrieve_url(PTVLXMLURL, UPASS, PTVLXMLZIP):
            if xbmcvfs.exists(PTVLXMLZIP):
                all(PTVLXMLZIP,XMLTV_CACHE_LOC)
                try:
                    xbmcvfs.delete(PTVLXMLZIP)
                    log('utils: SyncXMLTV, Removed PTVLXMLZIP')
                except:
                    log('utils: SyncXMLTV, Removing PTVLXMLZIP Failed!')
            
            if xbmcvfs.exists(PTVLXML):
                log('utils: SyncXMLTV, ptvlguide.xml download successful!')  
                infoDialog("Guidedata Update Complete")
                SyncPTV_NextRun = ((now + datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S.%f"))
                log('utils: SyncXMLTV, Now = ' + str(now) + ', SyncPTV_NextRun = ' + str(SyncPTV_NextRun))
        REAL_SETTINGS.setSetting("SyncPTV_NextRun",str(SyncPTV_NextRun))
        PTVL_SETTINGS.setSetting('PTVLXML_FORCE', 'false')
    # except Exception,e:
        # log("utils: SyncXMLTV_NEW Failed!" + str(e))
     
##################
#   URL Tools    #
##################

def _pbhook(numblocks, blocksize, filesize, dp, start_time):
    try: 
        percent = min(numblocks * blocksize * 100 / filesize, 100) 
        currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
        kbps_speed = numblocks * blocksize / (time.time() - start_time) 
        if kbps_speed > 0: 
            eta = (filesize - numblocks * blocksize) / kbps_speed 
        else: 
            eta = 0 
        kbps_speed = kbps_speed / 1024 
        total = float(filesize) / (1024 * 1024) 
        mbs = '%.02f MB of %.02f MB' % (currently_downloaded, total) 
        e = 'Speed: %.02f Kb/s ' % kbps_speed 
        e += 'ETA: %02d:%02d' % divmod(eta, 60) 
        dp.update(percent, mbs, e)
    except: 
        percent = 100 
        dp.update(percent) 
    if dp.iscanceled(): 
        dp.close() 
  
def download(url, dest, dp = None):
    log('download')
    if not dp:
        dp = xbmcgui.DialogProgress()
        dp.create("PseudoTV Live","Downloading & Installing Files", ' ', ' ')
    dp.update(0)
    start_time=time.time()
    try:
        urllib.urlretrieve(url, dest, lambda nb, bs, fs: _pbhook(nb, bs, fs, dp, start_time))
    except Exception,e:
        log('utils: download, Failed!,' + str(e))
     
def download_silent_thread(url, dest):
    log('download_silent_thread')
    try:
        urllib.urlretrieve(url, dest)
    except Exception,e:
        log('utils: download_silent_thread, Failed!,' + str(e))
         
def download_silent(url, dest):
    log('download_silent')
    download_silentThread = threading.Timer(0.5, download_silent_thread, [url, dest])
    download_silentThread.name = "download_silentThread"
    if download_silentThread.isAlive():
        download_silentThread.cancel()
        download_silentThread.join()
    download_silentThread.start()
    xbmc.sleep(10)
        
@cache_daily
def read_url_cached(url, userpass=False, return_type='read'):
    log("utils: read_url_cached")
    try:
        if return_type == 'readlines':
            response = open_url(url, userpass).readlines()
        else:
            response = open_url(url, userpass).read()
        return response
    except Exception,e:
        pass
        
@cache_monthly
def read_url_cached_monthly(url, userpass=False, return_type='read'):
    log("utils: read_url_cached_monthly")
    try:
        if return_type == 'readlines':
            response = open_url(url, userpass).readlines()
        else:
            response = open_url(url, userpass).read()
        return response
    except Exception,e:
        pass
  
def open_url(url, userpass=None):
    log("utils: open_url")
    page = ''
    try:
        request = urllib2.Request(url)
        if userpass:
            user, password = userpass.split(':')
            base64string = base64.encodestring('%s:%s' % (user, password))
            request.add_header("Authorization", "Basic %s" % base64string) 
        else:
            # TMDB needs a header to be able to read the data
            if url.startswith("http://api.themoviedb.org"):
                request.add_header("Accept", "application/json")
            else:
                request.add_header('User-Agent','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11')
        page = urllib2.urlopen(request)
        page.close
        return page
    except urllib2.HTTPError, e:
        return page
         
def retrieve_url(url, userpass, dest):
    log("utils: retrieve_url")
    try:
        resource = open_url(url, userpass)
        output = open(dest, 'w')
        output.write(resource.read())  
        output.close()
        return True
    except Exception, e:
        return False 
       
def get_data(url, data_type ='json'):
    log('utils: get_data, url = ' + url)
    data = []
    try:
        request = read_url_cached_monthly(url)
        if data_type == 'json':
            data = json.loads(request)
            if not data:
                data = 'Empty'
        else:
            data = request
    except Exception, e:
        data = 'Empty'
    return data
       
def anonFTPDownload(filename, DL_LOC):
    log('utils: anonFTPDownload, ' + filename + ' - ' + DL_LOC)
    try:
        ftp = ftplib.FTP("ftp.pseudotvlive.com", "PTVLuser@pseudotvlive.com", "PTVLuser")
        ftp.cwd("/")
        file = open(DL_LOC, 'w')
        ftp.retrbinary('RETR %s' % filename, file.write)
        file.close()
        ftp.quit()
        return True
    except Exception, e:
        log('utils: anonFTPDownload, Failed!! ' + str(e))
        return False
 
##################
# Zip Tools #
##################

def all(_in, _out, dp=None):
    if dp:
        return allWithProgress(_in, _out, dp)
    return allNoProgress(_in, _out)

def allNoProgress(_in, _out):
    try:
        zin = zipfile.ZipFile(_in, 'r')
        zin.extractall(_out)
    except Exception, e:
        return False
    return True

def allWithProgress(_in, _out, dp):
    zin = zipfile.ZipFile(_in,  'r')
    nFiles = float(len(zin.infolist()))
    count  = 0

    try:
        for item in zin.infolist():
            count += 1
            update = count / nFiles * 100
            dp.update(int(update))
            zin.extract(item, _out)
    except Exception, e:
        return False
    return True 
     
def getTitleYear(showtitle, showyear=0):  
    # extract year from showtitle, merge then return
    try:
        labelshowtitle = re.compile('(.+?) [(](\d{4})[)]$').findall(showtitle)
        title = labelshowtitle[0][0]
        year = int(labelshowtitle[0][1])
    except Exception,e:
        try:
            year = int(((showtitle.split(' ('))[1]).replace(')',''))
            title = ((showtitle.split('('))[0])
        except Exception,e:
            if showyear != 0:
                showtitle = showtitle + ' ('+str(showyear)+')'
                year, title, showtitle = getTitleYear(showtitle, showyear)
            else:
                title = showtitle
                year = 0
    if year == 0 and int(showyear) !=0:
        year = int(showyear)
    if year != 0 and '(' not in title:
        showtitle = title + ' ('+str(year)+')' 
    log("utils: getTitleYear, return " + str(year) +', '+ title +', '+ showtitle) 
    return year, title, showtitle
         
def writeSTRM(foldername, filename, url, purge=False):
    log('writeSTRM')
    try:
        filepath = os.path.join(STRM_LOC, foldername)
        if not xbmcvfs.exists(filepath): 
            xbmcvfs.mkdirs(filepath)
        fullpath = os.path.join(filepath, filename + '.strm')
        if purge == True:
            try: 
                xbmcvfs.delete(fullpath)
            except:
                pass
        fle = open(fullpath, "w")
        fle.write("%s" % url)
        fle.close()
    except Exception,e:
        log("writeSTRM, Failed " + str(e))
        
def writeSettings2(name, type, url):
    log('writeSettings2')
    thelist = []
    theentry = '|'.join([name, type, filetype, url])+'\n'
    
    if xbmcvfs.exists(SETTINGS2_LOC):
        fle = open(SETTINGS2_LOC, "r")
        thelist = fle.readlines()
        fle.close()
        
    if theentry not in thelist:
        thelist.append(theentry)
    else:
        thelist = replaceStringElem(thelist, theentry, theentry)
    try:
        fle = open(SETTINGS2_LOC, "w")
        fle.writelines(thelist)
        fle.close()
    except Exception,e:
        log("writeSettings2, Failed " + str(e))
    setProperty('writeSettings2','true')
  
def readSettings2(purge=False):
    log('readSettings2')
    # try:
    if xbmcvfs.exists(SETTINGS2_LOC):
        fle = open(SETTINGS2_LOC, "r")
        thelist = fle.readlines()
        fle.close()
        for i in range(len(thelist)):
            name, type, filetype, url = ((thelist[i]).split('|'))
            if filetype == 'file':
                writeSTRM(cleanStrms(path), cleanStrms(filename) ,filetype, file)
            else:
                fillPluginItems(urllib.unquote_plus(url), strm=True, strm_name=name, strm_type=type)
    # except Exception,e:
        # log("readSettings2, Failed " + str(e))
    setProperty('writeSettings2','false')
        
def chkWriteSettings2():
    log('chkWriteSettings2')
    if getProperty('writeSettings2') == 'true':
        readSettings2()
  
def runWriteSettings2():
    log('runWriteSettings2')
    readSettings2(Clear_Strms)
  
# if REAL_SETTINGS.getSetting("SyncXMLTV_Enabled") == "true" and isDon() == True:  
    # setBackgroundLabel('Initializing: XMLTV Service')
    # SyncXMLTV_NEW(REAL_SETTINGS.getSetting('PTVLXML_FORCE') == "true")
    
# if isDon() == True:
    # REAL_SETTINGS.setSetting("autoFindPopcorn","true")
    # REAL_SETTINGS.setSetting("autoFindCinema","true")
    
    
# if getProperty("Verified_Donor") == "true":
    # OPTIONS = OPTIONS + ['DONOR:'+(REAL_SETTINGS.getSetting('Donor_UP')).split(':')[0]]
        
    
###################

def fillExternalList(type, source='', list='Community'):
    log('fillExternalList')
    responce = []
    TMPExternalList = []
    ExternalNameList = []
    SortedExternalList = []
    ExternalSetting1List = []
    ExternalSetting2List = []
    ExternalSetting3List = []
    ExternalSetting4List = []
    RSSURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/rss_feeds.ini'
    YoutubeChannelURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_channel.ini'
    YoutubePlaylistURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_playlist.ini'
    YoutubeChannelNetworkURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_channel_networks.ini'
    YoutubePlaylistNetworkURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_playlist_networks.ini'
    
    if type == 'LiveTV':
        url = LiveURL
    elif type == 'InternetTV':
        url = InternetURL
    elif type == 'Plugin':
        url = PluginURL
    elif type == 'YouTube':
        if source == 'Channel':
            url = YoutubeChannelURL
        elif source == 'Playlist':
            url = YoutubePlaylistURL
        elif source == 'Networks':
            url = [YoutubeChannelNetworkURL]
            # url = [YoutubeChannelNetworkURL,YoutubePlaylistNetworkURL]
    elif type == 'RSS':
        url = RSSURL
    try:
        for i in range(len(url)):
            responce.extend(read_url_cached(url[i], return_type='readlines'))
    except:
        pass
    return removeStringElem(responce)#remove empty lines

def getExternalChannel(url):
    type, source, list, Channels = url.split(',')
    getExternalChannels(type, source, list, Channels)
    
def getExternalChannels(type, source='', list='Community', Channels='True'):
    log('getExternalChannels')
    data = fillExternalList(type, source, list)
    for i in range(len(data)):
        line = data[i].replace("\n","").replace('""',"")
        if type == 'RSS' or source == 'Channel' or source == 'Playlist':
            line = line.split(",")
        else:
            line = line.split("|")

        if not str(line).startswith(';'):
            if len(line) == 7:
                url = (line[2])
                channel_name = cleanLabels(line[6])
            elif len(line) == 2:
                url = line[0]
                channel_name = line[1] 
            elif len(line) == 3:
                url = line[1]
                channel_name = line[2]
            if Channels == 'True':
                FindLogo(channel_name)
                addDir(channel_name,'',('%s,%s,%s,%s' %(type, source, list, channel_name)),'getExternalChannels',2000, getProperty('PC.CHLOGO_%s' %channel_name.lower()), getProperty('PC.CHLOGO_%s' %channel_name.lower()))
            else:
                if channel_name.lower() == Channels.lower():
                    url = url.split(',')
                    for n in range(len(url)):
                        if url[n].startswith('PL'):
                            YT_Type = 2
                        else:
                            YT_Type = 1
                        getYoutubeVideos('tvshow', 'getExternalChannels', YT_Type, url[n], '', MEDIA_LIMIT, '')