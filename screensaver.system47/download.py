#   Copyright (C) 2023 Lunatixz
#
#
# This file is part of System 47 Live in HD Screensaver.
#
# System 47 Live in HD Screensaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# System 47 Live in HD Screensaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with System 47 Live in HD Screensaver.  If not, see <http://www.gnu.org/licenses/>.

import os, time, traceback, requests, re, sys
import shutil, tempfile, six

from kodi_six  import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from six.moves import urllib
from bs4       import BeautifulSoup
    
# Plugin Info
ADDON_ID      = 'screensaver.system47'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
DEBUG         = True
FILENAME      = 'screensaver.system47.v.2.5.01.mp4'
FILEPATH      = os.path.join(SETTINGS_LOC,FILENAME)
# DOWNLOAD_URL  = 'http://www.mediafire.com/file/cvptnk5p5zk41zb/screensaver.system47.mp4/file'
DOWNLOAD_URL  = 'https://www.mediafire.com/file/xjkqyiy9for97fl/screensaver.system47.v.2.5.01.mp4/file'
CHUNK_SIZE    = 512 * 1024  # 512KB

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg), level)

class Download(object):
    def __init__(self):
        self.start(DOWNLOAD_URL,FILEPATH)
        
 
    def start(self, url, output, quiet=False):
        url_origin = url
        sess = requests.session()
        sess.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.178 Safari/537.36"
        }
            
        while not xbmc.Monitor().abortRequested():
            res = sess.get(url, stream=True)
            if 'Content-Disposition' in res.headers:
                break
                
            for line in res.text.splitlines():
                m = re.search(r'href="((http|https)://download[^"]+)', line)
                if m:
                    url = m.groups()[0]
                    break
                    
            if url is None:
                return log('start, Permission denied: %s'%url_origin)
                
        if output is None:
            m = re.search(
                'filename="(.*)"', res.headers['Content-Disposition']
            )
            output = m.groups()[0]
            output = os.path.join(SETTINGS_LOC,output.encode('iso8859').decode('utf-8'))
        output_is_path = isinstance(output, six.string_types)

        if not quiet:
            msg = '%s\n%s\n%s'%(LANGUAGE(30002),FILENAME,FILEPATH)

        if output_is_path:
            tmp_file = tempfile.mktemp(
                suffix=tempfile.template,
                prefix=os.path.basename(output),
                dir=os.path.dirname(output),
            )
            f = xbmcvfs.File(tmp_file, 'wb')
        else:
            tmp_file = None
            f = output

        try:
            total = res.headers.get('Content-Length')
            if total is not None:
                total = int(total)
            if not quiet:
                dia = xbmcgui.DialogProgress()
                dia.create(ADDON_NAME,msg)
                dia.update(0, msg)
                
            for idx, chunk in enumerate(res.iter_content(chunk_size=CHUNK_SIZE)):
                f.write(chunk)
                if not quiet:
                    if dia.iscanceled():
                        raise Exception('Download Canceled')
                    per = int((idx-1)*100//(total//CHUNK_SIZE))
                    msg = '%s (%s%%)\n%s\n%s'%(LANGUAGE(30002),per,FILENAME,FILEPATH)
                    dia.update(per,msg)
                    
            if not quiet:
                dia.close()
                
            if tmp_file:
                f.close()
                msg = '%s\n%s\n%s'%(LANGUAGE(30002),tmp_file,output)
                dia.update(per,msg)
                if not xbmcvfs.copy(tmp_file, output):
                    raise Exception('Copy Failed! %s => %s'%(tmp_file, output))
        except Exception as e:
            log("start, failed! %s"%(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return self.deletefiles(tmp_file)
        finally: self.deletefiles(tmp_file)
        if not quiet: dia.update(100,msg)
        return output

        
    def deletefiles(self, tmp_file):
        #todo clean up all files ending with tmp
        try:
            if tmp_file:
                xbmcvfs.delete(tmp_file)
        except OSError:
            pass
            
if __name__ == '__main__':
    Download()