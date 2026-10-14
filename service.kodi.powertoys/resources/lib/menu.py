#   Copyright (C) 2026 Lunatixz
#
# This file is part of Kodi PowerToys
# Kodi PowerToys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# -*- coding: utf-8 -*-
import sys, json, xbmc, xbmcaddon, xbmcgui

ADDON    = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
LANG     = ADDON.getLocalizedString

def notify(message, data=None):
    cmd = {"jsonrpc": "2.0", "method": "JSONRPC.NotifyAll",
           "params": {"sender": ADDON_ID, "message": message, "data": data or {}},
           "id": ADDON_ID}
    xbmc.executeJSONRPC(json.dumps(cmd))

def main():
    items = [
        (LANG(32051), 'RunScraper'),   # Run scraper now
        (LANG(32052), 'RunRefresh'),   # Run refresh now
        (LANG(32053), 'RunClean'),     # Run clean now
        (LANG(32054), 'RunTexture'),   # Run texture maintenance now
        (LANG(32055), 'RunBackup'),    # Run backup now
        (LANG(32035), 'HealthReport'), # Library health report
    ]
    idx = xbmcgui.Dialog().select(ADDON.getAddonInfo('name'), [i[0] for i in items])
    if idx < 0: return
    notify(items[idx][1])

if __name__ == '__main__': main()
