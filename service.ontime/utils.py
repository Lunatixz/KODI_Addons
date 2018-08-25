#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of OnTime
#
# OnTime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OnTime is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OnTime.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, re, traceback, json, datetime, time, schedule, ast
import xbmc, xbmcplugin, xbmcaddon, xbmcgui, xbmcvfs

# Plugin Info
ADDON_ID       = 'service.ontime'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString
if xbmcvfs.exists(SETTINGS_LOC) == False: xbmcvfs.mkdir(SETTINGS_LOC)

## GLOBALS ##
DEBUG          = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
MY_SCHED       = os.path.join(SETTINGS_LOC,'schedule.json')
DEFAULT_OFFSET = int(REAL_SETTINGS.getSetting('Default_Offset'))
DEFAULT_PROMPT = int(REAL_SETTINGS.getSetting('Default_Prompt'))
DEFAULT_ACTION = int(REAL_SETTINGS.getSetting('Default_Action')) == 0
DEFAULT_LABEL  = REAL_SETTINGS.getSetting('Default_Label')
PROMPT_TYPES   = [LANGUAGE(32003),LANGUAGE(32004),LANGUAGE(32005),LANGUAGE(32006)]
ACTION_TYPES   = {True:LANGUAGE(32010),False:LANGUAGE(32011)}
ACTION_TYPE    = [LANGUAGE(32010),LANGUAGE(32011)]
LOGO_URL       = 'https://dummyimage.com/512x512/035e8b/FFFFFF.png&text=%s'
SCHED_INTER    = ['Day', 'Week', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
SCHED_INTVAL   = ['Seconds', 'Minutes', 'Hours', 'Days', 'Weeks']
SCHED_TYPES    = {LANGUAGE(32039):SCHED_INTVAL, LANGUAGE(32040):None, LANGUAGE(32038):SCHED_INTER}
SCHED_TYPE     = [LANGUAGE(32040),LANGUAGE(32038),LANGUAGE(32039)]
INTVAL_LIMITS  = {'Seconds':59, 'Minutes':59, 'Hours':23, 'Days':7, 'Weeks':52}
SCHED_OPERA    = ".at('%s')"
SCHED_BETWEEN  = '.to(%s)'
SCHED_TEMPT    = 'schedule.every({inttime}){between}.{interval}{operator}.tag({idx})'
SETTING_TEMPT  = [{'tag': 0, 'type': None, 'job': None, 'date': None, 'args': [DEFAULT_OFFSET, DEFAULT_PROMPT, DEFAULT_LABEL, DEFAULT_ACTION, '', ICON, '']}]
THREE_DAYS_SEC = 259200

try:
    from multiprocessing import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
except Exception: ENABLE_POOL = False
    
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)
    
def uni(string, encoding='utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode): string = unicode(string, encoding)
    return string

def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode): string = string.encode('ascii', 'ignore')
    return string
       
def trimString(content, limit=250, suffix='...'):
    if len(content) <= limit: return content
    return content[:limit].rsplit(' ', 1)[0]+suffix
     
def getPluginMeta(plugin):
    if plugin[0:9] == 'plugin://':
        plugin = plugin.replace("plugin://","")
        plugin = splitall(plugin)[0]
    else: plugin = plugin
    pluginID = xbmcaddon.Addon(plugin)
    return {'name':pluginID.getAddonInfo('name'), 'author':pluginID.getAddonInfo('author'), 'icon':pluginID.getAddonInfo('icon'), 'fanart':pluginID.getAddonInfo('fanart'), 'id':pluginID.getAddonInfo('id')}

def notificationDialog(message, header=ADDON_NAME, show=True, sound=False, time=1000, icon=ICON):
    log('notificationDialog: ' + message)
    if show == True:
        try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception as e:
            log("notificationDialog Failed! " + str(e), xbmc.LOGERROR)
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))

def browseDialog(type=1, heading='', shares='video', mask='', useThumbs=True, treatAsFolder=False, default='library://video/'):
    setProperty('MONITOR_INFOLABEL','True') 
    retval = xbmcgui.Dialog().browseSingle(type, '%s %s'%(ADDON_NAME,heading), shares, mask, useThumbs, treatAsFolder, default)
    setProperty('MONITOR_INFOLABEL','False')
    if len(retval) > 0:  return retval
    return None
    
def selectDialog(multi, list, header='', autoclose=0, preselect=None, useDetails=True):
    if multi == True:
        if preselect is None: preselect = []
        select = xbmcgui.Dialog().multiselect('%s %s'%(ADDON_NAME,header), list, autoclose, preselect, useDetails)
    else:
        if preselect is None: preselect = -1
        select = xbmcgui.Dialog().select('%s %s'%(ADDON_NAME,header), list, autoclose, preselect, useDetails)
    if select > -1: return select
    return None

def inputDialog(string1, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    # Types:
    # - xbmcgui.INPUT_ALPHANUM (standard keyboard)
    # - xbmcgui.INPUT_NUMERIC (format: #)
    # - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
    # - xbmcgui.INPUT_TIME (format: HH:MM)
    # - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
    # - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
    retval = xbmcgui.Dialog().input(string1, default, key, opt, close)
    if len(retval) > 0: return retval 
    return None   
    
def yesnoDialog(str1, str2='', str3='', header='', yes='', no='', autoclose=0):
    return xbmcgui.Dialog().yesno('%s %s'%(ADDON_NAME,header), str1, str2, str3, no, yes, autoclose)
     
def okDialog(str1, str2='', str3='', header=''):
    return xbmcgui.Dialog().ok('%s %s'%(ADDON_NAME,header), str1, str2, str3)
    
def textViewer(str1, header=''):
    return xbmcgui.Dialog().textviewer('%s %s'%(ADDON_NAME,header), str1)
    
def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts
  
def loadJson(string):
    try:
        if isinstance(string,dict): return string
        elif isinstance(string,basestring): return json.loads(uni(string))
        else: return {}
    except Exception as e: 
        log("loadJson, Failed! " + str(e), xbmc.LOGERROR) 
        return ''
    
def dumpJson(mydict, sortkey=True):
    return json.dumps(mydict, sort_keys=sortkey)

def getProperty(string1):
    try: return xbmcgui.Window(10000).getProperty('%s.%s'%(ADDON_ID,string1))
    except Exception as e:
        log("getProperty, Failed! " + str(e), xbmc.LOGERROR)
        return ''
          
def setProperty(string1, string2):
    try: xbmcgui.Window(10000).setProperty('%s.%s'%(ADDON_ID,string1), (string2))
    except Exception as e: log("setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(string):
    xbmcgui.Window(10000).clearProperty('%s.%s'%(ADDON_ID,string1))
     
def unquote(string):
    return urllib.unquote(string)
        
def quote(string):
    return urllib.quote(string)
        
def roundToHalfHour(thetime):
    n = datetime.datetime.fromtimestamp(thetime)
    delta = datetime.timedelta(minutes=30)
    if n.minute > 29: n = n.replace(minute=30, second=0, microsecond=0)
    else: n = n.replace(minute=0, second=0, microsecond=0)
    return time.mktime(n.timetuple())

def progressDialog(percent=0, control=None, string1=DEFAULT_LABEL, type=DEFAULT_PROMPT, header=ADDON_NAME):
    if control is None:
        if   percent == 0 and type == 0: control = xbmcgui.DialogProgress()
        elif percent == 0 and type == 1: control = xbmcgui.DialogProgressBG()
        if control is not None: control.create(header, string1)
    else:
        try: 
            if control.iscanceled(): return False
        except: pass
        if percent == 100: return control.close()
        control.update(percent, string1)
    return control

def poolList(method, items):
    results = []
    if ENABLE_POOL:
        pool = ThreadPool(cpu_count())
        results = pool.imap_unordered(method, items)
        pool.close()
        pool.join()
    else: results = [method(item) for item in items]
    results = filter(None, results)
    return results

def buildListItem(item):
    log('buildListItem, item = ' + str(item))
    try: 
        label, label2, thumb, url, tag = tuple(item)
        liz = xbmcgui.ListItem(label, label2, iconImage=LOGO_URL%(label[0].upper()), thumbnailImage=thumb, path=url)
        if tag: 
            contextMenu = [('Remove Event','XBMC.RunPlugin(%s)'%(sys.argv[0]+"?mode=removeEvent&tag="+str(tag)))]
            liz.addContextMenuItems(contextMenu)
        return liz
    except Exception as e: log("buildListItem, Failed! " + str(e), xbmc.LOGERROR)
    return
    
def getItemInfo(item):
    log('getItemInfo, item = ' + str(item))
    return (getTitle(item) , getSCHED(item) , getThumb(item), getPath(item), getTag(item))
    
def buildItemInfo(item):
    log('buildItemInfo, item = ' + str(item))
    listitems = []
    thumb = getThumb(item)
    listitems.append(buildListItem((getPath(item)                 , LANGUAGE(32016), thumb, '', getTag(item))))
    listitems.append(buildListItem((getTitle(item)                , LANGUAGE(32017), thumb, '', getTag(item))))
    listitems.append(buildListItem((getSCHED(item)                , LANGUAGE(32018), thumb, '', getTag(item))))
    listitems.append(buildListItem((getMSG(item)                  , LANGUAGE(32019), thumb, '', getTag(item))))
    listitems.append(buildListItem((str(getOffset(item))          , LANGUAGE(32020), thumb, '', getTag(item))))
    listitems.append(buildListItem((PROMPT_TYPES[getPrompt(item)] , LANGUAGE(32021), thumb, '', getTag(item))))
    listitems.append(buildListItem((ACTION_TYPES[getAction(item)] , LANGUAGE(32022), thumb, '', getTag(item))))
    return listitems
    
def buildSchedInfo():
    log('buildSchedInfo')
    listitems = []
    listitems.append(buildListItem((LANGUAGE(32040)               , LANGUAGE(32043), ICON , '', '')))
    listitems.append(buildListItem((LANGUAGE(32038)               , LANGUAGE(32041), ICON , '', '')))
    listitems.append(buildListItem((LANGUAGE(32039)               , LANGUAGE(32042), ICON , '', '')))
    return listitems
    
def getPath(item):
    log('getPath')
    return item['args'][6]
    
def getTitle(item):
    log('getTitle')
    return item['args'][4]
    
def getType(item):
    log('getType')
    return item['type'] 
    
def getSCHED(item):
    log('getSCHED')
    return item['job']  
    
def getDate(item):
    log('getDate')
    return item.get('date',datetime.datetime.now())
    
def getTag(item):
    log('getTag')
    return item['tag']
    
def getMSG(item):
    log('getMSG')
    return item['args'][2]
    
def getOffset(item):
    log('getOffset')
    return item['args'][0]
    
def getPrompt(item):
    log('getPrompt')
    return item['args'][1]
    
def getAction(item):
    log('getAction')
    return item['args'][3]
    
def getThumb(item):
    log('getThumb')
    return item['args'][5]
    
def setPath(item, new):
    log('setPath')
    item['args'][6] = new
    
def setTitle(item, new):
    log('setTitle')
    item['args'][4] = new
    
def setSCHED(item, new):
    log('setSCHED, new = ' + str(new))
    item['job']   = new
    
def setType(item, new='reoccurring'):
    log('setType, new = ' + str(new))
    item['type']  = new
    
def setDate(item, new):
    log('setDate')
    if isinstance(new, datetime.datetime): new = new.__str__()
    item['date']   = new
    
def setTag(item, new):
    log('setDate')
    item['tag']    = new
    
def setMSG(item, new):
    log('setMSG')
    item['args'][2] = new
    
def setOffset(item, new):
    log('setOffset')
    if isinstance(new, basestring): new = int(new)
    item['args'][0] = new
    
def setPrompt(item, new):
    log('setPrompt')
    if isinstance(new, basestring): new = int(new)
    item['args'][1] = new
    
def setAction(item, new):
    if isinstance(new, basestring): new = new in ['True','true']
    log('setAction, new = ' + str(new))
    item['args'][3] = new
    
def setThumb(item, new):
    log('setThumb')
    item['args'][5] = new
    
def getMySchedule():
    log('getMySchedule')
    fle = xbmcvfs.File(MY_SCHED)
    try: data = json.load(fle)['jobs']
    except Exception as e: 
        log("getMySchedule, Failed! " + str(e), xbmc.LOGERROR) 
        data = SETTING_TEMPT
    fle.close()
    return data
    
def setMySchedule(mySchedule):
    log('setMySchedule')
    fle = xbmcvfs.File(MY_SCHED, 'w')
    json.dump({"jobs":mySchedule}, fle)
    fle.close()
    setLastUpdate(datetime.datetime.now().strftime('%Y-%m-%dT%I:%M:00'))
    notificationDialog(LANGUAGE(32025))
    return mySchedule
    
def clearSchedule():
    setMySchedule(SETTING_TEMPT)
    notificationDialog(LANGUAGE(32048), time=1500)
    
def removeEvent(tag):
    mySchedule = getMySchedule()
    mySchedule = [item for item in SETTING_TEMPT if item['tag'] != tag]
    setMySchedule(mySchedule)
       
def getInfoLabel():
    log('getInfoLabel')
    setProperty('INFOLABEL_THUMB',(xbmc.getInfoLabel('ListItem.Thumb')  or xbmc.getInfoLabel('ListItem.Art(thumb)')  or xbmc.getInfoLabel('ListItem.Icon')))
    setProperty('INFOLABEL_TITLE',(xbmc.getInfoLabel('ListItem.Label')  or xbmc.getInfoLabel('ListItem.TVShowTitle') or xbmc.getInfoLabel('ListItem.Title')))
    xbmc.sleep(500)
    
def validateTime(input, frmt='%H:%M'):
    log('validateTime, input = ' + str(input))
    try:
        time.strptime(input, frmt)
        state = True
    except ValueError: 
        state = False
        notificationDialog(LANGUAGE(32031))
    log('validateTime, state = ' + str(state))
    return state
    
def validateRange(typ, val):
    log('validateRange, typ = ' + typ + ', val = ' + str(val))
    if 0 < val <= INTVAL_LIMITS[typ]: state = True
    else:
        state = False
        notificationDialog(LANGUAGE(32031))
    log('validateRange, state = ' + str(state))
    return state
    
def validateDate(input):
    log('validateDate, input = ' + str(input))
    try:
        datetime.datetime.strptime(input, '%d/%m/%Y')
        state = True
    except ValueError: 
        state = False
        notificationDialog(LANGUAGE(32031))
    log('validateDate, state = ' + str(state))
    return state
    
def getLastUpdate():
    try: return datetime.datetime.strptime(REAL_SETTINGS.getSetting('Last_Update'),'%Y-%m-%dT%I:%M:00')
    except: return datetime.datetime.now()
    
def setLastUpdate(dtobj):
    REAL_SETTINGS.setSetting('Last_Update',dtobj)