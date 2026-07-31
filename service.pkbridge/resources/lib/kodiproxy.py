#   Copyright (C) 2026 Lunatixz
#
#   PKBridge - Kodi-to-Plex bridge service
#   Kodi JSON-RPC data access layer
#
# This file is part of PKBridge.
# -*- coding: utf-8 -*-

import socket, json, time
from constants import (ADDON_ID, KODI_JSONRPC_IP, KODI_JSONRPC_PORT,
                       JSONRPC_TIMEOUT, CACHE_DIR, LIBRARY_CACHE_FILE,
                       CACHE_TTL, LOG, MONITOR)


class KodiProxy:
    """Reads Kodi library data via JSON-RPC (TCP socket to Kodi webserver)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cache = {}
        self._cache_times = {}

    def _send(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC command over TCP to Kodi."""
        cmd = {
            'jsonrpc': '2.0',
            'id': '%s.proxy' % ADDON_ID,
            'method': method,
        }
        if params:
            cmd['params'] = params

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(JSONRPC_TIMEOUT)
            sock.connect((KODI_JSONRPC_IP, KODI_JSONRPC_PORT))
            sock.sendall(json.dumps(cmd).encode('utf-8'))
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            data = json.loads(response.decode('utf-8'))
            if 'error' in data:
                LOG('JSONRPC error: %s' % data['error'], 3)
            return data.get('result', {})
        except Exception as e:
            LOG('JSONRPC send failed (%s): %s' % (method, e), 3)
            return {}

    def _get_cached(self, key: str, fetcher, ttl: int = CACHE_TTL):
        """Cache wrapper - returns fresh data or re-fetches if expired."""
        now = time.time()
        if key in self._cache and (now - self._cache_times.get(key, 0)) < ttl:
            return self._cache[key]
        data = fetcher()
        if data:
            self._cache[key] = data
            self._cache_times[key] = now
        return data

    def invalidate(self):
        self._cache.clear()
        self._cache_times.clear()

    # =========================================================================
    # Library Queries
    # =========================================================================

    def get_movies(self) -> list:
        """Return all movies from Kodi library."""
        def fetch():
            result = self._send('VideoLibrary.GetMovies', {
                'properties': [
                    'title', 'originaltitle', 'year', 'plot', 'plotoutline',
                    'tagline', 'rating', 'votes', 'mpaa', 'duration', 'runtime',
                    'genre', 'studio', 'director', 'writer', 'cast',
                    'set', 'setid', 'tag', 'thumb', 'fanart', 'trailer',
                    'dateadded', 'lastplayed', 'playcount', 'resume',
                    'art', 'uniqueid', 'premiered', 'originaltitle',
                ],
                'sort': {'method': 'title', 'order': 'ascending'},
            })
            return result.get('movies', [])
        return self._get_cached('movies', fetch)

    def get_tvshows(self) -> list:
        """Return all TV shows from Kodi library."""
        def fetch():
            result = self._send('VideoLibrary.GetTVShows', {
                'properties': [
                    'title', 'originaltitle', 'year', 'plot', 'rating',
                    'votes', 'mpaa', 'genre', 'studio', 'tag',
                    'thumb', 'fanart', 'dateadded', 'lastplayed',
                    'playcount', 'art', 'uniqueid', 'status',
                    'episode', 'watchedepisodes', 'season', 'premiered',
                ],
                'sort': {'method': 'title', 'order': 'ascending'},
            })
            return result.get('tvshows', [])
        return self._get_cached('tvshows', fetch)

    def get_episodes(self, tvshowid: int = None) -> list:
        """Return episodes, optionally filtered by tvshowid."""
        def fetch():
            params = {
                'properties': [
                    'title', 'plot', 'rating', 'votes', 'season',
                    'episode', 'playcount', 'firstaired', 'duration',
                    'runtime', 'director', 'writer', 'art', 'resume',
                    'dateadded', 'lastplayed', 'thumb', 'fanart',
                ],
                'sort': {'method': 'episode', 'order': 'ascending'},
            }
            if tvshowid is not None:
                params['tvshowid'] = tvshowid
            result = self._send('VideoLibrary.GetEpisodes', params)
            return result.get('episodes', [])
        cache_key = 'episodes.%s' % (tvshowid or 'all')
        return self._get_cached(cache_key, fetch)

    def get_movie_details(self, movieid: int) -> dict:
        """Return full details for a single movie."""
        result = self._send('VideoLibrary.GetMovieDetails', {
            'movieid': movieid,
            'properties': [
                'title', 'originaltitle', 'year', 'plot', 'plotoutline',
                'tagline', 'rating', 'votes', 'mpaa', 'duration', 'runtime',
                'genre', 'studio', 'director', 'writer', 'cast',
                'set', 'setid', 'tag', 'thumb', 'fanart', 'trailer',
                'dateadded', 'lastplayed', 'playcount', 'resume',
                'art', 'uniqueid', 'premiered',
            ],
        })
        return result.get('moviedetails', {})

    def get_tvshow_details(self, tvshowid: int) -> dict:
        """Return full details for a single TV show."""
        result = self._send('VideoLibrary.GetTVShowDetails', {
            'tvshowid': tvshowid,
            'properties': [
                'title', 'originaltitle', 'year', 'plot', 'rating',
                'votes', 'mpaa', 'genre', 'studio', 'tag',
                'thumb', 'fanart', 'dateadded', 'lastplayed',
                'playcount', 'art', 'uniqueid', 'status',
                'episode', 'watchedepisodes', 'season', 'premiered',
            ],
        })
        return result.get('tvshowdetails', {})

    def get_episode_details(self, episodeid: int) -> dict:
        """Return full details for a single episode."""
        result = self._send('VideoLibrary.GetEpisodeDetails', {
            'episodeid': episodeid,
            'properties': [
                'title', 'plot', 'rating', 'votes', 'season',
                'episode', 'playcount', 'firstaired', 'duration',
                'runtime', 'director', 'writer', 'art', 'resume',
                'dateadded', 'lastplayed', 'thumb', 'fanart',
                'tvshowid',
            ],
        })
        return result.get('episodedetails', {})

    def get_genres(self, media_type: str = 'video') -> list:
        """Return genre list for movies or tvshows."""
        method = 'VideoLibrary.GetGenres'
        params = {'type': media_type}
        result = self._send(method, params)
        return result.get('genres', [])

    def get_recently_added_movies(self, limit: int = 20) -> list:
        """Return recently added movies."""
        def fetch():
            result = self._send('VideoLibrary.GetRecentlyAddedMovies', {
                'properties': [
                    'title', 'originaltitle', 'year', 'plot', 'rating',
                    'genre', 'studio', 'thumb', 'fanart', 'playcount',
                    'dateadded', 'art', 'uniqueid', 'duration',
                ],
                'limits': {'start': 0, 'end': limit},
                'sort': {'method': 'dateadded', 'order': 'descending'},
            })
            return result.get('movies', [])
        return self._get_cached('recent_movies', fetch)

    def get_recently_added_episodes(self, limit: int = 20) -> list:
        """Return recently added episodes."""
        def fetch():
            result = self._send('VideoLibrary.GetRecentlyAddedEpisodes', {
                'properties': [
                    'title', 'plot', 'rating', 'season', 'episode',
                    'playcount', 'firstaired', 'art', 'thumb', 'fanart',
                    'dateadded', 'tvshowid', 'duration',
                ],
                'limits': {'start': 0, 'end': limit},
                'sort': {'method': 'dateadded', 'order': 'descending'},
            })
            return result.get('episodes', [])
        return self._get_cached('recent_episodes', fetch)

    def search(self, query: str) -> dict:
        """Search across movies and TV shows."""
        movies = self._send('VideoLibrary.GetMovies', {
            'filter': {'field': 'title', 'operator': 'contains', 'value': query},
            'properties': ['title', 'year', 'uniqueid'],
            'limits': {'start': 0, 'end': 20},
        })
        shows = self._send('VideoLibrary.GetTVShows', {
            'filter': {'field': 'title', 'operator': 'contains', 'value': query},
            'properties': ['title', 'year', 'uniqueid'],
            'limits': {'start': 0, 'end': 20},
        })
        return {
            'movies': movies.get('movies', []),
            'tvshows': shows.get('tvshows', []),
        }

    def get_stream_details(self, file_path: str) -> dict:
        """Get stream details (codec, resolution, etc.) for a file."""
        result = self._send('Files.GetFileDetails', {
            'file': file_path,
            'media': 'video',
            'properties': ['stream', 'size', 'date'],
        })
        return result.get('filedetails', {})

    def get_active_players(self) -> list:
        """Return currently active player(s)."""
        result = self._send('Player.GetActivePlayers')
        return result.get('players', [])

    def get_player_item(self, playerid: int) -> dict:
        """Return the currently playing item for a given player."""
        result = self._send('Player.GetItem', {
            'playerid': playerid,
            'properties': [
                'title', 'year', 'duration', 'genre', 'rating',
                'plot', 'thumb', 'art', 'uniqueid', 'playcount',
            ],
        })
        return result.get('item', {})


import threading
