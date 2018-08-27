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

import sys, os, re, traceback, json, time, _strptime, datetime, schedule, ast
import xbmc, xbmcplugin, xbmcaddon, xbmcgui
from utils import *

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.Player())
        
        
    def onPlayBackStarted(self):
        log('onPlayBackStarted')
        
        
    def onPlayBackEnded(self):
        log('onPlayBackEnded')
        
        
    def onPlayBackStopped(self):
        log('onPlayBackStopped')
        

class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self, xbmc.Monitor())
        self.pendingChange = False
        
        
    def onSettingsChanged(self):
        log('onSettingsChanged')
        if self.pendingChange == True: return
        self.pendingChange = True
        self.onChange()
        
        
    def onChange(self):
        log('onChange')
        if self.myService.loadMySchedule(): self.pendingChange = False
       
       
class Service():
    def __init__(self):
        self.myMonitor   = Monitor()
        self.myMonitor.myService = self
        self.myPlayer    = Player()
        self.myPlayer.myService  = self
        
        
    def handleWait(self, args):
        log('handleWait, args = ' + str(args))
        secs = 0
        waitTime, waitType, waitLabel, waitAction, actionTitle, actionThumb, actionPath, actionTag = tuple(args)
        if waitType == 3: self.myMonitor.waitForAbort(waitTime) #silent wait
        elif waitType == 2: #notify 3 times before start
            while not self.myMonitor.abortRequested():
                if (secs > waitTime): break
                invtime = int(round(waitTime//3))
                notificationDialog(waitLabel.format(title=actionTitle, secondsleft=str(waitTime - secs)), sound=True, time=2000, icon=actionThumb)
                self.myMonitor.waitForAbort(invtime)
                secs += invtime
        else: #dialog
            prog = progressDialog(0, string1=ADDON_NAME,  type=waitType)
            while not self.myMonitor.abortRequested():
                secs += 1
                if (secs > waitTime): break
                if progressDialog((int(100 // waitTime) * secs), prog, waitLabel.format(title=actionTitle, secondsleft=str(waitTime - secs))) == False: return False 
                self.myMonitor.waitForAbort(1)
            progressDialog(100, prog, type=waitType)
        if waitAction: return self.handleAction(actionTitle, actionThumb, actionPath, actionTag)

        
    def handleAction(self, actionTitle, actionThumb, actionPath, actionTag):
        log('handleAction')
        liz =  xbmcgui.ListItem(actionTitle, thumbnailImage=actionThumb, path=actionPath)
        liz.setProperty('IsPlayable', 'true')
        self.myPlayer.play(actionPath, liz)
        if actionTag: schedule.clear(actionTag)
        
        
    def loadMySchedule(self):
        schedule.clear()
        schedule.every(3).days.do(self.loadMySchedule)
        mySchedule = getMySchedule()
        log('loadMySchedule, mySchedule = ' + dumpJson(mySchedule))
        # job   = "schedule.every(25).seconds"; string
        # *args = (DEFAULT_OFFSET, DEFAULT_PROMPT, DEFAULT_LABEL, DEFAULT_ACTION, 'actionTitle', 'actionThumb', 'actionPath'); tuple'
        nowtime   = datetime.datetime.now()
        threedays = nowtime + datetime.timedelta(days=3)
        tprompt   = int(round(2000 // len(mySchedule)))
        for item in mySchedule: 
            try:
                job  = item['job']
                date = item['date']
                sing = item['type'] == 'single' #single - delete entry from json after eval
                tag  = item['tag']
                args = item['args']
                print date, sing, tag, args
                if sing == False: tag = ''
                args.append(tag)
                if job is None: continue
                elif not job.startswith('schedule.'): #minimum eval safety net 
                    log("loadMySchedule, WARNING SETTING TAMPERED WITH! ", xbmc.LOGWARNING)
                    continue
                elif date is not None: 
                    try: dtobj = datetime.datetime.strptime(date, '%Y-%m-%d 00:00:00')
                    except TypeError: dtobj = datetime.datetime(*(time.strptime(date, '%Y-%m-%d 00:00:00')[0:6]))
                    if threedays <= dtobj <= nowtime: log('loadMySchedule, loading date = ' + date)
                    else: continue
                    #todo pass job when dateobj isn't now, delete if old
                self.evalJob(job,(args)) #ast.literal_eval to strict?
                notificationDialog(LANGUAGE(32024),time=tprompt)
            except Exception as e: log("loadMySchedule, Failed! " + str(e), xbmc.LOGERROR)
        return True
        
        
    def evalJob(self, job, args):
        log('evalJob, job = ' + str(job) + ', args = ' + str(args))
        try: eval(job).do(self.handleWait, args)
        # try: ast.literal_eval(job).do(self.handleWait, args)
        except Exception as e: log("evalJob, Failed! " + str(e), xbmc.LOGERROR)
            
           
    def serviceStart(self): 
        self.loadMySchedule()
        while not self.myMonitor.abortRequested():
            if getProperty('MONITOR_INFOLABEL') == "True": getInfoLabel() #requires high sample rate
            elif self.myMonitor.waitForAbort(5): break
            elif xbmcgui.getCurrentWindowDialogId() == 10140: continue
            elif getProperty('CONFIG_OPEN') == "True" or self.myMonitor.pendingChange == True: continue #don't run during change
            else: schedule.run_pending()
        
if __name__ == '__main__': Service().serviceStart()

