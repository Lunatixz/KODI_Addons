#   Copyright (C) 2017 Steveb1968, Kevin S. Graer
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

import os, sys, re, traceback, fileinput
import xbmcaddon, xbmc, xbmcgui, xbmcvfs
from xml.etree import ElementTree as ET

# Plugin Info
ADDON_ID             = 'script.pseudotv.live.utilities'
REAL_SETTINGS        = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID             = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME           = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH           = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION        = REAL_SETTINGS.getAddonInfo('version')
ICON                 = REAL_SETTINGS.getAddonInfo('icon')
FANART               = REAL_SETTINGS.getAddonInfo('fanart')
KODI_VER             = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[0:4])
KODI_SKIN            = xbmc.getSkinDir()
KODI_SKIN_LOC        = xbmc.translatePath('special://skin')
KODI_FONT_LOC        = os.path.join(KODI_SKIN_LOC, 'fonts')
SKIN_XML_PARAMS      = ['xml','1080p','1080i','720p']
SKIN_DIA_PARAMS      = ['DialogFullScreenInfo.xml','DialogSeekBar.xml']
SELECT_PARAMS        = ['Apply Seekbar Patch','Apply Custom Font Patch']

# PTVL Info
PTVL_ID              = 'script.pseudotv.live'
PTVL_REAL_SETTINGS   = xbmcaddon.Addon(id=PTVL_ID)
PTVL_ID              = PTVL_REAL_SETTINGS.getAddonInfo('id')
PTVL_NAME            = PTVL_REAL_SETTINGS.getAddonInfo('name')
PTVL_PATH            = PTVL_REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
PTVL_VERSION         = PTVL_REAL_SETTINGS.getAddonInfo('version')
ICON                 = REAL_SETTINGS.getAddonInfo('icon')
FANART               = REAL_SETTINGS.getAddonInfo('fanart')
PTVL_SKIN            = PTVL_REAL_SETTINGS.getSetting("SkinSelector")
PTVL_SKIN_LOC        = xbmc.translatePath(os.path.join(PTVL_PATH, 'resources', 'skins' , PTVL_SKIN))
PTVL_FONT_LOC        = os.path.join(PTVL_SKIN_LOC,'fonts')
DEBUG                = PTVL_REAL_SETTINGS.getSetting('enable_Debug') == "true"

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level == xbmc.LOGDEBUG:
        return
    if level == xbmc.LOGERROR:
        msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
      
def replaceAll(file, searchExp, replaceExp):
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp,replaceExp)
        sys.stdout.write(line)
  
def findXMLPath(skin):
    dirs = xbmcvfs.listdir(skin)[0]
    for dir in dirs:
        if dir.lower() in SKIN_XML_PARAMS:
            return os.path.join(skin,dir), dir.replace('xml','1080i')
               
def findFonts(self, path):
    fonts = xbmcvfs.listdir(path)
    for file in fonts:
        if file.endswith('ttf'):
            yield file
            
def notificationDialog(message, header=ADDON_NAME, show=True, sound=False, time=1000, icon=ICON):
    log('SkinPatch: notificationDialog: ' + message)
    if show == False:
        return
    try: 
        xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
    except Exception,e:
        log("SkinPatch: notificationDialog Failed! " + str(e), xbmc.LOGERROR)
        xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, THUMB))
            
class SkinPatch():
    def __init__(self):
        log('SkinPatch: KODI_SKIN_LOC = ' + KODI_SKIN_LOC)
        log('SkinPatch: PTVL_SKIN_LOC = ' + PTVL_SKIN_LOC)
        msg = ''
        xmlPath, skinRes = findXMLPath(KODI_SKIN_LOC)
        for dir in SKIN_DIA_PARAMS:
            path = os.path.join(xmlPath,dir)
            if xbmcvfs.exists(path) == True:
                log('SkinPatch: checking ' + path) 
                try:
                    found = False
                    lineLST = file(path, "r").readlines()
                    for line in lineLST:
                        patch = line.find('<visible>Window.IsActive(fullscreenvideo) + !Window.IsActive(script.pseudotv.TVOverlay.xml) + !Window.IsActive(script.pseudotv.live.TVOverlay.xml)</visible>')
                        if patch > 0:
                            found = True
                            log("SkinPatch: found existing patch")
                            msg = 'Skin Already Patched'
                    if found == False:
                        log('SkinPatch: applying patch') 
                        msg = 'Applied Skin Patched'
                        replaceAll(path,'<window>','<window>\n\t<visible>Window.IsActive(fullscreenvideo) + !Window.IsActive(script.pseudotv.TVOverlay.xml) + !Window.IsActive(script.pseudotv.live.TVOverlay.xml)</visible>')
                        xbmc.executebuiltin('XBMC.ReloadSkin()')
                except Exception,e:
                    log('SkinPatch: Failed! ' + str(e))
                    msg = 'Failed to Patch Skin'
        notificationDialog(msg, show=DEBUG)

class FontPatch():
    def __init__(self):
        log('FontPatch: KODI_SKIN_LOC = ' + KODI_SKIN_LOC)
        log('FontPatch: PTVL_SKIN_LOC = ' + PTVL_SKIN_LOC)
        xmlPath, skinRes = findXMLPath(PTVL_SKIN_LOC)
        path = os.path.join(xmlPath, 'script.pseudotv.live.fonts.xml')
        if xbmcvfs.exists(path) == True:
            log("FontPatch: found xml path = " + path)
            with open(path, 'rt') as f:
                tree = ET.parse(f)
            for node in tree.findall('font'):
                try:
                    if node.attrib.get('res') == skinRes:
                        self.addFont(skinRes, node.attrib.get('name'), node.attrib.get('filename'), node.attrib.get('size'))
                except Exception,e:
                    log('FontPatch: patchFont, failed! ' + str(e))
               
               
    def addFont(self, fntres, fntname, filename, size, style=""):
        log("FontPatch: addFont, fntname  = " + fntname  + ", fntres  = " + fntres)
        log("FontPatch: addFont, filename = " + filename + ", size = " + size)
        reload_skin = False
        fontPath = os.path.join(PTVL_FONT_LOC, filename)
        xmlPath, skinRes = findXMLPath(KODI_SKIN_LOC)
        xmlPath = os.path.join(xmlPath, 'Font.xml')
        fontDest= os.path.join(KODI_FONT_LOC, filename)
        log("FontPatch: addFont, fontPath = " + fontPath)
        log("FontPatch: addFont, xmlPath  = " + xmlPath)

        if self.isFontInstalled(fntres, fntname, filename, size, fontPath, fontDest) == False:
            tree = ET.parse(xmlPath, parser=PCParser())
            root = tree.getroot()
            for sets in root.getchildren():
                sets.findall("font")[-1].tail = "\n\t\t"
                new = ET.SubElement(sets, "font")
                new.text, new.tail = "\n\t\t\t", "\n\t"
                subnew1 = ET.SubElement(new, "name")
                subnew1.text = fntname
                subnew1.tail = "\n\t\t\t"
                subnew2 = ET.SubElement(new, "filename")
                subnew2.text = (filename, "Arial.ttf")[sets.attrib.get("id") == "Arial"]
                subnew2.tail = "\n\t\t\t"
                subnew3 = ET.SubElement(new, "size")
                subnew3.text = size
                subnew3.tail = "\n\t\t\t"
                last_elem = subnew3
                if style in ["normal", "bold", "italics", "bolditalics"]:
                    subnew4 = ET.SubElement(new, "style")
                    subnew4.text = style
                    subnew4.tail = "\n\t\t\t"
                    last_elem = subnew4
                reload_skin = True
                last_elem.tail = "\n\t\t"
            tree.write(xmlPath)
            reload_skin = True

            # copy font
            if xbmcvfs.exists(fontDest) == False:
                log("FontPatch: copying " + fontPath + " to " + fontDest)
                xbmcvfs.copy(fontPath, fontDest)
        
            # reload skin
            if reload_skin == True:
                xbmc.executebuiltin("XBMC.ReloadSkin()")
            notificationDialog('Fonts installed', show=DEBUG)

            
    def isFontInstalled(self, fntres, fntname, filename, size, fontPath, fontDest):
        found     = False
        xmlPath, skinRes = findXMLPath(KODI_SKIN_LOC)
        xmlPath   = os.path.join(xmlPath, 'Font.xml')
        fleLst    = file(xmlPath, "r").read().strip().replace('\t','').replace('\r','').replace('\n','').replace('</font>','')
        fleLst    = fleLst.split('<font>')
        lineMatch = '<name>%s</name><filename>%s</filename><size>%s</size>'%(fntname,filename,size)
        # check xml
        for line in fleLst:
            if line.startswith(lineMatch):
                found = True
                break
            else:
                # change font if matching name in use.
                fontMatch = re.compile('<name>%s</name><filename>(.*?)</filename><size>%s</size>'%(fntname,size)).findall(line)
                if len(fontMatch) > 0   and fontMatch[0] == 'Arial.ttf':
                    continue
                elif len(fontMatch) > 0 and fontMatch[0] != filename:
                    searchExp  = '\n\t\t\t<name>%s</name>\n\t\t\t<filename>%s</filename>\n\t\t\t<size>%s</size>'%(fntname,fontMatch[0],size)
                    replaceExp = '\n\t\t\t<name>%s</name>\n\t\t\t<filename>%s</filename>\n\t\t\t<size>%s</size>'%(fntname,filename,size)
                    replaceAll(xmlPath, searchExp, replaceExp)
                    found = True
                    break

        # check font
        if found == True:
            if xbmcvfs.exists(fontDest) == True:
                notificationDialog('Font already installed', show=DEBUG)
                return True
            else:
                xbmcvfs.copy(fontPath, fontDest)
                notificationDialog('Font installed', show=DEBUG)
                return True
        return False
 
 
class PCParser(ET.XMLTreeBuilder):
    def __init__(self):
        ET.XMLTreeBuilder.__init__(self)
        self._parser.CommentHandler = self.handle_comment
        
        
    def handle_comment(self, data):
        self._target.start(ET.Comment, {})
        self._target.data(data)
        self._target.end(ET.Comment)

if __name__ == '__main__':
    # print sys.argv
    # if len(sys.argv) > 1 and sys.argv[1] == '-auto':
    SkinPatch()
    FontPatch()
    # else:
        # select = xbmcgui.Dialog().select(ADDON_NAME, SELECT_PARAMS)
        # if select == 0:
            # SkinPatch()
        # elif select == 1:
            # FontPatch()
            
        ## todo remove fonts, restore default