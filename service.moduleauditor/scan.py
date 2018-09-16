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

import sys, re, traceback, json, urlparse, datetime, urllib, urllib2, itertools
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
BASE_URL      = 'http://mirrors.kodi.tv/addons/%s/addons.xml'
MOD_QUERY     = '{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.python.module","properties":["name","version","author","enabled"]},"id":1}'
VER_QUERY     = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["version"]},"id":1}'
DOTS          = itertools.cycle(['','.', '..', '...'])

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
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
    
def loadJSON(string1):
    return json.loads(string1)
    
def dumpJSON(string1):
    return json.dumps(string1)

def getProperty(string1):
    try: return xbmcgui.Window(10000).getProperty('%s.%s'%(ADDON_ID,string1))
    except Exception as e:
        log("getProperty, Failed! " + str(e), xbmc.LOGERROR)
        return ''
          
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

def okDisable(string1):
    if yesnoDialog(string1, no=LANGUAGE(30009), yes=LANGUAGE(30015)): 
        results = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":false}, "id": 1}'%ADDON_ID)
        if results and "OK" in results: notificationDialog(LANGUAGE(30016))
    else: sys.exit()
        
def yesnoDialog(str1, str2='', str3='', header=ADDON_NAME, yes='', no='', autoclose=0):
    return xbmcgui.Dialog().yesno(header, str1, str2, str3, no, yes, autoclose)
    
def notificationDialog(message, header=ADDON_NAME, sound=False, time=1000, icon=ICON):
    try: xbmcgui.Dialog().notification(header, message, icon, time, sound)
    except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
    
def textViewer(string1, header=ADDON_NAME, usemono=True):
    xbmcgui.Dialog().textviewer(header, uni(string1), usemono)
    
def progressDialog(percent=0, control=None, string1='', string2='', string3='', header=ADDON_NAME):
    if control is None:
        if percent == 0: control = xbmcgui.DialogProgress()
        if control is not None:control.create(header, string1, string2, string3)
    else:
        if control.iscanceled(): return False
        if percent == 100: return control.close()
        control.update(percent, string1, string2, string3)
    return control
    
def cleanString(text):
    text = re.sub('\[COLOR=(.+?)\]','', text)
    text = text.replace('[/COLOR]' ,'')
    text = text.replace("[B]"      ,'')
    text = text.replace("[/B]"     ,'')
    text = text.replace("{filler}{status}" ,'')
    return text
    
def generateFiller(string1, string2, totline=88, fill='.'):
    filcnt  = totline - (len(cleanString(string1)) + len(cleanString(string2)))
    return (fill * filcnt)[:totline]
    
class SCAN(object):
    def __init__(self):
        self.pUpdate = 0
        self.pDialog = None
        self.kodiModules = {}
        self.cache   = SimpleCache()
        self.builds  = sorted(BUILDS, reverse=True)
        self.buildRepos()
        
        
    def sendJSON(self, command):
        log('sendJSON, command = ' + (command))
        cacheresponse = self.cache.get(ADDON_NAME + '.sendJSON, command = %s'%command)
        if not cacheresponse:
            cacheresponse = loadJSON(xbmc.executeJSONRPC(command))
            self.cache.set(ADDON_NAME + '.sendJSON, command = %s'%command, cacheresponse, expiration=datetime.timedelta(minutes=15))
        return cacheresponse
        
        
    def openURL(self, url):
        try:
            log('openURL, url = ' + str(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                cacheresponse = (urllib2.urlopen(urllib2.Request(url), timeout=TIMEOUT)).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheresponse, expiration=datetime.timedelta(minutes=15))
                xbmc.sleep(1000)
            return cacheresponse
        except Exception as e:
            log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return ''

            
    def validate(self):
        log('validate')
        lineLST = []
        #todo create listitem/selectDialog and trigger disable
        summary = self.scanModules()
        for item in summary: lineLST.append(item['label'])
        textViewer('\n'.join(lineLST))
        
    
    def scanModules(self):
        log('scanModules')
        summary   = []
        progCNT   = 0
        myModules = self.sendJSON(MOD_QUERY)['result']['addons']
        myBuild   = self.sendJSON(VER_QUERY)['result']['version']['major']
        topBranch = self.builds[self.builds.index(myBuild):]
        pTotal    = len(topBranch) + len(myModules)
        for idx1, myModule in enumerate(myModules):
            found   = False
            error   = False
            self.label   = '{name} v.{version}{filler}[B]{status}[/B]'.format(name=uni(myModule['name']),version=uni(myModule['version']),filler='{filler}',status='{status}')
            self.label2  = '{id} by {author} {enabled}'.format(id=uni(myModule['addonid']),author=uni(myModule['author']),enabled=uni(myModule['enabled']))
            self.pUpdate = (idx1) * 100 // pTotal
            self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string1='Auditing Modules ...', string2='Verifying %s'%(uni(myModule['addonid'])))
            for idx2, branch in enumerate(topBranch):
                repository = BUILDS[branch]
                found, error, kodiModule = self.findModule(myModule, self.kodiModules[repository])
                log('scanModules, myModule = %s, repository = %s, found = %s'%(myModule['addonid'],repository, found))
                verifed = 'True' if found and not error else 'False'
                self.pUpdate = (idx1+ idx2) * 100 // pTotal
                self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string2='Verifying %s'%(uni(myModule['addonid'])))
                if found: 
                    self.label  = self.label.format(filler=generateFiller(self.label,LANGUAGE(32002)),status=LANGUAGE(32002))
                    break
            if not found: self.label = self.label.format(filler=generateFiller(self.label,LANGUAGE(32003)),status=LANGUAGE(32003))
            summary.append({'found':found,'error':error,'label':self.label,'label2':self.label2,'kodiModule':(kodiModule),'myModule':(myModule)})
        summary = sorted(summary, key=lambda item: item['found'], reverse=False)
        summary = sorted(summary, key=lambda item: item['error'], reverse=True)
        self.pDialog = progressDialog(100, control=self.pDialog, string3='Audit Complete')
        return summary
        
        
    def findModule(self, myModule, kodiModules):
        found = False
        error = False
        for kodiModule in kodiModules:
            self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string3='Checking %s ...'%(uni(kodiModule['id'])))
            try:
                if myModule['addonid'] == kodiModule['id']:
                    found = True
                    if myModule['version'] != kodiModule['version']:
                        error = True
                        self.label  = self.label.format(filler=generateFiller(self.label,LANGUAGE(32004)),status=LANGUAGE(32004))
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
        
        
    def buildRepos(self): 
        self.pDialog = progressDialog(0, string1="Evaluating Kodi Repositories %s"%(DOTS.next()))
        self.poolList(self.buildRepo, self.builds)
    
    
    def buildRepo(self, build):
        repository   = BUILDS[build]
        self.pUpdate = (self.builds.index(build)) * 100 // len(BUILDS)
        self.pDialog = progressDialog(self.pUpdate, control=self.pDialog, string1="Evaluating Kodi Repositories %s"%(DOTS.next()), string2='reviewing %s'%(repository))
        log('buildRepo, repository = %s'%(repository))
        self.kodiModules[repository] = list(self.buildModules(repository))
        
        
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
        elif mode == 0: self.validate()

if __name__ == '__main__': SCAN().run()