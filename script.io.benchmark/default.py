#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of I/O Benchmark.
# The MIT License

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os, sys
from six.moves  import urllib 
from kodi_six   import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from monkeytest import Benchmark

# Plugin Info
ADDON_ID       = 'script.io.benchmark'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')

def log(msg, level = xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + str(msg), level)
    
def textviewer(msg, heading=ADDON_NAME, usemono=False):
    return xbmcgui.Dialog().textviewer(heading, msg, usemono)
    
if __name__ == '__main__':
    try:    params = dict(urllib.parse.parse_qsl(sys.argv[1]))
    except: params = {}
    TEST_PATH = (params.get('path') or SETTINGS_LOC)
    TEST_FILE = os.path.join((xbmcvfs.translatePath(TEST_PATH)),'test.tmp')
    log('params = %s, TEST_PATH = %s, TEST_FILE = %s'%(params,TEST_PATH,TEST_FILE))
    if not xbmcvfs.exists(os.path.join(TEST_PATH,'')): xbmcvfs.mkdirs(TEST_PATH)
    textviewer(Benchmark(TEST_FILE, 128, 1024, 512).print_result())