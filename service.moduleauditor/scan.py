#   Copyright (C) 2019 Team-Kodi
#
#
# This file is part of Kodi Module Auditor
#
# Kodi Module Auditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Kodi Module Auditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kodi Module Auditor.  If not, see <http://www.gnu.org/licenses/>.

import sys, re, traceback, json, datetime, urllib, urllib2, zlib
import xbmc, xbmcplugin, xbmcaddon, xbmcgui
import xml.etree.ElementTree as ET

from simplecache import SimpleCache, use_cache

try:
    from urllib.parse import parse_qsl  # py3
except ImportError:
    from urlparse import parse_qsl # py2
    
# Plugin Info
ADDON_ID      = 'service.moduleauditor'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
TIMEOUT       = 15
MENU_ITEMS    = [LANGUAGE(32021),LANGUAGE(32022)]
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == "true"
BASE_URL      = 'http://mirrors.kodi.tv/addons/%s/addons.xml.gz'
BUILDS        =  {19:'matrix',18:'leia',17:'krypton',16:'jarvis',15:'isengard',14:'helix',13:'gotham'}
MOD_QUERY     = '{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.python.module","enabled":true,"properties":["name","version","author","enabled"]},"id":1}'
DISABLE_QUERY = '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":%s}, "id": 1}'
VER_QUERY     = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["version"]},"id":1}'


def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)

def loadJSON(string1):
    return json.loads(string1)
    
def dumpJSON(string1):
    return json.dumps(string1)

def getProperty(string1):
    try: return xbmcgui.Window(10000).getProperty('%s.%s'%(ADDON_ID,string1))
    except Exception as e: return ''
          
def setProperty(string1, string2):
    print 'setProperty', string1, string2
    try: xbmcgui.Window(10000).setProperty('%s.%s'%(ADDON_ID,string1), string2)
    except Exception as e: log("setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(string1):
    xbmcgui.Window(10000).clearProperty('%s.%s'%(ADDON_ID,string))
     
def inputDialog(heading=ADDON_NAME, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    retval = xbmcgui.Dialog().input(heading, default, key, opt, close)
    if len(retval) > 0: return retval    
    
def okDialog(str1, str2='', str3='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2, str3)

def yesnoDialog(str1, str2='', str3='', header=ADDON_NAME, yes='', no='', autoclose=0):
    return xbmcgui.Dialog().yesno(header, str1, str2, str3, no, yes, autoclose)
    
def notificationDialog(message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
    try: xbmcgui.Dialog().notification(header, message, icon, time, sound)
    except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
    
def textViewer(string1, header=ADDON_NAME, usemono=True):
    xbmcgui.Dialog().textviewer(header, (string1), usemono)
    
def selectDialog(list, header='', autoclose=0, preselect=None, useDetails=True):
    if preselect is None: preselect = -1
    select = xbmcgui.Dialog().select('%s - %s'%(ADDON_NAME,header), list, autoclose, preselect, useDetails)
    if select > -1: return select
    return None

def progressDialog(percent=0, control=None, string1='', string2='', string3='', header=ADDON_NAME):
    if percent == 0 and control is None:
        control = xbmcgui.DialogProgress()
        control.create(header, string1, string2, string3)
        control.update(percent, string1, string2, string3)
    if control is not None:
        if control.iscanceled(): return control.close()
        elif percent == 100: return control.close()
        else: control.update(percent, string1, string2, string3)
    return control
    
def busyDialog(percent=0, control=None):
    if percent == 0 and control is None:
        control = xbmcgui.DialogBusy()
        control.create()
        control.update(percent)
    if control is not None:
        if control.iscanceled: return control.close()
        elif percent == 100: return control.close()
        else: control.update(percent)
    return control
        
def buildListItem(item):
    log('buildListItem, item = ' + str(item))
    try: 
        label, label2, url = tuple(item)
        liz = xbmcgui.ListItem(label, label2, path=url)
        liz.setArt({'icon':ICON, 'thumb':ICON})
        return liz
    except Exception as e: log("buildListItem, Failed! " + str(e), xbmc.LOGERROR)
    return None
    
def cleanString(text):
    text = re.sub('\[COLOR=(.+?)\]','', text)
    text = text.replace('[/COLOR]' ,'')
    text = text.replace("[B]"      ,'')
    text = text.replace("[/B]"     ,'')
    text = text.replace("{filler}{status}" ,'')
    return text
    
def generateFiller(string1, string2, totline=75, fill='.'):
    filcnt = abs(totline - (len(cleanString(string1)) + len(cleanString(string2))))
    return (fill * filcnt)[:totline]

def filterErrors(items):
    return [item for item in items if item['error'] or not item['found']]
    
def sortItems(items):
    items = sorted(items, key=lambda item: item['myModule']['name'], reverse=False)
    items = sorted(items, key=lambda item: item['found'], reverse=False)
    items = sorted(items, key=lambda item: item['error'], reverse=True)
    return items

def getWhiteList():
    log('getWhiteList')
    return loadJSON((REAL_SETTINGS.getSetting("White_List").replace('&apos;','"')))
    
def setWhiteList(url):
    log('setWhiteList, url = ' + (url))
    whiteList = getWhiteList()
    whiteList['modules'].append(url)
    REAL_SETTINGS.setSetting("White_List",dumpJSON(whiteList))
    notificationDialog(LANGUAGE(32019))
          
class SCAN(object):
    def __init__(self):
        self.cache       = SimpleCache()
        self.silent      = False
        self.pDialog     = None
        self.pUpdate     = 0
        self.matchCNT    = 0
        self.errorCNT    = 0
        self.kodiModules = {}
        
        
    def sendJSON(self, command, life=datetime.timedelta(seconds=60)):
        log('sendJSON, command = ' + (command))
        cacheresponse = self.cache.get(ADDON_NAME + '.sendJSON, command = %s'%command)
        if DEBUG: cacheresponse = None
        if not cacheresponse:
            cacheresponse = xbmc.executeJSONRPC(command)
            self.cache.set(ADDON_NAME + '.sendJSON, command = %s'%command, cacheresponse, expiration=life)
        return loadJSON(cacheresponse)
        
        
    def okDisable(self, string1, addonName, addonID, state):
        if yesnoDialog(string1):
            query = DISABLE_QUERY%(addonID, str(state).lower())
            log('okDisable, addonID = %s, state = %s, query = %s'%(addonID, state, query))
            results = self.sendJSON(query, life=datetime.timedelta(seconds=1))
            if results:
                if results['result'] == "OK": 
                    notificationDialog(LANGUAGE(32010))
                    return True
                else: notificationDialog(LANGUAGE(30001))
        return False


    def openURL(self, url):
        try:
            log('openURL, url = ' + str(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                headers = {'User-Agent':'Kodi-Auditor'}
                req = urllib2.Request(url, None, headers)
                page = urllib2.urlopen(req, timeout=TIMEOUT)
                if page.headers.get('Content-Type').find('gzip') >= 0 or page.headers.get('Content-Type').find('application/octet-stream') >= 0:
                  d = zlib.decompressobj(16+zlib.MAX_WBITS)
                  cacheresponse = d.decompress(page.read())
                else: cacheresponse = page.read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheresponse, expiration=datetime.timedelta(hours=12))
            return cacheresponse
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            notificationDialog(LANGUAGE(30001))
            return ''

            
    def preliminary(self):
        self.validate(background=True)
        if self.errorCNT > 0: notificationDialog(LANGUAGE(32006)%(self.errorCNT,'s' if self.errorCNT > 1 else ''),time=8000)
        
            
    def validate(self, background=False):
        log('validate')
        if getProperty('Running') == 'True': return
        setProperty('Running','True')
        self.matchCNT  = 0
        self.errorCNT  = 0
        summary = self.scanModules(background)
        setProperty('Running','False')
        if background: return
        if yesnoDialog(LANGUAGE(32009), yes=LANGUAGE(32008), no=LANGUAGE(32007)): self.buildDetails(filterErrors(summary))
        else: textViewer('\n'.join([item['label'] for item in summary]))
        

    def checkID(self, id):
        log('checkID, id = %s'%id)
        match = self.scanID(id)
        if match: setProperty('checkID.%s'%(id),str(match[0][0]))
        
        
    def scanID(self, id):
        myModules = self.sendJSON(MOD_QUERY)['result']['addons']
        return [self.findModule(myModule, self.kodiModules[self.buildRepo()]) for myModule in myModules if myModule['addonid'].lower() == id.lower()]
                
                
    def buildDetails(self, items):
        log('buildDetails')
        select = -1
        listItems = []
        for item in items:
            addonID = (item['myModule'].get('id','') or item['myModule'].get('addonid',None))
            if addonID is None: continue
            author  = (item['myModule'].get('provider-name','') or item['myModule']['author']) 
            label   = '%s v.%s by %s'%(addonID,item['myModule']['version'],author)
            label2  = 'Enabled: [B]%s[/B] | %s'%(str(item['myModule'].get('enabled',True)),item['label2'])
            liz = buildListItem((label,label2,addonID))
            # liz.setProperty('myModule'  ,dumpJSON(item['myModule']))
            # liz.setProperty('kodiModule',dumpJSON(item['kodiModule']))
            listItems.append(liz)
        while select is not None:
            select  = selectDialog(listItems,LANGUAGE(32012), preselect=select)
            if select is None: return
            sitem   = listItems[select]
            label   = sitem.getLabel()
            label2  = sitem.getLabel2()
            addonID = sitem.getPath()
            pselect = selectDialog([buildListItem((mItem,'','')) for mItem in MENU_ITEMS], LANGUAGE(32025)%(addonID))
            if pselect == 0:
                state = not(cleanString(label2.split('Enabled: ')[1].split(' |')[0]))
                if self.okDisable(LANGUAGE(32011)%(label), label, addonID, state): listItems.pop(select)
            elif pselect == 1:
                setWhiteList(addonID)
                listItems.pop(select)

    
    def scanModules(self, background=False):
        log('scanModules')
        summary    = []
        progCNT    = 0
        if not background: self.pDialog = progressDialog()
        repository = self.buildRepo()
        whiteList  = getWhiteList()['modules']
        myModules  = self.sendJSON(MOD_QUERY)['result']['addons']
        pTotal     = len(myModules)
        if not background: self.pDialog  = progressDialog(1, control=self.pDialog, string1=LANGUAGE(32014), string2=LANGUAGE(32015)%(repository.title()))
        for idx1, myModule in enumerate(myModules):
            found   = False
            error   = False
            self.label   = '{name} v.{version}{filler}[B]{status}[/B]'.format(name=(myModule['name']),version=(myModule['version']),filler='{filler}',status='{status}')
            self.pUpdate = (idx1) * 100 // pTotal
            if not background: self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string1=LANGUAGE(32016))
            found, error, kodiModule = self.findModule(myModule, self.kodiModules[repository], background)
            log('scanModules, myModule = %s, repository = %s, found = %s'%(myModule['addonid'],repository, found))
            verifed = 'True' if found and not error else 'False'
            if not background: self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string2=LANGUAGE(32017)%((myModule['addonid'])))
            if found and error:
                self.status = LANGUAGE(32004)
                self.label  = self.label.format(filler=generateFiller(self.label,LANGUAGE(32004)),status=self.status)
                self.label2 = LANGUAGE(32004)
            elif found and not error:
                self.status = LANGUAGE(32002)
                self.label  = self.label.format(filler=generateFiller(self.label,LANGUAGE(32002)),status=self.status)
                self.label2 = LANGUAGE(32002)
            if not found and not error: 
                self.status = LANGUAGE(32003)
                self.label  = self.label.format(filler=generateFiller(self.label,LANGUAGE(32003)),status=self.status)
                self.label2 = LANGUAGE(32003)
            setProperty('checkID',self.status)
            if myModule['addonid'] in whiteList: continue
            summary.append({'found':found,'error':error,'label':self.label,'label2':self.label2,'kodiModule':(kodiModule),'myModule':(myModule)})
        summary = sortItems(summary)
        filler  = generateFiller(LANGUAGE(32013),'')
        filler  = filler[:(len(filler)/2)-1]
        summary.insert(0,{'found':False,'error':False,'label':'%s%s%s'%(filler,LANGUAGE(32013),filler),'label2':'','kodiModule':{},'myModule':{}})
        summary.insert(1,{'found':False,'error':False,'label':'\n','label2':'','kodiModule':{},'myModule':{}})
        if not background: self.pDialog = progressDialog(100, control=self.pDialog, string3=LANGUAGE(32018))
        return summary
        
        
    def findModule(self, myModule, kodiModules, background=True):
        found = False
        error = False
        whiteList  = getWhiteList()['modules']
        for kodiModule in kodiModules:
            if not background: self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string3='Checking %s ...'%((kodiModule['id'])))
            try:
                if myModule['addonid'].lower() == kodiModule['id'].lower():
                    found = True
                    self.matchCNT += 1
                    if myModule['version'] != kodiModule['version']:
                        if not myModule['addonid'] in whiteList:
                            error = True
                            self.errorCNT += 1
                    break
            except Exception as e: log('findModule, failed parse %s - %s'%(str(myModule),str(e)), xbmc.LOGERROR)
        if found: return found, error, kodiModule
        return found, error, myModule

        
    def buildRepo(self):
        busy = False if self.silent else busyDialog()
        repository = BUILDS[self.sendJSON(VER_QUERY)['result']['version']['major']]
        log('buildRepo, repository = %s'%(repository))
        self.kodiModules[repository] = list(self.buildModules(repository, busy))
        return repository
        
                
    def buildModules(self, branch, busy=False):
        log('buildModules, branch = ' + (branch))
        try:
            tree = ET.fromstring(self.openURL(BASE_URL%(branch)))
            for idx, elem in enumerate(tree.iter()):
                if busy: busy = busyDialog(idx + 1, busy)
                if elem.tag == 'addon': addon = elem.attrib.copy()
                if elem.tag == 'extension' and  elem.attrib.copy()['point'] == 'xbmc.python.module': yield (addon)
        except Exception as e: 
            log("buildModules, Failed! " + str(e), xbmc.LOGERROR)
            if busy: busyDialog(100)
        
        
    def getParams(self):
        try: return dict(parse_qsl(sys.argv[2][1:]))
        except: return None
            
            
if __name__ == '__main__':
    params = SCAN().getParams()
    try: id = urllib.unquote_plus(params["id"])
    except: id = None
    try: mode = int(params["mode"])
    except: mode = None
    if mode is None: SCAN().validate()
    elif mode == '-scanID':  SCAN().checkID(id)