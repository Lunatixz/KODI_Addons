#   Copyright (C) 2026 Lunatixz
#
#   PKBridge - Kodi-to-Plex bridge service
#   Handles playback — Plex client asks, Kodi plays
#
# This file is part of PKBridge.
# -*- coding: utf-8 -*-

import os, time, threading
import xbmc, xbmcgui, xbmcplugin
from constants import LOG, MONITOR, PLAYER, PLEX_MACHINE_ID


class PKPlayer(xbmc.Player):
    """Listens for Plex playback requests and drives Kodi's player."""

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._current = {}    # what's playing right now
        self._pending = {}    # file path -> metadata, waiting to play

    # ------------------------------------------------------------------
    # Kodi Player callbacks
    # ------------------------------------------------------------------

    def onPlayBackStarted(self):
        LOG('onPlayBackStarted')
        self._resolve_pending()

    def onAVStarted(self):
        LOG('onAVStarted')
        self._update_playing()

    def onPlayBackEnded(self):
        LOG('onPlayBackEnded')
        with self._lock:
            self._current = {}

    def onPlayBackStopped(self):
        LOG('onPlayBackStopped')
        with self._lock:
            self._current = {}

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    def play_item(self, file_path: str, meta: dict = None) -> bool:
        """Play a file through Kodi's player.

        Args:
            file_path: Absolute path to the media file.
            meta: Optional dict with title, year, art, etc. for the OSD.

        Returns:
            True if playback was initiated.
        """
        if not file_path or not os.path.exists(file_path):
            LOG('play_item: file not found: %s' % file_path, 3)
            return False

        with self._lock:
            self._pending = {'file': file_path, 'meta': meta or {}}

        # Build a ListItem with metadata for the OSD
        li = xbmcgui.ListItem(path=file_path)
        if meta:
            info = {
                'title': meta.get('title', ''),
                'year': meta.get('year', 0),
                'genre': ', '.join(meta.get('genres', [])),
                'plot': meta.get('summary', ''),
                'rating': meta.get('rating', 0),
                'mpaa': meta.get('contentRating', ''),
                'duration': meta.get('durationInSeconds', 0),
                'mediatype': meta.get('type', 'video'),
            }
            li.setInfo('video', info)
            # Art
            art = {}
            if meta.get('thumb'):
                art['poster'] = meta['thumb']
            if meta.get('art'):
                art['fanart'] = meta['art']
            if art:
                li.setArt(art)

        LOG('play_item: %s' % file_path)
        super().play(file_path, li)
        return True

    def play_plex_stream(self, file_path: str, start_offset_ms: int = 0,
                         meta: dict = None) -> bool:
        """Play a file, optionally seeking to a resume position.

        Args:
            file_path: Absolute path to the media file.
            start_offset_ms: Resume position in milliseconds.
            meta: Optional metadata dict.

        Returns:
            True if playback was initiated.
        """
        if not file_path or not os.path.exists(file_path):
            LOG('play_plex_stream: file not found: %s' % file_path, 3)
            return False

        with self._lock:
            self._pending = {'file': file_path, 'meta': meta or {}, 'offset': start_offset_ms}

        li = xbmcgui.ListItem(path=file_path)
        if meta:
            info = {
                'title': meta.get('title', ''),
                'year': meta.get('year', 0),
                'genre': ', '.join(meta.get('genres', [])),
                'plot': meta.get('summary', ''),
                'rating': meta.get('rating', 0),
                'duration': meta.get('durationInSeconds', 0),
                'mediatype': meta.get('type', 'video'),
            }
            li.setInfo('video', info)
            art = {}
            if meta.get('thumb'):
                art['poster'] = meta['thumb']
            if meta.get('art'):
                art['fanart'] = meta['art']
            if art:
                li.setArt(art)

        LOG('play_plex_stream: %s (offset=%dms)' % (file_path, start_offset_ms))
        super().play(file_path, li)

        # If resuming, seek after playback starts
        if start_offset_ms > 0:
            self._seek_after_start(start_offset_ms)

        return True

    def _seek_after_start(self, offset_ms: int, retries: int = 20):
        """Wait for playback to begin then seek to offset."""
        def _do_seek():
            for _ in range(retries):
                if MONITOR().abortRequested():
                    return
                if self.isPlaying():
                    time.sleep(0.2)
                    try:
                        self.seekTime(offset_ms / 1000.0)
                        LOG('Resumed at %dms' % offset_ms)
                    except Exception as e:
                        LOG('Seek failed: %s' % e, 2)
                    return
                time.sleep(0.1)
        t = threading.Thread(target=_do_seek, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_pending(self):
        """After onPlayBackStarted, if we have pending offset, seek."""
        with self._lock:
            pending = self._pending
            self._pending = {}
        offset = pending.get('offset', 0)
        if offset > 0:
            self._seek_after_start(offset)

    def _update_playing(self):
        """Track what's currently playing."""
        with self._lock:
            if self._pending:
                self._current = self._pending
                self._pending = {}

    # ------------------------------------------------------------------
    # Session state (for /status/sessions)
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        """Return current playback state in Plex session format."""
        if not self.isPlaying():
            return {}

        try:
            item = {}
            # Try to get info from current playing item
            current_file = self.getPlayingFile() if hasattr(self, 'getPlayingFile') else ''
            total_time = self.getTotalTime() or 0
            current_time = self.getTime() or 0

            with self._lock:
                meta = self._current.get('meta', {})

            return {
                'title': meta.get('title', os.path.basename(current_file)),
                'type': meta.get('type', 'video'),
                'duration': int(total_time * 1000),
                'viewOffset': int(current_time * 1000),
                'state': 'playing' if not self.paused else 'paused',
                'file': current_file,
                'Player': {
                    'state': 'playing' if not self.paused else 'paused',
                    'time': int(current_time * 1000),
                    'duration': int(total_time * 1000),
                    'progress': int((current_time / total_time * 100) if total_time else 0),
                    'machineIdentifier': PLEX_MACHINE_ID,
                },
            }
        except Exception:
            return {}
