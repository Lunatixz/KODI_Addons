#   Copyright (C) 2016 Lunatixz
#
#
# This file is part of PseudoCinema Poster.
#
# PseudoCinema Poster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoCinema Poster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoCinema Poster.  If not, see <http://www.gnu.org/licenses/>.

import os, xbmc, xbmcgui, xbmcaddon, xbmcvfs

# Plugin Info
ADDON_ID = 'script.pseudocinema.poster'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
THUMB = os.path.join(ADDON_PATH, 'icon.png').decode('utf-8')
AUTOSTART_TIMER = [0,5,10,15,20,25,30][int(REAL_SETTINGS.getSetting('autostart_delay'))]

if AUTOSTART_TIMER != 0:
    xbmc.log('script.pseudotv.live-Service: autostart')
    xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (ADDON_NAME, "AutoStart Enabled", (1000)/2, THUMB))
    xbmc.sleep(AUTOSTART_TIMER*1000)
    xbmc.executebuiltin('RunScript("' + ADDON_PATH + '/default.py' + '")')
