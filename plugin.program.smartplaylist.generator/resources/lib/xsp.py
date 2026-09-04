#   Copyright (C) 2025 Lunatixz
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

class XSP:
    MANIFEST_KEY = 'xsp.manifest'

    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.cache  = SimpleCache()
        self.cache.enable_mem_cache = False
        self.kodi = Kodi(self.cache)
        self._manifest = self.cache.get(self.MANIFEST_KEY, ADDON_VERSION, True) or {}


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _unique_path(self, path, uid):
        # File-name collision handling: the same playlist (same uid) rebuilds
        # onto its file; a different playlist that would land on the same file
        # gets a " - N" suffix. Manifest persists so this holds across runs.
        owner = self._manifest.get(path)
        if owner == uid: return path
        if owner is None:
            self._manifest[path] = uid
        else:
            base, ext = os.path.splitext(path)
            n = 2
            while True:
                candidate = '%s - %s%s'%(base, n, ext)
                if self._manifest.get(candidate) in (None, uid):
                    path = candidate
                    self._manifest[path] = uid
                    break
                n += 1
        self.cache.set(self.MANIFEST_KEY, self._manifest, ADDON_VERSION, datetime.timedelta(days=90), True)
        return path


    def _write(self, root, path, list_name, pretty_print):
        self.log('create, Out: %s'%(ET.tostring(root, encoding='unicode')))
        if pretty_print: ET.indent(root)
        fle = xbmcvfs.File(path, 'w')
        ET.ElementTree(root).write(fle, encoding='utf-8', xml_declaration=True)
        fle.close()
        
        
    def create(self, list_name, match_items, pretty_print=True, uid=''):
        mixed_names = []
        for type, items in (list(match_items.items())):
            if len(items) == 0: continue
            match_item = {'movies'  :{'match_type':type      , 'match_field':'title'   ,'match_key':'title','match_opr':'is'},
                          'tvshows' :{'match_type':type      , 'match_field':'title'   ,'match_key':'title','match_opr':'is'},
                          'seasons' :{'match_type':'episodes', 'match_field':'path'    ,'match_key':'file' ,'match_opr':'contains'},
                          'episodes':{'match_type':type      , 'match_field':'filename','match_key':'file' ,'match_opr':'contains'}}[type]
                
            self.log('create, type = %s, name = %s, items = %s, key = %s, field = %s'%(type,list_name,len(items),match_item.get('match_key'),match_item.get('match_field')))
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
                path = os.path.join(xbmcvfs.translatePath(REAL_SETTINGS.getSetting('XSP_LOC')),'%s.xsp'%("%s - %s"%(validString(list_name),type.title().replace('Tvshows','TV Shows'))))
                path = self._unique_path(path, uid)
                self.log('create, File: %s'%(path))
                self._write(root, path, list_name, pretty_print)
            else: self.kodi.notificationDialog(LANGUAGE(32024)%(validString(list_name)))
        
        if self.kodi.hasPseudoTV and len(mixed_names) > 1:
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
                path = REAL_SETTINGS.getSetting('XSP_LOC').replace(os.path.basename(os.path.normpath(REAL_SETTINGS.getSetting('XSP_LOC'))),"Mixed")
                path = os.path.join(xbmcvfs.translatePath(path),'%s.xsp'%("%s - %s"%(validString(list_name),"Mixed")))
                path = self._unique_path(path, uid)
                self.log('create, File: %s'%(path))
                self._write(root, path, list_name, pretty_print)
            else: self.kodi.notificationDialog(LANGUAGE(32024)%(validString(list_name)))
