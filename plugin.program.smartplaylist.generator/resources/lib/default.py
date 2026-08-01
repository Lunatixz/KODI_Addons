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
from parsers  import trakt, imdb
from kodi     import Kodi
from xsp      import XSP

try:    from simplecache             import SimpleCache
except: from simplecache.simplecache import SimpleCache #pycharm stub

class SPGenerator:
    dia    = None
    msg    = ''
    pct    = 0
    tot    = 0
    cnt    = 0
    cntpct = 0
    
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.cache  = SimpleCache()
        self.cache.enable_mem_cache = False
        
        self.sysARG    = sysARG
        self.kodi      = Kodi(self.cache)
        self.xsp       = XSP()
        self.modules   = {LANGUAGE(32100):trakt.Trakt(self.cache),LANGUAGE(32112):imdb.IMDB(self.cache)}


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def auto_lists(self):
        for source, module in list(self.modules.items()):
            try: self.log('auto_lists, source = %s, saving = %s'%(source,self.kodi.setCacheSetting('%s.%s'%(ADDON_ID,source),[{'name':item.get('name'),'id':item.get('id'),'icon':item.get('icon',ICON)} for item in module.get_lists()])))
            except Exception: pass
        
        
    def build_lists(self, source, lists):
        def __buildMenu(item): return self.kodi.buildMenuListItem(item.get('name'),item.get('description'),item.get('icon',ICON),url=item.get('id'))
        with self.kodi.busy_dialog(): listitems = poolit(__buildMenu)(lists)
        selects = self.kodi.selectDialog(listitems,header='%s %s'%(source,ADDON_NAME),preselect=self.kodi.findItemsInLST(listitems, self.kodi.getCacheSetting('%s.%s'%(ADDON_ID,source)), item_key='getPath', val_key='id'),)
        if not selects is None: self.log('build_lists, source = %s, saving = %s'%(source,self.kodi.setCacheSetting('%s.%s'%(ADDON_ID,source),[{'name':listitems[select].getLabel(),'id':listitems[select].getPath(),'icon':listitems[select].getArt('icon')} for select in selects])))
        

    def match_items(self, source_items):
        matches   = {}
        func_list = {'movies'  : self.kodi.get_kodi_movies,
                     'tvshows' : self.kodi.get_kodi_tvshows,
                     'seasons' : self.kodi.get_kodi_tvshows,
                     'episodes': self.kodi.get_kodi_episodes}

        def __match(list_item, type, index):
            self.cntpct = round(self.cnt*100//self.tot)
            if self.dia: self.dia = self.kodi.progressBGDialog(self.pct, self.dia, '%s (%s%%)'%(self.msg, self.cntpct))
            for key in (list(list_item.get('uniqueid',{}).keys())):
                kodi_item = index.get((key, list_item.get('uniqueid',{}).get(key)))
                if not kodi_item: continue
                self.log('match_items, __match found! type %s | %s -> %s'%(type,kodi_item.get('uniqueid'),list_item.get('uniqueid')))
                if type == "seasons": matches.setdefault(type,[]).extend(self.kodi.get_kodi_seasons(kodi_item, list_item))
                else:                 matches.setdefault(type,[]).append(kodi_item)
                break
            self.cnt += 1

        for type, list_items in list(source_items.items()):
            self.log('match_items, type %s | list_items = %s'%(type, len(list_items)))
            index = {}
            for kodi_item in func_list.get(type)():
                for key, value in list((kodi_item.get('uniqueid') or {}).items()):
                    index.setdefault((key, value), kodi_item)
            self.msg    = '%s %s'%(LANGUAGE(32022),type.title().replace('Tvshows','TV Shows'))
            self.cntpct = 0
            self.cnt    = 0
            self.tot    = len(list(list_items))
            poolit(__match)(list_items, **{'type':type,'index':index})
        return matches


    def build_person(self, module, person):
        name = person.get('name')
        self.log('build_person, name = %s, id = %s'%(name, person.get('id')))
        tmlLST = self.match_items(module.get_trakt_person(person.get('id')))
        if tmlLST: self.xsp.create(name, tmlLST)


    def run(self, param="None"):
        if param.startswith(('Build_','Select_')):
            source = param.split('_')[1]
            module = self.modules.get(source) 
            if not module: return
            self.log('run, %s source = %s, module = %s'%(param.split('_')[0], source,module.__class__.__name__))
                
            if 'Select_' in param and not self.kodi.isRunning(source):
                with self.kodi.busy_dialog(), self.kodi.setRunning(source):
                    tmlLST = module.get_lists()
                    self.log("run, get_lists\n%s"%(tmlLST))
                    self.build_lists(source, tmlLST)
                REAL_SETTINGS.openSettings()
                    
            elif 'Build_' in param and not self.kodi.isRunning(source):
                if REAL_SETTINGS.getSettingBool('Enable_%s'%(source)):
                    with self.kodi.setRunning(source):
                        list_items = self.kodi.getCacheSetting('%s.%s'%(ADDON_ID,source))
                        if len(list_items) > 0:
                            self.dia = self.kodi.progressBGDialog(self.pct)
                            for idx, list_item in enumerate(list_items):
                                self.pct = int((idx+1)*100//len(list_items))
                                self.dia = self.kodi.progressBGDialog(self.pct, self.dia, message='%s:\n%s'%(ADDON_NAME,list_item.get('name')))
                                tmlLST = module.get_list_items(list_item.get('id'))
                                persons = tmlLST.pop('persons', [])
                                self.log("run, get_list_items\n%s"%(tmlLST))
                                self.xsp.create(list_item.get('name'),self.match_items(tmlLST))
                                for person in persons: self.build_person(module, person)
                                REAL_SETTINGS.setSetting('Build_%s'%(source),datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT))
                        else: self.kodi.notificationDialog(LANGUAGE(32023)%(source))
            else: self.kodi.notificationDialog(LANGUAGE(32025)%(ADDON_NAME))

        elif param == 'Run_All':
            if REAL_SETTINGS.getSettingBool('Auto_Enable'): self.auto_lists()
            for source in list(self.modules.keys()):
                self.kodi.executebuiltin('RunScript(special://home/addons/%s/resources/lib/default.py, Build_%s)'%(ADDON_ID,source))
            REAL_SETTINGS.setSetting('Last_Update',datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT))
        elif self.kodi.yesnoDialog('%s?'%(LANGUAGE(32110))):
            self.kodi.executebuiltin('RunScript(special://home/addons/%s/resources/lib/default.py, Run_All)'%(ADDON_ID))
        else:
            REAL_SETTINGS.openSettings()
        

if __name__ == '__main__': SPGenerator(sys.argv).run(sys.argv[1])

