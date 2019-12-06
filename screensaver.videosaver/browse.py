#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of Video ScreenSaver.
#
# Video ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Video ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Video ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import sys, traceback
import xbmc, xbmcaddon, xbmcgui
    
try:
    from urllib.parse import parse_qsl  # py3
except ImportError:
    from urlparse import parse_qsl # py2
    
# Plugin Info
ADDON_ID       = 'screensaver.videosaver'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)

def selectDialog(multi, list, header=ADDON_NAME, autoclose=0, preselect=None, useDetails=True):
    if multi == True:
        if not preselect: preselect = []
        select = xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
    else:
        if not preselect:  preselect = -1
        select = xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
    if select > -1: return select
        
def buildMenuListItem(label1="", label2="", iconImage="", thumbnailImage="", path="", offscreen=True):
    try: return xbmcgui.ListItem(label1, label2, iconImage, thumbnailImage, path, offscreen)
    except: return xbmcgui.ListItem(label1, label2, iconImage, thumbnailImage, path)
        
def browseDialog(multi, type=0, heading=ADDON_NAME, shares='', mask='', useThumbs=True, treatAsFolder=False, default='', prompt=False):
    options  = [{"label":"Video"    , "label2":"List Video Sources"},
                {"label":"Music"    , "label2":"List Music Sources"},
                {"label":"Files"    , "label2":"List File Sources"},
                {"label":"Pictures" , "label2":"List Picture Sources"},
                {"label":"Local"    , "label2":"List Local Drives"},
                {"label":"Network"  , "label2":"List Local Drives and Network Share"},
                {"label":"Resources", "label2":"List Resource Plugins"}]
    if prompt:
        listitems = [buildMenuListItem(option['label'],option['label2'],ICON) for option in options]
        select = selectDialog(False, listitems, 'Select Source Type')
        if select > -1: shares = options[select]['label'].lower().replace("network","")
        else: return
    if multi == True:
        # https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
        retval = xbmcgui.Dialog().browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
    else:
        # https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
        retval = xbmcgui.Dialog().browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
    return (retval or "")
        

if __name__ == '__main__':
    if not xbmcgui.Window(10000).getProperty("%s.Running"%(ADDON_ID)) == "True":
        xbmcgui.Window(10000).setProperty("%s.Running"%(ADDON_ID), "True")
        if sys.argv[1] == '-file':
            retval = browseDialog(False, 1, LANGUAGE(32014), treatAsFolder=False, prompt=True)
            if len(retval) > 0: REAL_SETTINGS.setSetting("VideoFile",retval)
        elif sys.argv[1] == '-folder': 
            retval = browseDialog(False, 0, LANGUAGE(32015), treatAsFolder=True, prompt=True)
            if len(retval) > 0: REAL_SETTINGS.setSetting("VideoFolder",retval)
        xbmcgui.Window(10000).setProperty("%s.Running"%(ADDON_ID), "False")
            