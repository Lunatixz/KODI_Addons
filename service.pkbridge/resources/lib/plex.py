#   Copyright (C) 2026 Lunatixz
#
#   PKBridge - Kodi-to-Plex bridge service
#   Translates Kodi library data into Plex API response format
#
# This file is part of PKBridge.
# -*- coding: utf-8 -*-

import time, hashlib, os
from constants import (ADDON_ID, ADDON_NAME, ADDON_VERSION, PLEX_MACHINE_ID,
                       PLEX_SERVER_NAME, DNS_REDIRECT_IP, generate_ratingKey,
                       LOG, MONITOR, PLAYER)
from kodiproxy import KodiProxy

MOVIE_SECTION_ID = 1
SHOW_SECTION_ID  = 2
SECTION_UUID_MOVIES = hashlib.md5(('movies.%s' % PLEX_MACHINE_ID).encode()).hexdigest()
SECTION_UUID_SHOWS  = hashlib.md5(('tvshows.%s' % PLEX_MACHINE_ID).encode()).hexdigest()

PLEX_CONTAINER_SIZE = 50


class PlexTranslator:
    """Kodi library data -> Plex API responses."""

    def __init__(self, kodiproxy: KodiProxy, host: str):
        self.kodiproxy = kodiproxy
        self.host = host

    def _base(self):
        return 'http://%s' % self.host

    # ------------------------------------------------------------------
    # Artwork URL proxy
    # ------------------------------------------------------------------

    def _thumb(self, kodi_path: str) -> str:
        if not kodi_path:
            return ''
        if kodi_path.startswith('image://'):
            kodi_path = kodi_path[8:]
        return '%s/image/%s' % (self._base(), kodi_path.rstrip('/'))

    def _art(self, art: dict, key: str = 'poster') -> str:
        url = art.get(key, '')
        if not url:
            alts = {'poster': ['thumb', 'thumb1'], 'fanart': ['fanart1', 'banner']}
            for a in alts.get(key, []):
                url = art.get(a, '')
                if url:
                    break
        return self._thumb(url) if url else ''

    # ------------------------------------------------------------------
    # File / part resolution (for streaming)
    # ------------------------------------------------------------------

    def resolve_file(self, rating_key_or_part_id: str) -> str:
        """Map a Plex ratingKey back to the actual Kodi file path."""
        for m in self.kodiproxy.get_movies():
            if generate_ratingKey(m.get('movieid', 0), 'movie') == rating_key_or_part_id:
                return m.get('file', '')
        for e in self.kodiproxy.get_episodes():
            if generate_ratingKey(e.get('episodeid', 0), 'episode') == rating_key_or_part_id:
                return e.get('file', '')
        return ''

    def resolve_thumb(self, rating_key: str) -> str:
        """Resolve a ratingKey to a local thumbnail file path."""
        for m in self.kodiproxy.get_movies():
            if generate_ratingKey(m.get('movieid', 0), 'movie') == rating_key:
                art = m.get('art', {})
                url = art.get('poster', art.get('thumb', ''))
                if url and url.startswith('image://'):
                    return url[8:].rstrip('/')
        for s in self.kodiproxy.get_tvshows():
            if generate_ratingKey(s.get('tvshowid', 0), 'show') == rating_key:
                art = s.get('art', {})
                url = art.get('poster', art.get('thumb', ''))
                if url and url.startswith('image://'):
                    return url[8:].rstrip('/')
        return ''

    # =================================================================
    #  SERVER  /  (identity)
    # =================================================================

    def server_info(self) -> dict:
        return {'MediaContainer': {
            'size': 0,
            'allowCameraUpload': False,
            'allowChannelAccess': False,
            'allowMediaDeletion': False,
            'allowSharing': False,
            'allowSync': False,
            'allowTuners': False,
            'backgroundProcessing': False,
            'certificate': False,
            'companionProxy': False,
            'countryCode': 'US',
            'diagnostics': 'none',
            'eventStream': True,
            'friendlyName': PLEX_SERVER_NAME,
            'hubSearch': True,
            'itemClusters': True,
            'livetv': 0,
            'machineIdentifier': PLEX_MACHINE_ID,
            'mediaProviders': True,
            'multiuser': False,
            'myPlex': False,
            'myPlexMappingState': '',
            'myPlexSigninState': '',
            'myPlexSubscription': False,
            'myPlexUsername': '',
            'offlineTranscode': 0,
            'ownerFeatures': [],
            'platform': 'Kodi',
            'platformVersion': ADDON_VERSION,
            'pluginHost': False,
            'pushNotifications': False,
            'readOnlyLibraries': False,
            'streamingBrainABRVersion': 1,
            'streamingBrainVersion': 1,
            'sync': False,
            'transcoderActiveVideoSessions': 0,
            'transcoderAudio': True,
            'transcoderLyrics': False,
            'transcoderPhoto': False,
            'transcoderSubtitles': False,
            'transcoderVideo': True,
            'transcoderVideoBitrates': '64,96,208,320,720,1500,2000,3000,4000,8000,10000',
            'transcoderVideoQualities': '0,1,2,3,4,5,6,7,8',
            'transcoderVideoResolutions': '120,240,360,480,720,1080',
            'updatedAt': int(time.time()),
            'updater': '0',
            'version': '%s (%s)' % (ADDON_VERSION, PLEX_MACHINE_ID[:8]),
            'voiceSearch': False,
            'localAddresses': DNS_REDIRECT_IP or '127.0.0.1',
            'remoteAddresses': DNS_REDIRECT_IP or '127.0.0.1',
            'Directory': [
                {'key': 'library', 'title': 'library', 'type': 'video'},
            ],
        }}

    # =================================================================
    #  PREFS  /:/prefs
    # =================================================================

    def server_prefs(self) -> dict:
        return {'MediaContainer': {
            'size': 1,
            'Setting': [
                {'id': 'FriendlyName', 'label': 'Friendly Name', 'summary': 'Server name',
                 'type': 'text', 'default': PLEX_SERVER_NAME, 'value': PLEX_SERVER_NAME},
                {'id': 'ManualPort', 'label': 'Port', 'summary': 'Server port',
                 'type': 'int', 'default': '32400', 'value': '32400'},
            ],
        }}

    # =================================================================
    #  LIBRARY SECTIONS  /library/sections
    # =================================================================

    def library_sections(self) -> dict:
        movies_count = len(self.kodiproxy.get_movies())
        shows_count = len(self.kodiproxy.get_tvshows())

        sections = [
            self._section_dir(MOVIE_SECTION_ID, 'Movies', 'movie', 'Movie',
                              '/:/resources/movie-fanart.jpg', movies_count,
                              'com.plexapp.agents.imdb', SECTION_UUID_MOVIES),
            self._section_dir(SHOW_SECTION_ID, 'TV Shows', 'show', 'TV Series',
                              '/:/resources/show-fanart.jpg', shows_count,
                              'com.plexapp.agents.thetvdb', SECTION_UUID_SHOWS),
        ]

        return {'MediaContainer': {
            'size': len(sections),
            'allowSync': False,
            'title1': 'Plex Library',
            'title2': 'Plex Library',
            'identifier': 'com.plexapp.plugins.library',
            'machineIdentifier': PLEX_MACHINE_ID,
            'mediaTagPrefix': '/system/bundle/media/flags/',
            'mediaTagVersion': '1657676813',
            'Directory': sections,
        }}

    def _section_dir(self, sid, name, stype, scanner, art, count, agent, uuid):
        return {
            'allowSync': False, 'art': art, 'composite': '',
            'filters': True, 'refreshing': 'false', 'scanner': scanner,
            'scannerVersion': 2, 'key': '%d/all' % sid, 'language': 'en',
            'uuid': uuid, 'updatedAt': int(time.time()), 'createdAt': 0,
            'scannedAt': 0, 'agent': agent, 'deletedScript': '',
            'editing': 0, 'enableAutoSync': False, 'hidden': 0,
            'id': sid, 'lastScanned': int(time.time()), 'location': '',
            'name': name, 'plugin': '', 'queryScript': '',
            'refreshInterval': 14, 'type': stype, 'version': 15,
            'title': name,
        }

    # =================================================================
    #  SECTION CHILDREN  /library/sections/{id}/all
    # =================================================================

    def section_children(self, section_id: int, action: str, q: dict,
                         start: int = 0, size: int = PLEX_CONTAINER_SIZE) -> dict:
        if action == 'all':
            return self._section_all(section_id, start, size)
        if action == 'recentlyAdded':
            return self._section_recent(section_id, start, size)
        if action == 'onDeck':
            return self._section_on_deck(section_id, start, size)
        if action == 'search':
            return self._section_search(section_id, q, start, size)
        return self._section_all(section_id, start, size)

    def _section_all(self, sid: int, start: int, size: int) -> dict:
        if sid == MOVIE_SECTION_ID:
            return self._movies_container(start, size)
        if sid == SHOW_SECTION_ID:
            return self._shows_container(start, size)
        return self._empty('Movies')

    def _movies_container(self, start: int, size: int) -> dict:
        movies = self.kodiproxy.get_movies()
        total = len(movies)
        items = [self._movie_to_plex(m) for m in movies[start:start + size]]
        return self._wrap(items, total, start, 'Movies', 'All Movies')

    def _shows_container(self, start: int, size: int) -> dict:
        shows = self.kodiproxy.get_tvshows()
        total = len(shows)
        items = [self._show_to_plex(s) for s in shows[start:start + size]]
        return self._wrap(items, total, start, 'TV Shows', 'All Shows')

    def _section_recent(self, sid: int, start: int, size: int) -> dict:
        if sid == MOVIE_SECTION_ID:
            movies = self.kodiproxy.get_recently_added_movies(size)
            items = [self._movie_to_plex(m) for m in movies]
            return self._wrap(items, len(items), 0, 'Movies', 'Recently Added')
        if sid == SHOW_SECTION_ID:
            eps = self.kodiproxy.get_recently_added_episodes(size)
            items = [self._episode_to_plex(e) for e in eps]
            return self._wrap(items, len(items), 0, 'TV Shows', 'Recently Added')
        return self._empty('Recently Added')

    def _section_on_deck(self, sid: int, start: int, size: int) -> dict:
        return self._empty('On Deck')

    def _section_search(self, sid: int, q: dict, start: int, size: int) -> dict:
        query = q.get('query', q.get('title', ''))
        if not query:
            return self._empty('Search')
        results = self.kodiproxy.search(query)
        items = []
        if sid == MOVIE_SECTION_ID:
            items = [self._movie_to_plex(m) for m in results.get('movies', [])]
        elif sid == SHOW_SECTION_ID:
            items = [self._show_to_plex(s) for s in results.get('tvshows', [])]
        return self._wrap(items, len(items), 0, 'Search', query)

    def _wrap(self, items, total, offset, title1='', title2=''):
        return {'MediaContainer': {
            'size': len(items), 'totalSize': total, 'offset': offset,
            'allowSync': False, 'title1': title1, 'title2': title2,
            'identifier': 'com.plexapp.plugins.library',
            'machineIdentifier': PLEX_MACHINE_ID,
            'mediaTagPrefix': '/system/bundle/media/flags/',
            'mediaTagVersion': '1657676813',
            'Metadata': items,
        }}

    def _empty(self, title=''):
        return {'MediaContainer': {
            'size': 0, 'totalSize': 0, 'offset': 0,
            'title1': title, 'title2': title, 'Metadata': [],
        }}

    # =================================================================
    #  METADATA  /library/metadata/{key}
    #  CHILDREN  /library/metadata/{key}/children
    # =================================================================

    def metadata(self, rating_key: str, child: str, q: dict) -> dict:
        if child == 'children':
            return self._get_children(rating_key, q)
        if child == 'grandchildren':
            return self._get_grandchildren(rating_key, q)
        # Single item
        item = self._find_item(rating_key)
        if item:
            return {'MediaContainer': {'size': 1, 'Metadata': [item]}}
        return self._empty()

    def _get_children(self, parent_key: str, q: dict) -> dict:
        """Children of a show = episodes; children of a season = episodes."""
        # Check if parent is a show
        for s in self.kodiproxy.get_tvshows():
            sk = generate_ratingKey(s.get('tvshowid', 0), 'show')
            if sk == parent_key:
                eps = self.kodiproxy.get_episodes(s.get('tvshowid', 0))
                items = [self._episode_to_plex(e, s, sk) for e in eps]
                return self._wrap(items, len(items), 0, s.get('title', ''), 'All Episodes')
        return self._empty()

    def _get_grandchildren(self, parent_key: str, q: dict) -> dict:
        return self._empty()

    def _find_item(self, rating_key: str):
        for m in self.kodiproxy.get_movies():
            if generate_ratingKey(m.get('movieid', 0), 'movie') == rating_key:
                return self._movie_to_plex(m)
        for s in self.kodiproxy.get_tvshows():
            if generate_ratingKey(s.get('tvshowid', 0), 'show') == rating_key:
                return self._show_to_plex(s)
        for e in self.kodiproxy.get_episodes():
            if generate_ratingKey(e.get('episodeid', 0), 'episode') == rating_key:
                return self._episode_to_plex(e)
        return None

    def get_item_meta(self, rating_key: str) -> dict:
        """Return a Kodi-friendly metadata dict for the player OSD."""
        item = self._find_item(rating_key)
        if not item:
            return {}
        return {
            'title': item.get('title', ''),
            'year': item.get('year', 0),
            'summary': item.get('summary', ''),
            'rating': item.get('rating', 0),
            'contentRating': item.get('contentRating', ''),
            'type': item.get('type', 'video'),
            'durationInSeconds': item.get('duration', 0) // 1000 if item.get('duration', 0) else 0,
            'genres': [g.get('tag', '') for g in item.get('Genre', [])],
            'thumb': item.get('thumb', ''),
            'art': item.get('art', ''),
        }

    # =================================================================
    #  SEARCH  /hubs/search?query=...
    # =================================================================

    def search(self, query: str) -> dict:
        if not query:
            return self._empty('Search')
        results = self.kodiproxy.search(query)
        items = [self._movie_to_plex(m) for m in results.get('movies', [])]
        items += [self._show_to_plex(s) for s in results.get('tvshows', [])]
        return {'MediaContainer': {
            'size': len(items), 'Metadata': items,
            'title1': 'Search', 'title2': query,
        }}

    # =================================================================
    #  HUBS  /hubs
    # =================================================================

    def global_hubs(self) -> dict:
        hubs = []
        # Recently added movies
        recent_movies = self.kodiproxy.get_recently_added_movies(10)
        if recent_movies:
            hubs.append({
                'type': 'movie',
                'title': 'Recently Added Movies',
                'hubIdentifier': 'movie.recentlyAdded',
                'size': len(recent_movies),
                'Metadata': [self._movie_to_plex(m) for m in recent_movies],
            })
        # Recently added episodes
        recent_eps = self.kodiproxy.get_recently_added_episodes(10)
        if recent_eps:
            hubs.append({
                'type': 'episode',
                'title': 'Recently Added Episodes',
                'hubIdentifier': 'episode.recentlyAdded',
                'size': len(recent_eps),
                'Metadata': [self._episode_to_plex(e) for e in recent_eps],
            })
        return {'MediaContainer': {
            'size': len(hubs), 'Hub': hubs,
        }}

    # =================================================================
    #  SESSIONS  /status/sessions
    # =================================================================

    def sessions(self, pkplayer=None) -> dict:
        # First check if our PKBridge player is active
        if pkplayer:
            state = pkplayer.get_state()
            if state:
                return {'MediaContainer': {'size': 1, 'Metadata': [state]}}

        # Fallback: ask Kodi's JSONRPC for active players
        players = self.kodiproxy.get_active_players()
        if not players:
            return {'MediaContainer': {'size': 0, 'Metadata': []}}
        item = self.kodiproxy.get_player_item(players[0].get('playerid', 1))
        plex_item = {
            'ratingKey': '0',
            'key': '',
            'guid': '',
            'title': item.get('title', ''),
            'type': item.get('type', 'video'),
            'viewOffset': 0,
            'duration': (item.get('duration', 0) or 0) * 1000,
            'Player': {
                'state': 'playing', 'time': 0,
                'duration': (item.get('duration', 0) or 0) * 1000,
                'progress': 0, 'errorCode': 0,
                'machineIdentifier': PLEX_MACHINE_ID,
                'address': self.host.split(':')[0], 'port': int(self.host.split(':')[1]),
                'protocol': 'http', 'version': ADDON_VERSION,
            },
        }
        return {'MediaContainer': {'size': 1, 'Metadata': [plex_item]}}

    # =================================================================
    #  PLAYLISTS  /playlists
    # =================================================================

    def playlists(self) -> dict:
        return {'MediaContainer': {'size': 0, 'Metadata': []}}

    # =================================================================
    #  MEDIA PROVIDERS  /media/providers
    # =================================================================

    def media_providers(self) -> dict:
        return {'MediaContainer': {
            'size': 1,
            'MediaProvider': [{
                'identifier': 'com.plexapp.plugins.library',
                'protocol': 'file',
                'protocolCapabilities': 'timeline,search,skip,subs,webVideo,transcode,loudnessanalysis',
                'title': PLEX_SERVER_NAME,
                'updated': int(time.time()),
            }],
        }}

    # =================================================================
    #  SYSTEM  /system
    # =================================================================

    def system_info(self) -> dict:
        return {'MediaContainer': {
            'size': 0,
            'friendlyName': PLEX_SERVER_NAME,
            'machineIdentifier': PLEX_MACHINE_ID,
            'myPlex': False,
            'myPlexMappingState': '',
            'myPlexSigninState': '',
            'myPlexUsername': '',
            'platform': 'Kodi',
            'platformVersion': ADDON_VERSION,
            'transcoderActiveVideoSessions': 0,
            'updatedAt': int(time.time()),
            'version': '%s (%s)' % (ADDON_VERSION, PLEX_MACHINE_ID[:8]),
        }}

    # =================================================================
    #  ITEM TRANSLATION — Kodi dict -> Plex Metadata
    # =================================================================

    def _movie_to_plex(self, m: dict) -> dict:
        kid = m.get('movieid', 0)
        rk = generate_ratingKey(kid, 'movie')
        uid = m.get('uniqueid', {})
        imdb = uid.get('imdb', '')
        tmdb = uid.get('tmdb', '')
        guid = ('imdb://%s' % imdb) if imdb else ('tmdb://%s' % tmdb) if tmdb else ('local://%s' % rk)

        title = m.get('title', '')
        year = m.get('year', 0)
        art = m.get('art', {})

        genres = self._list(m.get('genre', []))
        studios = self._list(m.get('studio', []))
        directors = self._list(m.get('director', []))
        writers = self._list(m.get('writer', []))

        dur = self._ms_duration(m.get('duration', 0), m.get('runtime', 0))
        resume = m.get('resume', {}) or {}
        view_offset = int(resume.get('position', 0) * 1000)

        cast = []
        for a in (m.get('cast', []) or []):
            if isinstance(a, dict):
                cast.append({'tag': a.get('name', '')})
            elif isinstance(a, str):
                cast.append({'tag': a})

        file_path = m.get('file', '')
        stream_key = '%s/parts/%s/stream' % (self._base(), rk)

        return {
            'ratingKey': rk,
            'key': '/library/metadata/%s' % rk,
            'guid': guid,
            'studio': studios[0] if studios else '',
            'title': title,
            'titleSort': m.get('originaltitle', title),
            'contentRating': m.get('mpaa', ''),
            'summary': m.get('plot', ''),
            'rating': float(m.get('rating', 0)),
            'audienceRating': float(m.get('rating', 0)),
            'viewCount': m.get('playcount', 0),
            'viewOffset': view_offset,
            'duration': dur,
            'year': year,
            'thumb': self._art(art, 'poster'),
            'art': self._art(art, 'fanart'),
            'durationInSeconds': m.get('runtime', dur // 1000 if dur else 0),
            'originallyAvailableAt': m.get('premiered', ''),
            'addedAt': self._epoch(m.get('dateadded', '')),
            'updatedAt': int(time.time()),
            'type': 'movie',
            'Genre': [{'tag': g} for g in genres],
            'Director': [{'tag': d} for d in directors],
            'Writer': [{'tag': w} for w in writers],
            'Country': [],
            'Role': cast,
            'Media': [{
                'duration': dur,
                'bitrate': 0,
                'width': 0,
                'height': 0,
                'videoCodec': '',
                'videoResolution': '',
                'videoFrameRate': '',
                'audioChannels': 0,
                'audioCodec': '',
                'container': '',
                'videoProfile': '',
                'id': 0,
                'Part': [{
                    'id': 0,
                    'duration': dur,
                    'file': file_path,
                    'container': '',
                    'videoProfile': '',
                    'size': 0,
                    'key': stream_key,
                    'accessible': True,
                    'exists': True,
                }],
            }],
        }

    def _show_to_plex(self, s: dict) -> dict:
        kid = s.get('tvshowid', 0)
        rk = generate_ratingKey(kid, 'show')
        uid = s.get('uniqueid', {})
        tvdb = uid.get('tvdb', '')
        imdb = uid.get('imdb', '')
        guid = ('thetvdb://%s' % tvdb) if tvdb else ('imdb://%s' % imdb) if imdb else ('local://%s' % rk)

        title = s.get('title', '')
        art = s.get('art', {})
        genres = self._list(s.get('genre', []))
        studios = self._list(s.get('studio', []))

        return {
            'ratingKey': rk,
            'key': '/library/metadata/%s/children' % rk,
            'guid': guid,
            'studio': studios[0] if studios else '',
            'title': title,
            'titleSort': s.get('originaltitle', title),
            'contentRating': s.get('mpaa', ''),
            'summary': s.get('plot', ''),
            'rating': float(s.get('rating', 0)),
            'audienceRating': float(s.get('rating', 0)),
            'viewCount': s.get('playcount', 0),
            'year': s.get('year', 0),
            'thumb': self._art(art, 'poster'),
            'art': self._art(art, 'fanart'),
            'originallyAvailableAt': s.get('premiered', ''),
            'addedAt': self._epoch(s.get('dateadded', '')),
            'updatedAt': int(time.time()),
            'type': 'show',
            'childCount': s.get('season', 0),
            'leafCount': s.get('episode', 0),
            'viewedLeafCount': s.get('watchedepisodes', 0),
            'Genre': [{'tag': g} for g in genres],
            'Role': [],
        }

    def _episode_to_plex(self, e: dict, show: dict = None, show_rk: str = None) -> dict:
        kid = e.get('episodeid', 0)
        rk = generate_ratingKey(kid, 'episode')
        season_num = e.get('season', 0)
        ep_num = e.get('episode', 0)

        uid = {}
        if show:
            uid = show.get('uniqueid', {})
        tvdb = uid.get('tvdb', '')
        guid = ('thetvdb://%s/%d/%d' % (tvdb, season_num, ep_num)) if tvdb else ('local://%s' % rk)

        art = e.get('art', {})
        dur = self._ms_duration(e.get('duration', 0), e.get('runtime', 0))
        resume = e.get('resume', {}) or {}
        view_offset = int(resume.get('position', 0) * 1000)
        file_path = e.get('file', '')
        stream_key = '%s/parts/%s/stream' % (self._base(), rk)
        show_title = show.get('title', '') if show else ''
        show_art = show.get('art', {}) if show else {}

        return {
            'ratingKey': rk,
            'key': '/library/metadata/%s' % rk,
            'guid': guid,
            'parentRatingKey': show_rk or '',
            'grandparentRatingKey': show_rk or '',
            'parentTitle': show_title,
            'grandparentTitle': show_title,
            'title': e.get('title', ''),
            'titleSort': e.get('title', ''),
            'summary': e.get('plot', ''),
            'rating': float(e.get('rating', 0)),
            'audienceRating': float(e.get('rating', 0)),
            'viewCount': e.get('playcount', 0),
            'viewOffset': view_offset,
            'duration': dur,
            'year': show.get('year', 0) if show else 0,
            'thumb': self._art(art, 'poster'),
            'art': self._art(art, 'fanart'),
            'parentThumb': self._art(show_art, 'poster'),
            'grandparentThumb': self._art(show_art, 'poster'),
            'originallyAvailableAt': e.get('firstaired', ''),
            'addedAt': self._epoch(e.get('dateadded', '')),
            'updatedAt': int(time.time()),
            'type': 'episode',
            'index': ep_num,
            'parentIndex': season_num,
            'skipCount': 0,
            'skipParent': False,
            'Genre': [],
            'Writer': [],
            'Director': [],
            'Media': [{
                'duration': dur,
                'bitrate': 0,
                'width': 0,
                'height': 0,
                'videoCodec': '',
                'videoResolution': '',
                'videoFrameRate': '',
                'audioChannels': 0,
                'audioCodec': '',
                'container': '',
                'videoProfile': '',
                'id': 0,
                'Part': [{
                    'id': 0,
                    'duration': dur,
                    'file': file_path,
                    'container': '',
                    'videoProfile': '',
                    'size': 0,
                    'key': stream_key,
                    'accessible': True,
                    'exists': True,
                }],
            }],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _list(val) -> list:
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return [v.strip() for v in val.replace('/', ',').split(',') if v.strip()]
        return []

    @staticmethod
    def _ms_duration(dur_sec, runtime_sec) -> int:
        """Kodi returns seconds; Plex wants milliseconds."""
        d = runtime_sec or dur_sec or 0
        if isinstance(d, str):
            try:
                d = int(d)
            except ValueError:
                d = 0
        return d * 1000 if d < 100000 else d

    @staticmethod
    def _epoch(date_str: str) -> int:
        if not date_str:
            return int(time.time())
        try:
            return int(time.mktime(time.strptime(date_str, '%Y-%m-%d %H:%M:%S')))
        except (ValueError, OverflowError):
            return int(time.time())
