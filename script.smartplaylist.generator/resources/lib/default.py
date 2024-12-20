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
from globals import *

class SPGenerator:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.dia    = None
        self.pct    = 0
        self.cache  = SimpleCache()
        self.cache.enable_mem_cache = False
        
        self.sysARG = sysARG
        self.kodi   = Kodi(self.cache)
        self.lists  = [LANGUAGE(32100),]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def build_lists(self, source, lists):
        def __buildMenu(item):
            return self.kodi.buildMenuListItem(item.get('name'),item.get('description'),item.get('icon',ICON),url=item.get('id'))
        
        with self.kodi.busy_dialog():
            listitems = poolit(__buildMenu)(lists)
            
        selects = self.kodi.selectDialog(listitems,header='%s %s'%(source,ADDON_NAME),preselect=self.kodi.findItemsInLST(listitems, self.kodi.getCacheSetting('%s.%s'%(ADDON_ID,source)), item_key='getPath', val_key='id'),)
        if not selects is None: 
            self.log('build_lists, source = %s, saving = %s'%(source,self.kodi.setCacheSetting('%s.%s'%(ADDON_ID,source),[{'name':listitems[select].getLabel(),'id':listitems[select].getPath(),'icon':listitems[select].getArt('icon')} for select in selects])))
        

    def match_items(self, source_items):
        matches      = {}
        func_list    = {'movies':self.kodi.get_kodi_movies,'tvshows':self.kodi.get_kodi_shows,'episodes':self.kodi.get_kodi_episodes}
        incl_missing = REAL_SETTINGS.getSetting('Incl_Missing') == 'true'

        def __match(kodi_item, type, list_items):
            for list_item in list_items:
                if   list_item.get('uniqueid',{}).get('imdb') == kodi_item.get('uniqueid',{}).get('imdb',random.random()): matches.setdefault(type,[]).append(kodi_item)
                elif list_item.get('uniqueid',{}).get('tmdb') == kodi_item.get('uniqueid',{}).get('tmdb',random.random()): matches.setdefault(type,[]).append(kodi_item)
                elif incl_missing:                                                                                         matches.setdefault(type,[]).append(list_item)
        
        for type, list_items in list(source_items.items()):
            self.log('match_items, Type: %s, INCL_MISSING: %s'%(type,incl_missing))
            if self.dia: self.dia = self.kodi.progressBGDialog(self.pct, self.dia, 'Matching %s'%(type.title()))
            poolit(__match)(func_list.get(type)(), **{'type':type,'list_items':list_items})
        return matches


    def create_xsp(self, list_name, match_items, match_val=REAL_SETTINGS.getSetting('Field_Type'), pretty_print=True):    
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
                    
        # incl_missing = REAL_SETTINGS.getSetting('Incl_Missing') == 'true'
        # for type, items in (list(match_items.items())):
            # if incl_missing:
                # match_field = 'title'
                # match_key   = 'title'
            # else: 
                # match_field = {'0':'title','1':'filename'}[str(match_val)].lower()
                # if type == 'tvshows' and match_field == 'filename':
                    # match_field = 'path'
                    # match_key   = 'file'
                # elif match_field == 'title':
                    # match_key = 'title'
                # else:
                    # match_key = 'file'
                
            if  type == 'movies':
                match_field = 'title'
                match_key   = 'title'
            elif type == 'tvshows':
                match_field = 'title'
                match_key   = 'showtitle'
            elif type == 'episodes':
                match_field = 'title'
                match_key   = 'title'
                
            self.log('create_xsp, Type: %s, Name: %s, Items: %s, Key: %s, Field: %s'%(type,list_name,len(items),match_key,match_field))
            root = ET.Element("smartplaylist")
            root.set("type",type)
            name = ET.SubElement(root, "name")
            name.text = "%s - %s"%(list_name,type.title())
            match = ET.SubElement(root, "match")
            match.text = "all"
            rule = ET.SubElement(root, "rule")
            rule.set("field", match_field)
            rule.set("operator", "is")
            
            for idx, item in enumerate(items):
                if not item.get(match_key): continue
                value = ET.SubElement(rule, "value")
                value.text = item.get(match_key)
                
            self.log('create_xsp, Out: %s'%(ET.tostring(root, encoding='unicode')))
            if pretty_print: __indent(root)
            tree = ET.ElementTree(root)
            path = os.path.join(xbmcvfs.translatePath(REAL_SETTINGS.getSetting('XSP_LOC')),'%s.xsp'%(validString(list_name)))
            self.log('create_xsp, File: %s'%(path))
            fle = xbmcvfs.File(path, 'w')
            tree.write(fle, encoding='utf-8', xml_declaration=True)
            fle.close()


    def run(self):
        try:    param = self.sysARG[1]
        except: param = None
        if param.startswith(('Build_','Select_')):
            source = param.split('_')[1]
            sys.path.insert(0, os.path.join(ADDON_PATH,'resources','lib','parsers'))
            module = __import__(source.lower())
            object = getattr(module,source)
            self.log('run, %s source = %s, module = %s, object = %s'%(param.split('_')[0], source,module.__name__,object.__name__))
                
            if 'Select_' in param and not self.kodi.isRunning(param):
                with self.kodi.busy_dialog(), self.kodi.setRunning(param):
                    self.build_lists(source,object(self.cache).get_lists())
                    
            elif 'Build_' in param and not self.kodi.isRunning(param):
                with self.kodi.setRunning(param):
                    list_items = self.kodi.getCacheSetting('%s.%s'%(ADDON_ID,source))
                    for idx, list_item in enumerate(list_items):
                        self.pct = int(idx*100//len(list_items))
                        self.dia = self.kodi.progressBGDialog(self.pct, message='Building Smartplaylist:\n%s'%(list_item.get('name')))
                        self.create_xsp(list_item.get('name'),self.match_items(object(self.cache).get_list_items(list_item.get('id'))))
                        REAL_SETTINGS.setSetting('%s_Update'%(source),datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT))
                        self.dia = self.kodi.progressBGDialog(100, message=LANGUAGE(32015))
                        if REAL_SETTINGS.getSetting('Notify_Enable') == "true":
                            self.kodi.notificationDialog('SmartPlaylists Updated:\n%s'%(list_item.get('name')))

        elif param == 'Run_All':
            for list in self.lists:
                self.kodi.executebuiltin('RunScript(special://home/addons/%s/resources/lib/default.py, Build_%s)'%(ADDON_ID,list))
            REAL_SETTINGS.setSetting('Last_Update',datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT))
                    
        elif self.kodi.yesnoDialog(LANGUAGE(32017)):
            self.kodi.executebuiltin('RunScript(special://home/addons/%s/resources/lib/default.py, Run_All)'%(ADDON_ID))
      
        else: REAL_SETTINGS.openSettings()
if __name__ == '__main__': SPGenerator(sys.argv).run()

