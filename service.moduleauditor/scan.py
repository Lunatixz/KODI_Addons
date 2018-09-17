#   Copyright (C) 2018 Team-Kodi
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

import sys, re, traceback, json, urlparse
import datetime, urllib, urllib2, itertools, random
import xbmc, xbmcplugin, xbmcaddon, xbmcgui
import xml.etree.ElementTree as ET

from simplecache import SimpleCache, use_cache
try:
    from multiprocessing import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
except: ENABLE_POOL = False

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
BUILDS        = {18:'leia',17:'krypton',16:'jarvis',15:'isengard',14:'helix',13:'gotham'}
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == "true"
WAIT          = int(REAL_SETTINGS.getSetting('Scan_Wait'))
BASE_URL      = 'http://mirrors.kodi.tv/addons/%s/addons.xml'
MOD_QUERY     = '{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.python.module","enabled":true,"properties":["name","version","author","enabled"]},"id":1}'
VER_QUERY     = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["version"]},"id":1}'
DOTS          = itertools.cycle(['','.', '..', '...'])

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode): string = string.encode('ascii', 'ignore')
    return string
    
def uni(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode): string = string.encode('utf-8', 'ignore' )
        else: string = ascii(string)
    return string
    
def loadJSON(string1):
    return json.loads(string1)
    
def dumpJSON(string1):
    return json.dumps(string1)

def getProperty(string1):
    try: return xbmcgui.Window(10000).getProperty('%s.%s'%(ADDON_ID,string1))
    except Exception as e: return ''
          
def setProperty(string1, string2):
    try: xbmcgui.Window(10000).setProperty('%s.%s'%(ADDON_ID,string1), string2)
    except Exception as e: log("setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(string1):
    xbmcgui.Window(10000).clearProperty('%s.%s'%(ADDON_ID,string))
     
def inputDialog(heading=ADDON_NAME, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    retval = xbmcgui.Dialog().input(heading, default, key, opt, close)
    if len(retval) > 0: return retval    
    
def okDialog(str1, str2='', str3='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2, str3)

def okDisable(string1, addonName, addonID, state):
    if yesnoDialog(string1):
        query = '{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":%s}, "id": 1}'%(addonID, str(state).lower())
        log('okDisable, addonID = %s, state = %s, query = %s'%(addonID, state, query))
        results = xbmc.executeJSONRPC(query)
        if results and "OK" in results: 
            notificationDialog(LANGUAGE(32010))
            return True
        else: notificationDialog(LANGUAGE(30001))
    else: return False
        
def yesnoDialog(str1, str2='', str3='', header=ADDON_NAME, yes='', no='', autoclose=0):
    return xbmcgui.Dialog().yesno(header, str1, str2, str3, no, yes, autoclose)
    
def notificationDialog(message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
    try: xbmcgui.Dialog().notification(header, message, icon, time, sound)
    except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
    
def textViewer(string1, header=ADDON_NAME, usemono=True, silent=False):
    if silent: return
    xbmcgui.Dialog().textviewer(header, uni(string1), usemono)
    
def selectDialog(list, header='', autoclose=0, preselect=None, useDetails=True):
    if preselect is None: preselect = -1
    select = xbmcgui.Dialog().select('%s - %s'%(ADDON_NAME,header), list, autoclose, preselect, useDetails)
    if select > -1: return select
    return None
    
def progressDialog(percent=0, control=None, string1='', string2='', string3='', header=ADDON_NAME, silent=False):
    if silent: return
    if control is None:
        if percent == 0: control = xbmcgui.DialogProgress()
        if control is not None:control.create(header, string1, string2, string3)
    else:
        if control.iscanceled(): return False
        if percent == 100: return control.close()
        control.update(percent, string1, string2, string3)
    return control
    
def buildListItem(item):
    log('buildListItem, item = ' + str(item))
    try: 
        label, label2, url = tuple(item)
        liz = xbmcgui.ListItem(label, label2, path=url)
        liz.setArt({'icon':ICON, 'thumb':ICON})
        # contextMenu = [('Enable Module','XBMC.RunPlugin(%s)'%(sys.argv[0]+"?mode=1&name="+item+"&url="+url))]
        # liz.addContextMenuItems(contextMenu)
        return liz
    except Exception as e: log("buildListItem, Failed! " + str(e), xbmc.LOGERROR)
    return
    
def cleanString(text):
    text = re.sub('\[COLOR=(.+?)\]','', text)
    text = text.replace('[/COLOR]' ,'')
    text = text.replace("[B]"      ,'')
    text = text.replace("[/B]"     ,'')
    text = text.replace("{filler}{status}" ,'')
    return text
    
def generateFiller(string1, string2, totline=75, fill='.'):
    filcnt  = totline - (len(cleanString(string1)) + len(cleanString(string2)))
    return (fill * filcnt)[:totline]

def filterItems(items):
    for item in items:
        if not item['error'] and item['found']: continue
        yield item
            
class SCAN(object):
    def __init__(self):
        self.cache       = SimpleCache()
        self.silent      = False
        self.pDialog     = None
        self.pUpdate     = 0
        self.matchCNT    = 0
        self.errorCNT    = 0
        self.kodiModules = {}
        self.topBranch   = BUILDS[self.sendJSON(VER_QUERY)['result']['version']['major']]
        
        
    def sendJSON(self, command):
        log('sendJSON, command = ' + (command))
        cacheresponse = self.cache.get(ADDON_NAME + '.sendJSON, command = %s'%command)
        if not cacheresponse:
            cacheresponse = loadJSON(xbmc.executeJSONRPC(command))
            self.cache.set(ADDON_NAME + '.sendJSON, command = %s'%command, cacheresponse, expiration=datetime.timedelta(minutes=1))
        return cacheresponse
        
        
    def openURL(self, url):
        try:
            log('openURL, url = ' + str(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                cacheresponse = (urllib2.urlopen(urllib2.Request(url), timeout=TIMEOUT)).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheresponse, expiration=datetime.timedelta(minutes=random.randrange(10, 20, 1)))
                xbmc.sleep(2000)
            return cacheresponse
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            notificationDialog(LANGUAGE(30001))
            return ''

            
    def preliminary(self): 
        self.silent = True
        self.validate()
        if self.matchCNT + self.errorCNT > 0: notificationDialog(LANGUAGE(32006)%(self.errorCNT),time=8000)
        
            
    def validate(self):
        log('validate')
        self.matchCNT  = 0
        self.errorCNT  = 0
        self.buildRepo(self.topBranch)
        summary = self.scanModules()
        if self.silent: return
        if yesnoDialog(LANGUAGE(32009), yes=LANGUAGE(32008), no=LANGUAGE(32007)): self.buildDetails(filterItems(summary))
        else: textViewer('\n'.join([item['label'] for item in summary]))

       
    def buildDetails(self, items):
        log('buildDetails')
        select = 0
        listItems = []
        for item in items:
            addonID = (item['kodiModule'].get('id','') or item['kodiModule']['addonid'])
            author  = (item['kodiModule'].get('provider-name','') or item['kodiModule']['author']) 
            label   = '%s v.%s by %s'%(addonID,item['kodiModule']['version'],author)
            label2  = 'Enabled: [B]%s[/B] | %s'%(str(item['kodiModule'].get('enabled',True)),item['label2'])
            listItems.append((label,label2,addonID))
        while select is not None:
            select  = selectDialog(self.poolList(buildListItem, listItems),LANGUAGE(32012), preselect=select)
            if select is None: return
            item    = listItems[select]
            state   = not (cleanString(item[1].split('Enabled: ')[1]) == 'True')
            string1 = LANGUAGE(32011)%(item[0])
            if okDisable(string1, item[0], item[2], state): listItems.pop(select)

            
    def enableModule(self, name, url):
        log('enableModule, name = %s, url = %s'%(name, url))
    
    
    def scanModules(self):
        log('scanModules')
        summary    = []
        progCNT    = 0
        repository = self.topBranch
        myModules  = self.sendJSON(MOD_QUERY)['result']['addons']
        pTotal     = len(myModules)
        for idx1, myModule in enumerate(myModules):
            found   = False
            error   = False
            self.label   = '{name} v.{version}{filler}[B]{status}[/B]'.format(name=uni(myModule['name']),version=uni(myModule['version']),filler='{filler}',status='{status}')
            self.pUpdate = (idx1) * 100 // pTotal
            self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string1='Auditing Modules ...', string2='Verifying %s'%(uni(myModule['addonid'])), silent=self.silent)
            found, error, kodiModule = self.findModule(myModule, self.kodiModules[repository])
            log('scanModules, myModule = %s, repository = %s, found = %s'%(myModule['addonid'],repository, found))
            verifed = 'True' if found and not error else 'False'
            self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string2='Verifying %s'%(uni(myModule['addonid'])), silent=self.silent)
            if found and error:
                self.label  = self.label.format(filler=generateFiller(self.label,LANGUAGE(32004)),status=LANGUAGE(32004))
                self.label2 = LANGUAGE(32004)
            elif found and not error: 
                self.label  = self.label.format(filler=generateFiller(self.label,LANGUAGE(32002)),status=LANGUAGE(32002))
                self.label2 = LANGUAGE(32002)
            if not found and not error: 
                self.label  = self.label.format(filler=generateFiller(self.label,LANGUAGE(32003)),status=LANGUAGE(32003))
                self.label2 = LANGUAGE(32003)
            summary.append({'found':found,'error':error,'label':self.label,'label2':self.label2,'kodiModule':(kodiModule),'myModule':(myModule)})
        summary = sorted(summary, key=lambda item: item['kodiModule']['name'], reverse=False)
        summary = sorted(summary, key=lambda item: item['found'], reverse=False)
        summary = sorted(summary, key=lambda item: item['error'], reverse=True)
        self.pDialog = progressDialog(100, control=self.pDialog, string3='Audit Complete', silent=self.silent)
        return summary
        
        
    def findModule(self, myModule, kodiModules):
        found = False
        error = False
        for kodiModule in kodiModules:
            self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string3='Checking %s ...'%(uni(kodiModule['id'])), silent=self.silent)
            try:
                if myModule['addonid'] == kodiModule['id']:
                    found = True
                    self.matchCNT += 1
                    if myModule['version'] != kodiModule['version']:
                        error = True
                        self.errorCNT += 1
                    break
            except Exception as e: log('findModule, failed parse %s - %s'%(str(myModule),str(e)), xbmc.LOGERROR)
        if found: return found, error, kodiModule
        return found, error, myModule
        
        
    def poolList(self, method, items):
        results = []
        if ENABLE_POOL:
            pool = ThreadPool(cpu_count())
            results = pool.imap_unordered(method, items)
            pool.close()
            pool.join()
        else: results = [method(item) for item in items]
        results = filter(None, results)
        return results
        
        
    def buildRepo(self, repository): 
        log('buildRepo, repository = %s'%(repository))
        self.pDialog = progressDialog(0, string1="Building Kodi Repositories ...", string2='reviewing %s'%(repository.title()), silent=self.silent)
        self.kodiModules[repository] = list(self.buildModules(repository))
        self.pDialog = progressDialog(100, string1="Building Kodi Repositories ...", string2='reviewing %s'%(repository.title()), silent=self.silent)
    
        
    def buildModules(self, branch):
        log('buildModules, branch = ' + (branch))
        tree = ET.fromstring (self.openURL(BASE_URL%(branch)))
        for elem in tree.iter():
            if elem.tag == 'addon': addon = elem.attrib.copy()
            if elem.tag == 'extension' and elem.attrib.copy()['point'] == 'xbmc.python.module': yield (addon)
            
            
    def getParams(self):
        try: return dict(urlparse.parse_qsl(sys.argv[2][1:]))
        except: return None
            
            
    def run(self):  
        params=self.getParams()
        try: url=urllib.unquote_plus(params["url"])
        except: url=None
        try: name=urllib.unquote_plus(params["name"])
        except: name=None
        try: mode=int(params["mode"])
        except: mode=None
        log("Mode: "+str(mode))
        log("URL : "+str(url))
        log("Name: "+str(name))

        if mode==None:  self.validate()
        if mode==1:     self.enableModule(name, url)

if __name__ == '__main__': SCAN().run()