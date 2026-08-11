#   Copyright (C) 2026 Lunatixz
#
#
# This file is part of Smartplaylist Generator.
#
# Smartplaylist Generator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Smartplaylist Generator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import hashlib, json, re, threading

from globals  import *

MODEL_TYPES = {'movie':'movies','show':'tvshows','season':'seasons','episode':'episodes'}
TYPES       = ('movies','tvshows','seasons','episodes')
MAX_ROLL    = 5
DEFAULT_MODEL = 'cohere/north-mini-code:free'
# Known-stable free models on OpenRouter; rolled through when the configured
# model fails. Ordered by expected JSON reliability first.
FREE_MODELS = (
    'cohere/north-mini-code:free',
    'google/gemma-4-26b-a4b-it:free',
    'google/gemma-4-31b-it:free',
    'openai/gpt-oss-20b:free',
    'nvidia/nemotron-3-nano-30b-a3b:free',
    'poolside/laguna-xs-2.1:free',
    'openrouter/free',
)

SYSTEM_PROMPT = (
 "You are a media cataloging assistant for a Kodi media center building a smartplaylist from the user's request.\n"
 "Analyze the request and respond with ONLY a single valid JSON object (no prose, no markdown fences).\n"
 'Schema: {"movies":[{"title":"...","year":2010,"uniqueid":{"imdb":"tt...","tmdb":123,"trakt":...,"tvdb":...}}],'
 '"tvshows":[...],"seasons":[...],'
 '"episodes":[{"title":"...","year":2010,"season":1,"episode":3,"showtitle":"...","uniqueid":{"imdb":"tt...","tvdb":...}}],'
 '"layout":"episode_order|random|chronological|mixed|..."}\n'
 "Rules:\n"
 "- Decide which type keys to fill: movies, tvshows, seasons, episodes. Fill all that apply.\n"
 "- Only include content that genuinely belongs to the requested theme, universe, or series. "
 "Never include same-named or lookalike content from outside the theme (e.g. for a Star Trek request, "
 "do NOT list 'Speed', 'Star Wars', or unrelated shows). When unsure a title belongs to the theme, leave it out.\n"
 "- Use exact canonical titles and correct original release years. Never invent or approximate titles.\n"
 "- Always include the original release 'year' for every entry.\n"
 "- For every episode, always include its 'season' and 'episode' numbers (e.g. season 1, episode 3) and the "
 "parent show's exact title in 'showtitle'.\n"
 "- Include every reference id you know for an entry - imdb (tt...), tmdb, trakt, tvdb - in 'uniqueid'.\n"
 "- Fill each list with every well-known real title matching the request - do not limit the count.\n"
 "- Track the requested content type and layout (episode order, random, chronological, marathon, etc.) in 'layout'.\n"
 "- Honor requested specifics: genres, actors, year ranges, studios, ratings.\n"
 "- If the media type is unclear, fill a mix of movies and tvshows."
)

PROOFREAD_PROMPT = (
 "You proofread a Kodi smartplaylist request before it is saved.\n"
 "Respond with ONLY a single valid JSON object (no prose, no markdown fences): "
 '{"name":"...","prompt":"..."}\n'
 'The "name" must keep the original playlist name verbatim, then append a short parenthetical tag capturing the '
 'key distinguishing details from the request (content type, layout such as episode order/random/chronological, '
 'genre, actor, year) so the playlist stands out among others, e.g. "Star Trek (Chronological Sci-Fi)".\n'
 'The "prompt" is the request with typos and grammar fixed, keeping every intent: content type, layout, genres, '
 'actors, year ranges.'
)

class OpenRouter:
    match_mode = 'title'

    def __init__(self, cache=None):
        self.monitor = MONITOR()
        if cache is None: self.cache = SimpleCache()
        else:
            self.cache = cache
            self.cache.enable_mem_cache = False

        self.enabled = REAL_SETTINGS.getSetting('Enable_OpenRouter') == 'true'
        self.name    = LANGUAGE(32200)
        self.logo    = ICON
        self._error_notified = False


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _headers(self):
        return { 'Content-Type': 'application/json',
                 'Authorization': 'Bearer %s'%(REAL_SETTINGS.getSetting('OpenRouter_APIKEY')),
                 'X-Title': ADDON_NAME }


    def _notify(self, message):
        if self._error_notified: return
        self._error_notified = True
        xbmcgui.Dialog().notification(ADDON_NAME, message, ICON, PROMPT_DELAY)


    def _handleError(self, response):
        # OpenRouter's standard error body: {"error": {"code": ..., "message": "..."}}
        message = None
        try:
            message = (response.json().get('error') or {}).get('message')
        except Exception: pass
        if message:             self._notify(str(message))
        elif response.status_code == 401: self._notify(LANGUAGE(32213))
        else:                   self._notify('OpenRouter error %s'%(response.status_code))


    def _request(self, payload, timeout=30):
        if not REAL_SETTINGS.getSettingBool('Enable_OpenRouter'): return {}
        # requests' timeout is unreliable on some Kodi platforms, so enforce a
        # hard wall-clock cap in a daemon thread: a hung model can never block
        # the build lock forever.
        result = {}

        def _call():
            try:
                response = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=self._headers(), json=payload, timeout=(5, timeout))
                if response.status_code == 200: result['data'] = response.json()
                else: self.log('_request, failed! %s'%(response.status_code), xbmc.LOGERROR)
            except Exception as e: self.log('_request, failed! %s'%(e), xbmc.LOGERROR)

        thread = threading.Thread(target=_call, daemon=True)
        thread.start()
        thread.join(timeout + 10)
        if thread.is_alive():
            self.log('_request, timed out after %s secs'%(timeout + 10), xbmc.LOGERROR)
            return {}
        return result.get('data', {})


    def _free_models(self):
        # Live list of free text models for the roll, cached for a day:
        # OpenRouter-hosted free models the key can access, plus free BYOK
        # models the user's own provider keys may unlock. Falls back to the
        # hardcoded FREE_MODELS if the fetch fails.
        cached = self.cache.get('openrouter.free_models', ADDON_VERSION, True)
        if cached: return cached
        models = list(FREE_MODELS)
        try:
            response = requests.get('https://openrouter.ai/api/v1/models', headers=self._headers(), timeout=15)
            if response.status_code == 200:
                free = sorted([m.get('id') for m in response.json().get('data', [])
                               if 'text' in m.get('architecture',{}).get('output_modalities', [])
                               and self._is_free(m)
                               and (self._hasAccess(m) or self._is_byok(m))])
                if free:
                    models = free
                    self.cache.set('openrouter.free_models', models, ADDON_VERSION, datetime.timedelta(days=1), True)
        except Exception as e:
            self.log('_free_models, fetch failed! %s'%(e), xbmc.LOGWARNING)
        return models


    def _model_chain(self):
        # Stick to the user's configured model first, then the free roll only.
        configured = REAL_SETTINGS.getSetting('OpenRouter_Model') or DEFAULT_MODEL
        chain = []
        for m in (configured,) + tuple(self._free_models()):
            if m and m not in chain: chain.append(m)
        return chain


    def _chat(self, messages, temperature=0.4):
        # Try the user's configured model, then roll through the free list
        # (capped so a bad run can't block the build lock for minutes).
        for model in self._model_chain()[:MAX_ROLL]:
            payload = { 'model': model, 'temperature': temperature, 'messages': messages,
                        'provider': { 'allow_fallbacks': True, 'require_parameters': True, 'data_collection': 'deny' }}
            response = self._request(payload)
            if not response:
                self.log('_chat, model %s failed, rolling to next'%(model), xbmc.LOGWARNING)
                continue
            try: content = response['choices'][0]['message']['content']
            except Exception as e:
                self.log('_chat, bad response shape from %s: %s'%(model, e), xbmc.LOGWARNING)
                continue
            data = self._parse_json(content)
            if data is None:
                self.log('_chat, model %s returned unparseable output, rolling'%(model), xbmc.LOGWARNING)
                continue
            self.log('_chat, model %s responded OK'%(model))
            return data
        self.log('_chat, all models failed', xbmc.LOGERROR)
        return None


    def _prompts_file(self):
        return os.path.join(SETTINGS_LOC, 'openrouter_playlists.json')


    def _load(self):
        if not xbmcvfs.exists(self._prompts_file()): return []
        try:
            fle  = xbmcvfs.File(self._prompts_file(), 'r')
            raw  = fle.read()
            fle.close()
            return json.loads(raw)
        except Exception as e:
            self.log('_load, failed! %s'%(e), xbmc.LOGWARNING)
            return []


    def _save(self, prompts):
        fle = xbmcvfs.File(self._prompts_file(), 'w')
        fle.write(json.dumps(prompts, indent=2))
        fle.close()


    def _find(self, playlist_id):
        for p in self._load():
            if p.get('id') == playlist_id: return p
        return None


    def get_lists(self):
        if not self.enabled: return []
        return [{'name': p.get('name'), 'description': p.get('prompt'), 'id': p.get('id'), 'icon': self.logo} for p in self._load()]


    def get_list_items(self, playlist_id):
        if not self.enabled: return {}
        playlist = self._find(playlist_id)
        if not playlist: return {}
        # Hash the playlist (prompt + rules + generation counter) so edits or
        # 'Regenerate' produce a new cache key -> one AI call per distinct prompt.
        key = 'openrouter.ai.%s.%s'%(playlist_id, hashlib.md5(json.dumps(playlist).encode('utf-8')).hexdigest()[:10])
        results = self.cache.get(key, ADDON_VERSION, True)
        if results: return results
        # Negative cache: a failed/empty generation means don't burn tokens
        # re-asking for the same prompt within the next 30 minutes.
        fail_key = 'openrouter.fail.%s'%(key)
        if self.cache.get(fail_key, ADDON_VERSION, True):
            self.log('get_list_items, cached failure for %s, skipping API call'%(playlist_id))
            return {}
        results = self._generate(playlist)
        if results:
            self.cache.set(key, results, ADDON_VERSION, datetime.timedelta(days=90), True)
        else:
            self.cache.set(fail_key, True, ADDON_VERSION, datetime.timedelta(minutes=30), True)
        return results


    def _generate(self, playlist):
        prompt = playlist.get('prompt','')
        rules  = playlist.get('rules', [])
        if rules:
            prompt += '\n\nAlso enforce these rules:\n' + '\n'.join('field=%s, operator=%s, value=%s'%(r.get('field'),r.get('operator'),r.get('value')) for r in rules)
        data = self._chat([{'role':'system','content': SYSTEM_PROMPT},
                           {'role':'user','content': prompt}], 0.4)
        if data is None:
            self._notify(LANGUAGE(32214))
            return {}
        return self._normalize(data)


    @staticmethod
    def _parse_json(content):
        match = re.search(r'\{.*\}', content, re.S)
        if not match: return None
        try: return json.loads(match.group(0))
        except Exception: return None


    def _normalize(self, data):
        layout = data.get('layout')
        if layout: self.log('_parse, layout = %s'%(layout))
        tmp = {}
        for mtype, mkey in MODEL_TYPES.items():
            items = data.get(mkey) or []
            if not isinstance(items, list): continue
            for item in items:
                if not isinstance(item, dict) or not item.get('title'): continue
                tmp.setdefault(mkey, []).append({'type': mtype, 'title': item.get('title'), 'year': item.get('year'), 'season': item.get('season'), 'episode': item.get('episode'), 'showtitle': item.get('showtitle'), 'uniqueid': item.get('uniqueid') or {}, 'data': item})
        for mkey in TYPES:
            tmp.setdefault(mkey, [])
        return tmp


    def _parse(self, content):
        data = self._parse_json(content)
        if data is None:
            self.log('_parse, no valid JSON in response', xbmc.LOGWARNING)
            return {}
        return self._normalize(data)


    def _proofread(self, name, prompt):
        data = self._chat([{'role':'system','content': PROOFREAD_PROMPT},
                           {'role':'user','content': 'Playlist name: %s\nRequest: %s'%(name, prompt)}], 0.2)
        if not data: return None
        return {'name': data.get('name') or name, 'prompt': data.get('prompt') or prompt}


    def _hasAccess(self, model):
        # OpenRouter marks per-user access via endpoints[].is_provider_allowlisted.
        # Hide models with no usable endpoint; no access info -> assume usable.
        allowlisted = [e.get('is_provider_allowlisted') for e in (model.get('endpoints') or [])]
        if not allowlisted or all(v is None for v in allowlisted): return True
        return any(allowlisted)


    @staticmethod
    def _is_free(model):
        if (model.get('id') or '').endswith(':free'): return True
        pricing = model.get('pricing') or {}
        try:
            return float(pricing.get('prompt') or '1') == 0 and float(pricing.get('completion') or '1') == 0
        except Exception: return False


    @staticmethod
    def _is_byok(model):
        # Bring-Your-Own-Key endpoints: served via the user's own provider key.
        return any(e.get('is_byok') for e in (model.get('endpoints') or []))


    @staticmethod
    def _sort_key(model):
        # Free first, then BYOK, then the rest; alphabetical within each group.
        rank = 0 if OpenRouter._is_free(model) else (1 if OpenRouter._is_byok(model) else 2)
        return (rank, (model.get('name') or '').lower())


    def _display_name(self, model):
        name = model.get('name', 'Unknown')
        if self._is_free(model) and '(free' not in name.lower(): name += ' (Free)'
        if self._is_byok(model) and '(byok' not in name.lower(): name += ' (BYOK)'
        return name


    def _getContextModels(self):
        if not self.enabled: return
        try:
            response = requests.get('https://openrouter.ai/api/v1/models', headers=self._headers(), timeout=15)
            if response.status_code != 200:
                self._handleError(response)
                return
            models = [m for m in response.json().get('data', [])
                      if 'text' in m.get('architecture',{}).get('output_modalities', [])
                      and self._hasAccess(m)]
            models = sorted(models, key=self._sort_key)
            current = REAL_SETTINGS.getSetting('OpenRouter_Model')
            preselect = next((i for i, m in enumerate(models) if m.get('id') == current), -1)
            self.log('_getContextModels, accessible text models = %s, preselect = %s'%(len(models), preselect))
            sel = xbmcgui.Dialog().select('OpenRouter Model', [self._display_name(m) for m in models], preselect=preselect)
            if sel > -1: REAL_SETTINGS.setSetting('OpenRouter_Model', models[sel].get('id'))
        except Exception as e: self.log('_getContextModels, failed! %s'%(e), xbmc.LOGERROR)


    def add_playlist(self):
        dlg = xbmcgui.Dialog()
        name = dlg.input('AI Playlist Name', type=xbmcgui.INPUT_ALPHANUM)
        if not name: return
        prompt = dlg.input('Describe the content you want', type=xbmcgui.INPUT_ALPHANUM)
        if not prompt: return
        playlist = {'id': str(uuid.uuid4()), 'name': name, 'prompt': prompt, 'rules': []}
        if self.enabled:
            corrected = self._proofread(name, prompt)
            if corrected:
                playlist['name']   = corrected.get('name')   or name
                playlist['prompt'] = corrected.get('prompt') or prompt
        prompts = self._load()
        prompts.append(playlist)
        self._save(prompts)
        self._select(playlist)
        self._build()
        dlg.notification(ADDON_NAME, 'Playlist added')


    def _select(self, playlist):
        key      = '%s.%s'%(ADDON_ID, self.name)
        selected = self.cache.get(key, 1, False) or []
        if not any(item.get('id') == playlist.get('id') for item in selected):
            selected.append({'name': playlist.get('name'), 'id': playlist.get('id'), 'icon': self.logo})
            self.cache.set(key, selected, 1, datetime.timedelta(days=84), False)


    def _build(self):
        xbmc.executebuiltin('RunScript(special://home/addons/%s/resources/lib/default.py, Build_OpenRouter)'%(ADDON_ID))


    def manage(self):
        dlg = xbmcgui.Dialog()
        prompts = self._load()
        if not prompts:
            dlg.notification(ADDON_NAME, 'No AI playlists yet')
            return
        idx = dlg.select('AI Playlists', [p.get('name') for p in prompts])
        if idx < 0: return
        p = prompts[idx]
        act = dlg.select(p.get('name'), ['Edit Name', 'Edit Prompt', 'Add Rule', 'Regenerate', 'Clear Build Time', 'Delete'])
        if act < 0: return
        if act == 0:
            name = dlg.input('Playlist Name', default=p.get('name'))
            if name: p['name'] = name
        elif act == 1:
            prompt = dlg.input('Describe the content you want', default=p.get('prompt'))
            if prompt: p['prompt'] = prompt
        elif act == 2:
            field = dlg.input('Field (genre, actor, title, year, studio, mpaa, rating)', type=xbmcgui.INPUT_ALPHANUM)
            if not field: return
            op    = dlg.input('Operator (is, isnot, contains, doesnotcontain, greaterthan, lessthan)', default='contains')
            value = dlg.input('Value', type=xbmcgui.INPUT_ALPHANUM)
            if not value: return
            p.setdefault('rules', []).append({'field': field, 'operator': op, 'value': value})
        elif act == 3:
            p['gen'] = int(p.get('gen', 0)) + 1
        elif act == 4:
            self.cache.delete('%s.BuildTime.%s'%(ADDON_ID, p.get('id')), 1, False)
        elif act == 5:
            if dlg.yesno(ADDON_NAME, 'Delete %s?' % p.get('name')):
                prompts.pop(idx)
                self._save(prompts)
                return
        self._save(prompts)
        self._build()
        dlg.notification(ADDON_NAME, 'Updated')


    def _run(self, sysARG=sys.argv):
        param = sysARG[1] if len(sysARG) > 1 else None
        self.log('_run, param = %s'%(param))
        if   param == 'AddPlaylist':      self.add_playlist()
        elif param == 'ManagePlaylists':  self.manage()
        elif param == 'getContextModels': self._getContextModels()
        REAL_SETTINGS.openSettings()


if __name__ == '__main__': OpenRouter()._run(sys.argv)
