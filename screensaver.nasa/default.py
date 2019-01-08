#   Copyright (C) 2019 Lunatixz
#
#
# This file is part of NASA - Image of the Day ScreenSaver.
#
# NASA - Image of the Day ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NASA - Image of the Day ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NASA - Image of the Day ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import gui
import xbmcaddon

# Plugin Info
ADDON_ID       = 'screensaver.nasa'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))

if __name__ == '__main__':
    ui = gui.GUI("default.xml", ADDON_PATH, "default")
    ui.doModal()