#   Copyright (C) 2026 Lunatixz
#
#   PKBridge - Kodi-to-Plex bridge service
#   Main entry point — started by Kodi on boot
#
# This file is part of PKBridge.
# -*- coding: utf-8 -*-

import sys, time, os
from constants import (ADDON_ID, ADDON_NAME, ADDON_VERSION, PLEX_DEFAULT_PORT,
                       LOG, MONITOR, CACHE_DIR, ADDON)

MON = MONITOR()

# README URL for QR code - update this to your repo URL
README_URL = 'https://github.com/plugin.video.pseudotv.live/tree/master/service.pkbridge'


def _generate_qr_code(url, save_path):
    """Generate QR code image using pyqrcode."""
    try:
        import pyqrcode
        qr = pyqrcode.create(url, error='M')
        qr.png(save_path, scale=6)
        return True
    except Exception as e:
        LOG('QR generation failed: %s' % e, 2)
        return False


def _show_first_run_dialog():
    """Show first-time setup dialog with QR code."""
    try:
        import xbmcgui
        
        # Check if we already showed the dialog
        first_run_file = os.path.join(CACHE_DIR, 'first_run_done')
        if os.path.exists(first_run_file):
            return
        
        # Generate QR code
        qr_path = os.path.join(CACHE_DIR, 'setup_qr.png')
        qr_generated = _generate_qr_code(README_URL, qr_path)
        
        # Build message
        msg = (
            '[B]PKBridge Setup Guide[/B]\n\n'
            'PKBridge emulates a Plex Media Server using your Kodi library.\n\n'
            '[B]Quick Start:[/B]\n'
            '1. In your Plex app, add server: [COLOR yellow]<your-kodi-ip>:32400[/COLOR]\n'
            '2. Use any token (or leave blank)\n\n'
            '[B]For Dispatch/plex.tv apps:[/B]\n'
            '• Configure DNS redirect to your PKBridge IP\n'
            '• See README for detailed instructions\n\n'
            '[B]Settings:[/B]\n'
            '• Set "DNS Redirect IP" in addon settings\n\n'
            '[B]DNS Setup by Platform:[/B]\n'
            '• [COLOR yellow]Android TV:[/COLOR] Install "Personal DNS Filter" from Play Store\n'
            '• [COLOR yellow]Windows:[/COLOR] Add "192.168.1.100 plex.tv" to hosts file\n'
            '• [COLOR yellow]macOS:[/COLOR] Add to /etc/hosts: "192.168.1.100 plex.tv"\n'
            '• [COLOR yellow]Linux:[/COLOR] Add to /etc/hosts: "192.168.1.100 plex.tv"\n\n'
            '[B]Same Device?[/B]\n'
            'Use 127.0.0.1 instead of LAN IP\n\n'
            '[I]Scan QR code for full documentation[/I]'
        )
        
        # Show text viewer dialog (scrollable, shows more text)
        dialog = xbmcgui.Dialog()
        dialog.textviewer('PKBridge Setup', msg)
        
        # Mark first run as done
        with open(first_run_file, 'w') as f:
            f.write('done')
            
    except Exception as e:
        LOG('First run dialog error: %s' % e, 2)


def _start():
    LOG('%s v%s starting' % (ADDON_NAME, ADDON_VERSION))

    # Show first-run dialog
    _show_first_run_dialog()

    from kodiproxy  import KodiProxy
    from plex       import PlexTranslator
    from player     import PKPlayer
    from server     import PKBridgeServer
    from gdm        import GDMListener

    kodiproxy  = KodiProxy()
    pkplayer   = PKPlayer()

    # Server binds and resolves its own port
    server = PKBridgeServer(kodiproxy, PlexTranslator(kodiproxy, '0.0.0.0:%d' % PLEX_DEFAULT_PORT), pkplayer)
    server.start()

    # Now that the server knows its real host:port, update the translator
    translator = PlexTranslator(kodiproxy, server.get_host())
    server.translator = translator

    # GDM discovery
    gdm = GDMListener(port=server.port)
    gdm.start()

    LOG('%s running on %s' % (ADDON_NAME, server.get_host()))

    # Main idle loop
    while not MON.abortRequested():
        if MON.waitForAbort(5):
            break

    # Shutdown
    LOG('%s shutting down' % ADDON_NAME)
    gdm.stop()
    server.stop()
    kodiproxy.invalidate()
    LOG('%s stopped' % ADDON_NAME)


if __name__ == '__main__' or True:
    try:
        _start()
    except Exception as e:
        LOG('Fatal: %s' % e, 4)
        import traceback
        traceback.print_exc()
