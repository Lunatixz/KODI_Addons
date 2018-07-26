#   Copyright (C) 2017 Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, re
import MyFont
import xbmcaddon, xbmc, xbmcgui, xbmcvfs
from xml.etree import ElementTree as ET

# Plugin Info
ADDON_ID             = 'script.pseudotv.live.patcher'
REAL_SETTINGS        = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID             = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME           = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH           = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION        = REAL_SETTINGS.getAddonInfo('version')
KODI_VER             = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[0:4])
ICON                 = os.path.join(ADDON_PATH, 'icon.png')
FANART               = os.path.join(ADDON_PATH, 'fanart.jpg')

# PTVL Info
PTVL_ID              = 'script.pseudotv.live'
PTVL_REAL_SETTINGS   = xbmcaddon.Addon(id=PTVL_ID)
PTVL_ID              = PTVL_REAL_SETTINGS.getAddonInfo('id')
PTVL_NAME            = PTVL_REAL_SETTINGS.getAddonInfo('name')
PTVL_PATH            = PTVL_REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
PTVL_VERSION         = PTVL_REAL_SETTINGS.getAddonInfo('version')
PTVL_ICON            = os.path.join(PTVL_PATH, 'icon.png')
PTVL_FANART          = os.path.join(PTVL_PATH, 'fanart.jpg')
PTVL_SELECT_SKIN_LOC = xbmc.translatePath(os.path.join(PTVL_PATH, 'resources', 'skins' , PTVL_REAL_SETTINGS.getSetting("SkinSelector")))

# Find XBMC Skin path
if xbmcvfs.exists(xbmc.translatePath(os.path.join('special://'  ,'skin','720p',''))):
    XBMC_SKIN_LOC = xbmc.translatePath(os.path.join('special://','skin','720p',''))
elif xbmcvfs.exists(xbmc.translatePath(os.path.join('special://','skin','1080i',''))):
    XBMC_SKIN_LOC = xbmc.translatePath(os.path.join('special://','skin','1080i',''))
else:
    XBMC_SKIN_LOC = xbmc.translatePath(os.path.join('special://','skin','xml',''))
    
# Find PTVL selected skin folder 720 or 1080i?
if xbmcvfs.exists(os.path.join(PTVL_SELECT_SKIN_LOC, '720p','')):
    PTVL_SKIN_SELECT = xbmc.translatePath(os.path.join(PTVL_SELECT_SKIN_LOC, '720p', ''))
else:
    PTVL_SKIN_SELECT = xbmc.translatePath(os.path.join(PTVL_SELECT_SKIN_LOC, '1080i', ''))

def log(msg, level = xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
 
def patchFont():    
    log("default: patchFont")
    path = os.path.join(PTVL_SKIN_SELECT, 'script.pseudotv.live.fonts.xml')
    if xbmcvfs.exists(path) == True:
        with open(path, 'rt') as f:
            tree = ET.parse(f)
        for node in tree.findall('font'):
            try:
                if node.attrib.get('res') == MyFont.getSkinRes():
                    return MyFont.addFont(node.attrib.get('name'), node.attrib.get('filename'), node.attrib.get('size'))
            except Exception,e:
                log('default: patchFont, failed! ' + str(e))
                return False
                
def patchSeekbar():
    log("default: patchSeekbar")
    DSPath = xbmc.translatePath(os.path.join(XBMC_SKIN_LOC, 'DialogSeekBar.xml'))
    #Patch dialogseekbar to ignore OSD for PTVL.
    try:
        found = False
        lineLST = file(DSPath, "r").readlines()   
        for line in lineLST:
            patch = line.find('<visible>Window.IsActive(fullscreenvideo) + !Window.IsActive(script.pseudotv.TVOverlay.xml) + !Window.IsActive(script.pseudotv.live.TVOverlay.xml)</visible>')
            if patch > 0:
                found = True
        log("default: patchSeekbar, found = " + str(found)) 
        if found == False:
            replaceAll(DSPath,'<window>','<window>\n\t<visible>Window.IsActive(fullscreenvideo) + !Window.IsActive(script.pseudotv.TVOverlay.xml) + !Window.IsActive(script.pseudotv.live.TVOverlay.xml)</visible>')
            xbmc.executebuiltin('XBMC.ReloadSkin()')
            log('default: patchSeekbar, Patched dialogseekbar.xml')
        return True
    except Exception,e:
        log('default: patchSeekbar, Failed! ' + str(e))
        return False
        
if xbmcgui.Window(10000).getProperty("PseudoTVPatcher") != "True":
    xbmcgui.Window(10000).setProperty("PseudoTVPatcher", "True")
    font = patchFont()
    skin = patchSeekbar()
    if int(font + skin) > 1:
        msg = "Complete"
    else:
        msg = "Failed!"
    xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (ADDON_NAME, 'Patch %s'%(msg), 1000, ICON))
    xbmcgui.Window(10000).setProperty("PseudoTVPatcher", "False")