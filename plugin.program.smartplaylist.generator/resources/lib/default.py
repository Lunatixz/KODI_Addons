#   Copyright (C) 2024 Lunatixz
#
#
# This file is part of Smartplaylist Generator.
#
# Smartplaylist Generator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smartplaylist Generator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-
from globals  import *
from parsers  import trakt
from kodi     import Kodi

try:    from simplecache             import SimpleCache
except: from simplecache.simplecache import SimpleCache #pycharm stub

class SPGenerator:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.cache  = SimpleCache()
        self.cache.enable_mem_cache = False
        
        self.dia       = None
        self.msg       = ''
        self.pct       = 0
        self.tot       = 0
        self.cnt       = 0
        self.cntpct    = 0
        self.sysARG    = sysARG
        self.kodi      = Kodi(self.cache)
        self.modules   = {LANGUAGE(32100):trakt.Trakt(self.cache)}
        self.hasPseudo = xbmc.getCondVisibility('System.HasAddon(plugin.video.pseudotv.live)')
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def auto_lists(self):
        for source, module in list(self.modules.items()):
            self.log('auto_lists, source = %s, saving = %s'%(source,self.kodi.setCacheSetting('%s.%s'%(ADDON_ID,source),[{'name':item.get('name'),'id':item.get('id'),'icon':item.get('icon',ICON)} for item in module.get_lists()])))
        
        
    def build_lists(self, source, lists):
        def __buildMenu(item): return self.kodi.buildMenuListItem(item.get('name'),item.get('description'),item.get('icon',ICON),url=item.get('id'))
        with self.kodi.busy_dialog():
            listitems = poolit(__buildMenu)(lists)
        selects = self.kodi.selectDialog(listitems,header='%s %s'%(source,ADDON_NAME),preselect=self.kodi.findItemsInLST(listitems, self.kodi.getCacheSetting('%s.%s'%(ADDON_ID,source)), item_key='getPath', val_key='id'),)
        if not selects is None: self.log('build_lists, source = %s, saving = %s'%(source,self.kodi.setCacheSetting('%s.%s'%(ADDON_ID,source),[{'name':listitems[select].getLabel(),'id':listitems[select].getPath(),'icon':listitems[select].getArt('icon')} for select in selects])))
        

    def match_items(self, source_items):
        matches      = {}
        func_list    = {'movies'  : self.kodi.get_kodi_movies,
                        'tvshows' : self.kodi.get_kodi_tvshows,
                        'seasons' : self.kodi.get_kodi_tvshows,
                        'episodes': self.kodi.get_kodi_episodes,
                        'persons' : log}

        def __match(list_item, type, kodi_items):
            self.cntpct = round(self.cnt*100//self.tot)
            for kodi_item in kodi_items:
                match = None
                if self.dia: self.dia = self.kodi.progressBGDialog(self.pct, self.dia, '%s (%s%%)'%(self.msg, self.cntpct))
                for key in (list(list_item.get('uniqueid',{}).keys())):
                    if list_item.get('uniqueid',{}).get(key) == kodi_item.get('uniqueid',{}).get(key,random.random()): match = kodi_item
                    if match: 
                        self.log('match_items, __match found! type %s | %s -> %s'%(type,kodi_item.get('uniqueid'),list_item.get('uniqueid')))
                        if type == "seasons": matches.setdefault(type,[]).extend(self.kodi.get_kodi_seasons(kodi_item, list_item))
                        else:                 matches.setdefault(type,[]).append(match)
                        break
            self.cnt += 1
                
        for type, list_items in list(source_items.items()):
            self.log('match_items, type %s | list_items = %s'%(type, len(list_items)))
            kodi_items  = func_list.get(type)()
            self.msg    = '%s %s'%(LANGUAGE(32022),type.title().replace('Tvshows','TV Shows'))
            self.cntpct = 0
            self.cnt    = 0
            self.tot    = len(list(list_items))
            poolit(__match)(list_items, **{'type':type,'kodi_items':kodi_items})
        return matches


    def create_xsp(self, list_name, match_items, pretty_print=True):
        def __indent(elem, level=0):
            """
            Indent XML for pretty printing
            """
            i = "\n" + level*"  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for elem in elem:
                    __indent(elem, level+1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i

        
        mixed_names = []
        for type, items in (list(match_items.items())):
            if len(items) == 0: continue
            match_item = {'movies'  :{'match_type':type      , 'match_field':'title'   ,'match_key':'title','match_opr':'is'},
                          'tvshows' :{'match_type':type      , 'match_field':'title'   ,'match_key':'title','match_opr':'is'},
                          'seasons' :{'match_type':'episodes', 'match_field':'path'    ,'match_key':'file' ,'match_opr':'contains'},
                          'episodes':{'match_type':type      , 'match_field':'filename','match_key':'file' ,'match_opr':'contains'}}[type]
                
            self.log('create_xsp, type = %s, name = %s, items = %s, key = %s, field = %s'%(type,list_name,len(items),match_item.get('match_key'),match_item.get('match_field')))
            root = ET.Element("smartplaylist")
            root.set("type",match_item.get('match_type'))
            name = ET.SubElement(root, "name")
            name.text = "%s - %s"%(list_name,type.title().replace('Tvshows','TV Shows'))
            mixed_names.append("%s - %s"%(list_name,type.title().replace('Tvshows','TV Shows')))
            match = ET.SubElement(root, "match")
            match.text = "all"
            rule = ET.SubElement(root, "rule")
            rule.set("field", match_item.get('match_field'))
            rule.set("operator", match_item.get('match_opr'))
            
            values = []
            for idx, item in enumerate(items):
                if item.get(match_item.get('match_key')):
                    values.append(item)
                    value = ET.SubElement(rule, "value")
                    match_value = item.get(match_item.get('match_key'))
                    if match_item.get('match_field') == "filename": match_value = os.path.split(match_value)[1]
                    elif match_item.get('match_field') == "path":   match_value = os.path.split(match_value)[0]
                    value.text = match_value
                    
            if len(values) > 0:
                self.log('create_xsp, Out: %s'%(ET.tostring(root, encoding='unicode'))) 
                if pretty_print: __indent(root)
                tree = ET.ElementTree(root)
                path = os.path.join(xbmcvfs.translatePath(REAL_SETTINGS.getSetting('XSP_LOC')),'%s.xsp'%("%s - %s"%(validString(list_name),type.title().replace('Tvshows','TV Shows'))))
                self.log('create_xsp, File: %s'%(path))
                fle = xbmcvfs.File(path, 'w')
                tree.write(fle, encoding='utf-8', xml_declaration=True)
                fle.close()
                
                if REAL_SETTINGS.getSetting('Notify_Enable') == "true": self.kodi.notificationDialog('%s %s:\n%s'%(LANGUAGE(32017),{True:LANGUAGE(32020),False:LANGUAGE(32021)}[xbmcvfs.exists(path)],list_name))
            else: self.kodi.notificationDialog(LANGUAGE(32024)%(validString(list_name)))
        
        if self.hasPseudo and len(mixed_names) > 1:
            root = ET.Element("smartplaylist")
            root.set("type","mixed")
            name = ET.SubElement(root, "name")
            name.text = "%s - Mixed (PseudoTV)"%(list_name)
            match = ET.SubElement(root, "match")
            match.text = "all"
            
            values = []
            for idx, name in enumerate(mixed_names):
                rule = ET.SubElement(root, "rule")
                rule.set("field", "playlist")
                rule.set("operator", "is")
                values.append(name)
                value = ET.SubElement(rule, "value")
                value.text = name
                    
            if len(values) > 0:
                self.log('create_xsp, Out: %s'%(ET.tostring(root, encoding='unicode'))) 
                if pretty_print: __indent(root)
                tree = ET.ElementTree(root)
                path = REAL_SETTINGS.getSetting('XSP_LOC').replace(os.path.basename(os.path.normpath(REAL_SETTINGS.getSetting('XSP_LOC'))),"Mixed")
                path = os.path.join(xbmcvfs.translatePath(path),'%s.xsp'%("%s - %s"%(validString(list_name),"Mixed")))
                self.log('create_xsp, File: %s'%(path))
                fle = xbmcvfs.File(path, 'w')
                tree.write(fle, encoding='utf-8', xml_declaration=True)
                fle.close()
                
                if REAL_SETTINGS.getSetting('Notify_Enable') == "true": self.kodi.notificationDialog('%s %s:\n%s'%(LANGUAGE(32017),{True:LANGUAGE(32020),False:LANGUAGE(32021)}[xbmcvfs.exists(path)],list_name))
            else: self.kodi.notificationDialog(LANGUAGE(32024)%(validString(list_name)))


    def run(self):
        try:    param = self.sysARG[1]
        except: param = None
        if param.startswith(('Build_','Select_')):
            source = param.split('_')[1]
            module = self.modules.get(source) 
            if not module: return
            self.log('run, %s source = %s, module = %s'%(param.split('_')[0], source,module.__class__.__name__))
                
            if 'Select_' in param and not self.kodi.isRunning(source):
                with self.kodi.busy_dialog(), self.kodi.setRunning(source):
                    self.build_lists(source,module.get_lists())
                REAL_SETTINGS.openSettings()
                    
            elif 'Build_' in param and not self.kodi.isRunning(source):
                with self.kodi.setRunning(source):
                    list_items = self.kodi.getCacheSetting('%s.%s'%(ADDON_ID,source))
                    if len(list_items) > 0:
                        self.dia = self.kodi.progressBGDialog(self.pct)
                        for idx, list_item in enumerate(list_items):
                            self.pct = int((idx+1)*100//len(list_items))
                            self.dia = self.kodi.progressBGDialog(self.pct, self.dia, message='%s:\n%s'%(ADDON_NAME,list_item.get('name')))
                            self.create_xsp(list_item.get('name'),self.match_items(module.get_list_items(list_item.get('id'))))
                            REAL_SETTINGS.setSetting('Build_%s'%(source),datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT))
                    else: self.kodi.notificationDialog(LANGUAGE(32023)%(source))
                    
            else: self.kodi.notificationDialog(LANGUAGE(32025)%(ADDON_NAME))

        elif param == 'Run_All':
            if REAL_SETTINGS.getSetting('Auto_Enable') == 'true': self.auto_lists()
            for source in list(self.modules.keys()):
                self.kodi.executebuiltin('RunScript(special://home/addons/%s/resources/lib/default.py, Build_%s)'%(ADDON_ID,source))
            REAL_SETTINGS.setSetting('Last_Update',datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT))
        elif self.kodi.yesnoDialog('%s?'%(LANGUAGE(32110))): self.kodi.executebuiltin('RunScript(special://home/addons/%s/resources/lib/default.py, Run_All)'%(ADDON_ID))
        else: REAL_SETTINGS.openSettings()
        
if __name__ == '__main__': SPGenerator(sys.argv).run()

