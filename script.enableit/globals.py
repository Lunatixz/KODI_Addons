#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of Enable it!.
#
# Enable it! is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Enable it! is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Enable it!.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import re, os, sys, json
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

# Plugin Info
ADDON_ID      = 'script.enableit'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = os.path.join(ADDON_PATH, 'icon.png')
FANART        = os.path.join(ADDON_PATH, 'fanart.jpg')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
ENABLE        = REAL_SETTINGS.getSetting('Enable') == "0"

CONTENTS = ["unknown",
            "video",
            "audio",
            "image",
            "executable"]
            
TYPES    = ["unknown",
            "xbmc.player.musicviz",
            "xbmc.gui.skin",
            "xbmc.pvrclient",
            "kodi.adsp",
            "kodi.inputstream",
            "kodi.peripheral",
            "xbmc.python.script",
            "xbmc.python.weather",
            "xbmc.subtitle.module",
            "xbmc.python.lyrics",
            "xbmc.metadata.scraper.albums",
            "xbmc.metadata.scraper.artists",
            "xbmc.metadata.scraper.movies",
            "xbmc.metadata.scraper.musicvideos",
            "xbmc.metadata.scraper.tvshows",
            "xbmc.ui.screensaver",
            "xbmc.python.pluginsource",
            "xbmc.addon.repository",
            "xbmc.webinterface",
            "xbmc.service",
            "xbmc.audioencoder",
            "kodi.context.item",
            "kodi.audiodecoder",
            "kodi.resource.images",
            "kodi.resource.language",
            "kodi.resource.uisounds",
            "xbmc.addon.video",
            "xbmc.addon.audio",
            "xbmc.addon.image",
            "xbmc.addon.executable",
            "xbmc.metadata.scraper.library",
            "xbmc.python.library",
            "xbmc.python.module",
            "kodi.game.controller"]

CONTENT_TYPES = ["xbmc.python.script",
                 "xbmc.addon.repository",
                 "xbmc.addon.video",
                 "xbmc.addon.audio",
                 "xbmc.addon.image",
                 "xbmc.addon.executable",
                 "xbmc.python.library",
                 "xbmc.python.module"]
