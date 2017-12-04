#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoTV Library.
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
import urllib, urllib2, cookielib, requests
import time, datetime
import os, sys, re, traceback
import xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs
import SimpleDownloader as downloader
try:
    import json
except:
    import simplejson as json

from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP

addon = xbmcaddon.Addon('plugin.video.pseudo.library')
addon_version = addon.getAddonInfo('version')
ADDON_NAME = addon.getAddonInfo('name')
profile = xbmc.translatePath(addon.getAddonInfo('profile').decode('utf-8'))
home = xbmc.translatePath(addon.getAddonInfo('path').decode('utf-8'))
favorites = os.path.join(profile, 'favorites')
history = os.path.join(profile, 'history')

icon = os.path.join(home, 'icon.png')
FANART = os.path.join(home, 'fanart.jpg')
source_file = os.path.join(home, 'source_file')
functions_dir = profile

downloader = downloader.SimpleDownloader()
debug = addon.getSetting('debug')
if os.path.exists(favorites)==True:
    FAV = open(favorites).read()
else: FAV = []
if os.path.exists(favorites)==True:
    FAV = open(favorites).read()
else: FAV = []

DIRS = []
STRM_LOC = xbmc.translatePath(addon.getSetting('STRM_LOC'))

def addon_log(string):
    # if debug == 'true':
    xbmc.log("[plugin.video.pseudo.library-%s]: %s" %(addon_version, string))

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
                       
def cleanLabels( text, format=''):
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
    text = text.replace("\ ",'')
    text = text.replace("/ ",'')
    text = text.replace("\\",'/')
    text = text.replace("//",'/')
    text = text.replace('plugin.video.','')
    text = text.replace('plugin.audio.','')
    text = re.sub('[\/:*?<>|!@#$/:]', '', text)
    if format == 'title':
        text = text.title().replace("'S","'s")
    elif format == 'upper':
        text = text.upper()
    elif format == 'lower':
        text = text.lower()
    else:
        text = text
        
    text = uni(text.strip())
    return text

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

def removeNonAscii(s): return "".join(filter(lambda x: ord(x)<128, s))

def sendJSON(command):
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))
    return uni(data)
           
def requestItem(file, fletype='video'):
    addon_log("requestItem") 
    json_query = ('{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":1,"properties":["thumbnail","fanart","title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid"]}, "id": 1}')
    json_folder_detail = sendJSON(json_query)
    return re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
          
def requestList(path, fletype='video'):
    addon_log("requestList, path = " + path) 
    json_query = ('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "properties":["thumbnail","fanart","title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid"]}, "id": 1}'%(path,fletype))
    json_folder_detail = sendJSON(json_query)
    return re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)      
   
def fillPluginItems(url, media_type='video', file_type=False, strm=False, strm_name='', strm_type='Other'):
    addon_log('fillPluginItems')
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
                
            thumbnail = removeNonAscii(thumbnails.group(1))
            fanart = removeNonAscii(fanarts.group(1))
            
            if addon.getSetting('Link_Type') == '0':
                link = sys.argv[0]+"?url="+urllib.quote_plus(file)+"&mode="+str(10)+"&name="+urllib.quote_plus(label)+"&fanart="+urllib.quote_plus(fanart)
            else:
                link = file
            
            if strm_type in ['TV','Episodes']:
                path = os.path.join('TV',strm_name)
                filename = strm_name + ' - ' + label
                print path, filename
                
            if filetype == 'file':
                if strm:
                    writeSTRM(cleanStrms(path), cleanStrms(filename) ,link)
                else:
                    addLink(label,file,10,thumbnail,fanart,description,'','','',None,'',total=len(detail))
                    #xbmc.executebuiltin("Container.SetViewMode(500)")
            else:
                if strm:
                    fillPluginItems(file, media_type, file_type, strm, label, strm_type)
                else:
                    addDir(label,file,101,thumbnail,fanart,description,'','','')
                    #xbmc.executebuiltin("Container.SetViewMode(500)")    
        
def fillPlugins(type='video'):
    addon_log('fillPlugins, type = ' + type)
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
            if type == 'video' and path.startswith('plugin.video') and not path.startswith('plugin.video.pseudo.library'):
                thumbnail = removeNonAscii(thumbnails.group(1))
                fanart = removeNonAscii(fanarts.group(1))
                addDir(name,'plugin://'+path,101,thumbnail,fanart,description,type,'date','credits')

def getSources():
    addon_log('getSources')
    addDir('Video Plugins','video',1,icon,FANART,'description','genre','date','credits')
    addDir('Music Plugins','music',1,icon,FANART,'description','genre','date','credits')
    addDir('UPNP Servers','upnp://',2,icon,FANART,'description','genre','date','credits')
    addDir('PVR Backend','pvr://',2,icon,FANART,'description','genre','date','credits')

def getData(url,fanart):
    addon_log('getData, url = ' + type)
    
def playsetresolved(url,name,iconimage,setresolved=True):
    addon_log('playsetresolved')
    if setresolved:
        liz = xbmcgui.ListItem(name, iconImage=iconimage)
        liz.setInfo(type='Video', infoLabels={'Title':name})
        liz.setProperty("IsPlayable","true")
        liz.setPath(url)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
    else:
        xbmc.executebuiltin('XBMC.RunPlugin('+url+')')      
        
def addDir(name,url,mode,iconimage,fanart,description,genre,date,credits,showcontext=False):
    addon_log('addDir')
    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&fanart="+urllib.quote_plus(fanart)
    ok=True
    contextMenu = []
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo(type="Video", infoLabels={ "Title": name, "Plot": description, "Genre": genre, "dateadded": date, "credits": credits })
    liz.setProperty("Fanart_Image", fanart)
    contextMenu.append(('Create Strms','XBMC.RunPlugin(%s&mode=200&name=%s)'%(u, name)))
    liz.addContextMenuItems(contextMenu)
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    return ok
        
def addLink(name,url,mode,iconimage,fanart,description,genre,date,showcontext,playlist,regexs,total,setCookie=""): 
    addon_log('addLink') 
    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&fanart="+urllib.quote_plus(fanart)
    ok = True
    contextMenu =[]
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo(type="Video", infoLabels={ "Title": name, "Plot": description, "Genre": genre, "dateadded": date })
    liz.setProperty("Fanart_Image", fanart)
    liz.setProperty('IsPlayable', 'true')
    contextMenu.append(('Create Strm','XBMC.RunPlugin(%s&mode=200&name=%s)'%(u, name)))
    liz.addContextMenuItems(contextMenu)
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,totalItems=total)
    return ok
        
def getCommunitySources(browse=False):
    addon_log('getCommunitySources')
    
def removeStringElem(lst,string=''):
    return ([x for x in lst if x != string])
    
def replaceStringElem(lst,old='',new=''):
    return ([x.replace(old,new) for x in lst])
    
def makeSTRM(filepath, filename, url):
    addon_log('makeSTRM')
    filepath = os.path.join(STRM_LOC, filepath)
    if not xbmcvfs.exists(filepath): 
        xbmcvfs.mkdirs(filepath)
    fullpath = os.path.join(filepath, filename + '.strm')
    if xbmcvfs.exists(fullpath):
        if addon.getSetting('Clear_Strms') == 'true':
            xbmcvfs.delete(fullpath)
        else:
            return fullpath
    else:
        fle = open(fullpath, "w")
        fle.write("%s" % url)
        fle.close()
        return fullpath
        
def writeSTRM(path, file, url):
    addon_log('writeSTRM')
    makeSTRM(path, file, url)
          
def writeSettings2(url, type='Other'):
    addon_log('writeSettings2')
    thelist = []
    thefile = xbmc.translatePath(os.path.join(profile,'settings2.xml'))
    theentry = '|'.join([type,url])+'\n'
    
    if xbmcvfs.exists(thefile):
        fle = open(thefile, "r")
        thelist = fle.readlines()
        fle.close()
        
    if theentry not in thelist:
        thelist.append(theentry)
    else:
        thelist = replaceStringElem(thelist, theentry, theentry)
        
    try:
        fle = open(thefile, "w")
        fle.writelines(thelist)
        fle.close()
    except Exception,e:
        addon_log("writeSettings2, Failed " + str(e))
          
def isSettings2(url, type='Other'):
    addon_log('isSettings2')
    # parse settings2 for url return bool if found
    
def removeSettings2(url, type='Other'):       
    addon_log('removeSettings2')
    # parse settings2 for url remove entry
    
def getType():
    Types = ['TV','Episodes','Movies','Other']
    select = selectDialog(Types)
    if select >= 0:
        return Types[select]
    
def getURL(par):
    try:
        # if par.startswith('?url=plugin://plugin.video.pseudo.library/')
            # url = par.split('?url=')[1]
        # else:
        url = par.split('?url=')[1]
        url = url.split('&mode=')[0]
    except:
        url = None
    return url
     
##################
# GUI Tools #
##################

def handle_wait(time_to_wait,header,title): #*Thanks enen92
    dlg = xbmcgui.DialogProgress()
    dlg.create("PseudoTV Live", header)
    secs=0
    percent=0
    increment = int(100 / time_to_wait)
    cancelled = False
    while secs < time_to_wait:
        secs += 1
        percent = increment*secs
        secs_left = str((time_to_wait - secs))
        remaining_display = "Starts In " + str(secs_left) + " seconds, Cancel Channel Change?" 
        dlg.update(percent,title,remaining_display)
        xbmc.sleep(1000)
        if (dlg.iscanceled()):
            cancelled = True
            break
    if cancelled == True:
        return False
    else:
        dlg.close()
        return True

def show_busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialog)')

def hide_busy_dialog():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    while xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        time.sleep(.1)
        
def Error(header, line1= '', line2= '', line3= ''):
    dlg = xbmcgui.Dialog()
    dlg.ok(header, line1, line2, line3)
    del dlg

def infoDialog(str, header=ADDON_NAME, time=4000):
    try: xbmcgui.Dialog().notification(header, str, THUMB, time, sound=False)
    except: xbmc.executebuiltin("Notification(%s,%s, %s, %s)" % (header, str, time, THUMB))

def okDialog(str1, str2='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2)

def selectDialog(list, header=ADDON_NAME, autoclose=0):
    if len(list) > 0:
        select = xbmcgui.Dialog().select(header, list, autoclose)
        return select

def yesnoDialog(str1, str2='', header=ADDON_NAME, yes='', no=''):
    answer = xbmcgui.Dialog().yesno(header, str1, str2, '', yes, no)
    return answer
     
def browse(type, heading, shares, mask='', useThumbs=False, treatAsFolder=False, path='', enableMultiple=False):
    retval = xbmcgui.Dialog().browse(type, heading, shares, mask, useThumbs, treatAsFolder, path, enableMultiple)
    return retval
       
def get_params():
    addon_log('get_params')
    param=[]
    paramstring=sys.argv[2]
    addon_log('paramstring = ' + paramstring)
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
    addon_log('param = ' + str(param))
    return param

xbmcplugin.setContent(int(sys.argv[1]), 'movies')

try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_GENRE)
except:
    pass

params=get_params()

url=None
name=None
mode=None
playlist=None
iconimage=None
fanart=FANART
playlist=None
fav_mode=None
regexs=None

try:
    url=urllib.unquote_plus(params["url"]).decode('utf-8')
except:
    url=getURL(sys.argv[2])
    pass
try:
    name=urllib.unquote_plus(params["name"])
except:
    pass
try:
    iconimage=urllib.unquote_plus(params["iconimage"])
except:
    pass
try:
    fanart=urllib.unquote_plus(params["fanart"])
except:
    pass
try:
    mode=int(params["mode"])
except:
    pass
try:
    playlist=eval(urllib.unquote_plus(params["playlist"]).replace('||',','))
except:
    pass
try:
    fav_mode=int(params["fav_mode"])
except:
    pass
try:
    regexs=params["regexs"]
except:
    pass

addon_log("Mode: "+str(mode))
if not url is None:
    addon_log("URL: "+str(url.encode('utf-8')))
addon_log("Name: "+str(name))

if mode==None:
    addon_log("getSources")
    getSources()
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode==1:
    fillPlugins(url)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
elif mode==2:
    fillPluginItems(url)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
elif mode==10:
    addon_log("setResolvedUrl")
    item = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

elif mode==100:
    fillPlugins(url)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode==101:
    fillPluginItems(url)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
elif mode==200:
    addon_log("write multi strms")
    type = getType()
    writeSettings2(url, type)
    fillPluginItems(url, strm=True, strm_name=name, strm_type=type)

elif mode==201:
    addon_log("write single strm")
    # fillPluginItems(url)
    # makeSTRM(name, name, url)