#   Copyright (C) 2026 Lunatixz
#
#   PKBridge - Kodi-to-Plex bridge service
#   Emulates a Plex Media Server using Kodi library data
#
# This file is part of PKBridge.
#
# PKBridge is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PKBridge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PKBridge.  If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-

import os, sys, json, time, uuid, hashlib, socket, threading
import datetime, traceback

from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs

# =============================================================================
# Addon Identity
# =============================================================================
ADDON_ID      = 'service.pkbridge'
ADDON         = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH    = ADDON.getAddonInfo('path')
LANGUAGE      = ADDON.getLocalizedString

# =============================================================================
# Kodi API References
# =============================================================================
MONITOR_INSTANCE = None

def MONITOR():
    global MONITOR_INSTANCE
    if MONITOR_INSTANCE is None:
        MONITOR_INSTANCE = xbmc.Monitor()
    return MONITOR_INSTANCE

PLAYER_INSTANCE = None

def PLAYER():
    global PLAYER_INSTANCE
    if PLAYER_INSTANCE is None:
        PLAYER_INSTANCE = xbmc.Player()
    return PLAYER_INSTANCE

# =============================================================================
# Network / Server Defaults
# =============================================================================
PLEX_DEFAULT_PORT = 32400  # Standard Plex port, matches real PMS
PLEX_SERVER_NAME  = 'PKBridge Kodi Server'
PLEX_MACHINE_ID   = hashlib.md5(('%s.%s' % (ADDON_ID, socket.gethostname())).encode()).hexdigest()
DNS_REDIRECT_IP   = ADDON.getSetting('DNS_Redirect_IP') or None

# GDM (Good Day Mate) discovery - Plex's UDP multicast protocol
GDM_MULTICAST_ADDR = '239.0.0.250'
GDM_PORT           = 32414  # Primary GDM port

# =============================================================================
# Kodi JSON-RPC Transport
# =============================================================================
KODI_JSONRPC_IP   = '127.0.0.1'
KODI_JSONRPC_PORT = 9090     # Kodi's built-in JSON-RPC TCP port
JSONRPC_TIMEOUT   = 10       # seconds

# =============================================================================
# Thread Pool
# =============================================================================
THREAD_WORKERS = 4

# =============================================================================
# File / Cache
# =============================================================================
CACHE_DIR     = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)

LIBRARY_CACHE_FILE = os.path.join(CACHE_DIR, 'library_cache.json')
CACHE_TTL = 300  # 5 minutes

# =============================================================================
# Plex Metadata Object Defaults
# =============================================================================
PLEX_CONTAINER_SIZE = 50  # Default pagination size for /library/sections/{id}/all

# =============================================================================
# Plex-style ratingKey generation
# =============================================================================
def generate_ratingKey(kodi_id: int, media_type: str) -> str:
    """Generate a stable numeric ratingKey from Kodi's unique identifiers."""
    raw = '%s.%s.%s' % (ADDON_ID, media_type, kodi_id)
    return str(abs(int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)))

# =============================================================================
# Simple logger
# =============================================================================
LOG_LEVEL = xbmc.LOGDEBUG

def LOG(msg, level=xbmc.LOGDEBUG):
    xbmc.log('%s [%s]: %s' % (ADDON_NAME, ADDON_VERSION, msg), level if level >= LOG_LEVEL else LOG_LEVEL)
