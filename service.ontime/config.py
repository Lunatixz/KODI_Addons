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

import sys, os, re, traceback, json, time, datetime, schedule, ast
import xbmc, xbmcplugin, xbmcaddon, xbmcgui
from utils import *
    
class OnTime():
    def __init__(self):
        log('__init__')
        self.itemIDX     = 0
        self.mySchedule  = getMySchedule()
        self.configItems = {LANGUAGE(32016):self.buildPath  , LANGUAGE(32017):self.buildTitle,
                            LANGUAGE(32018):self.buildSCHED , LANGUAGE(32019):self.buildMSG,
                            LANGUAGE(32020):self.buildOffset, LANGUAGE(32021):self.buildPrompt,
                            LANGUAGE(32022):self.buildAction}
        self.buildList()
                
        
    def buildList(self, foList=0):
        log('buildList, foList = ' + str(foList))
        setProperty('CONFIG_OPEN','True')
        print self.mySchedule[0], type(self.mySchedule[0]), SETTING_TEMPT[0], type(SETTING_TEMPT[0]), self.mySchedule[0] == SETTING_TEMPT[0]
        if not self.mySchedule[0] == SETTING_TEMPT[0]: self.mySchedule.insert(0,SETTING_TEMPT[0])
        self.itemIDX = 0
        listitems = poolList(buildListItem, poolList(getItemInfo, self.mySchedule))
        listitems.insert(0, buildListItem(('+New Schedule', 'Create New Schedule', ICON, '', '')))
        print 'buildList', self.mySchedule, len(self.mySchedule), listitems, len(listitems)
        select = selectDialog(False, listitems, LANGUAGE(32026), preselect=foList)
        try:
            print 'buildList newitem', select
            if select is None: setMySchedule(self.mySchedule)
            elif select == 0: self.buildNew(select)
            else: self.buildItem(select)
        except: setMySchedule(self.mySchedule)
        setProperty('CONFIG_OPEN','False') 
        
       
    def buildNew(self, idx):
        self.itemIDX = idx
        item = self.mySchedule[idx]
        log('buildNew, item = ' + str(item))
        for config in list(self.configItems.values()): config(item)
        print 'buildNew', self.mySchedule, len(self.mySchedule), item
        self.mySchedule = setMySchedule(self.mySchedule)
        self.buildList(len(self.mySchedule))
        
     
    def buildItem(self, idx, foItem=0):
        try: 
            item = self.mySchedule[idx]
            log('buildItem, item = ' + str(item) + ', foItem = ' + str(foItem))
            listitem = buildItemInfo(item)
            select   = selectDialog(False, listitem, LANGUAGE(32035), preselect=foItem)
            self.configItems[listitem[select].getLabel2()](item)
            self.buildItem(idx, select)
        except: self.buildList(idx)
       
   
    def buildPath(self, item):
        log('buildPath')
        try: path = getPath(item)
        except: path = 'library://video/'
        try: 
            url = browseDialog(default=path, heading='%s %s'%(LANGUAGE(32037),LANGUAGE(32016)))
            if url is None: raise
            setPath(item,url)
            setThumb(item,(getProperty('INFOLABEL_THUMB') or getThumb(item)))
            setTitle(item,(getProperty('INFOLABEL_TITLE') or getTitle(item)))
        except Exception('buildPath, Invalid'): self.buildList()
        
        
    def buildTitle(self, item):
        log('buildTitle')
        try: title = getTitle(item) 
        except: title = ''
        setTitle(item,(inputDialog('%s %s'%(LANGUAGE(32023),LANGUAGE(32017)), title) or ''))
        
        
    def buildSCHED(self, item):
        log('buildSCHED, item = ' + str(item))
        schedTypes = SCHED_TYPES[SCHED_TYPE[selectDialog(False, buildSchedInfo())]]
        if schedTypes is None:
            opLabel = LANGUAGE(32046)
            while not xbmc.Monitor().abortRequested():
                try:
                    dateval = inputDialog(LANGUAGE(32044), key=xbmcgui.INPUT_DATE)
                    dateval = '{0:02d}/{1:02d}/{2:02d}'.format(*tuple(map(int,re.findall('(?:(\d+))',dateval))))
                    if validateDate(dateval): break
                except: return
            dtobj = datetime.datetime.strptime(dateval, '%d/%m/%Y')
            setDate(item,dtobj)
            setType(item,'single')
            schedType = dtobj.strftime('%A')
        else: 
            opLabel = LANGUAGE(32045)
            setType(item,'reoccurring')
            schedType  = (schedTypes[selectDialog(False, schedTypes, LANGUAGE(32036), useDetails=False)])
        log('buildSCHED, schedType = ' + str(schedType))
        if schedType in SCHED_INTVAL:
            opera = '' 
            while not xbmc.Monitor().abortRequested():
                try: 
                    intVal = int(inputDialog(LANGUAGE(32032)%(schedType.lower()), key=xbmcgui.INPUT_NUMERIC))
                    if validateRange(schedType, intVal): break
                except: return
        else:
            intVal = ''
            while not xbmc.Monitor().abortRequested():
                try: 
                    timeval = inputDialog(LANGUAGE(32030)%(opLabel,schedType), key=xbmcgui.INPUT_TIME)
                    timeval = '{0:02d}:{1:02d}'.format(*tuple(map(int,re.findall('(?:(\d+))',timeval))))
                    if validateTime(timeval): break
                except: return
            opera = SCHED_OPERA%timeval
        setSCHED(item,(SCHED_TEMPT.format(inttime=intVal, between='', interval=schedType.lower(), operator=opera, idx=self.itemIDX) or []))
    
    
    def buildMSG(self, item):
        log('buildMSG')
        try: msg = getMSG(item) 
        except: msg = DEFAULT_LABEL
        setMSG(item,(inputDialog('%s %s'%(LANGUAGE(32023),LANGUAGE(32019)), msg) or DEFAULT_LABEL))
        
        
    def buildOffset(self, item):
        log('buildOffset')
        try: offset = getOffset(item)
        except: offset = DEFAULT_OFFSET
        setOffset(item,(inputDialog('%s %s'%(LANGUAGE(32023),LANGUAGE(32020)), str(offset), key=xbmcgui.INPUT_NUMERIC) or DEFAULT_OFFSET))
        
        
    def buildPrompt(self, item):
        log('buildPrompt')
        try: prompt = getPrompt(item)
        except: prompt = DEFAULT_PROMPT
        setPrompt(item, (selectDialog(False, PROMPT_TYPES, LANGUAGE(32021), preselect=PROMPT_TYPES.index(PROMPT_TYPES[prompt]), useDetails=False) or DEFAULT_PROMPT))
        
        
    def buildAction(self, item):
        log('buildAction')
        try: action = getAction(item)
        except: action = DEFAULT_ACTION
        select = selectDialog(False, ACTION_TYPE, LANGUAGE(32022), preselect=ACTION_TYPE.index(ACTION_TYPES[action]), useDetails=False)
        if select is not None: select = select == 0
        else: select = DEFAULT_ACTION
        setAction(item, select)
        
if __name__ == '__main__': OnTime()