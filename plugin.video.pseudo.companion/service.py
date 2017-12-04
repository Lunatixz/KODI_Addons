#   Copyright (C) 2016 Kevin S. Graer
#
#
# This file is part of PseudoCompanion.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from utils import *

monitor = xbmc.Monitor()
while not monitor.abortRequested():
    # Sleep/wait for abort for 1 seconds
    if monitor.waitForAbort(1):
        # Abort was requested while waiting. We should exit
        break
    if getProperty('PseudoTVRunning') == "True":
        STATE = 'true'
        STATUS = '[COLOR=green]ONLINE[/COLOR]'
    else:
        STATE = 'false'
        STATUS = '[COLOR=red]OFFLINE[/COLOR]'
    setProperty('PseudoCompanion.STATE', STATE)
    setProperty('PseudoCompanion.STATUS', STATUS)