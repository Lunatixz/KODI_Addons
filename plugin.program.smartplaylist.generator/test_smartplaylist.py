# -*- coding: utf-8 -*-
# Run: python test_smartplaylist.py
# Standalone check of IMDB/Trakt classification + parsing (stubs Kodi/network).
import json
import os
import sys
import types

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib')


def stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


class FakeAddon:
    def getAddonInfo(self, k): return 'x'
    def getSetting(self, k): return 'false'
    def getSettingBool(self, k): return False
    def setSetting(self, *a): pass
    def getLocalizedString(self, k): return 'str%s' % k
    def openSettings(self): pass


class FakeResp:
    def __init__(self, content=b''):
        self.content = content
        self.status_code = 200
    @property
    def text(self): return self.content.decode('utf-8', 'replace')
    @property
    def headers(self): return {'Content-Type': 'text/html'}
    def raise_for_status(self): pass
    def json(self): return json.loads(self.content)


class Mon:
    def abortRequested(self): return False
    def waitForAbort(self, *a): return False


RESP = {}
def _get(url, *a, **k):
    for key in RESP:
        if key in url:
            return RESP[key]
    raise AssertionError('no stub for url %s' % url)
def _post(url, *a, **k):
    model = (k.get('json') or {}).get('model', '')
    if model and model in RESP:
        return RESP[model]
    for key in RESP:
        if key in url:
            return RESP[key]
    return FakeResp(b'{"choices":[{"message":{"content":"no json"}}]}')
stub('requests', get=_get, post=_post)
stub('xbmc', LOGDEBUG=0, LOGINFO=2, LOGWARNING=3, LOGERROR=4,
     Monitor=lambda: Mon(), Player=object, InfoTagVideo=object,
     log=lambda *a: None, executeJSONRPC=lambda *a: '{}',
     getCondVisibility=lambda *a: False, executebuiltin=lambda *a: None)
xbmcgui = stub('xbmcgui', Window=object, Dialog=object, ListItem=object,
               DialogProgressBG=object, NOTIFICATION_INFO=0)
stub('xbmcaddon', Addon=lambda id: FakeAddon())
stub('xbmcplugin')
stub('xbmcvfs', translatePath=lambda p: p, File=object, exists=lambda p: False)
stub('kodi_six', xbmc=sys.modules['xbmc'], xbmcaddon=sys.modules['xbmcaddon'],
     xbmcplugin=sys.modules['xbmcplugin'], xbmcgui=xbmcgui, xbmcvfs=sys.modules['xbmcvfs'])
stub('infotagger', listitem=stub('infotagger.listitem', ListItemInfoTag=object))
stub('simplecache', SimpleCache=object)
stub('simplecache.simplecache', SimpleCache=object)


class _Script:
    string = ''


class _Soup:
    def __init__(self, string):
        self._string = string
    def find(self, *a, **k):
        s = _Script(); s.string = self._string; return s
    def find_all(self, *a, **k):
        return []


stub('bs4', BeautifulSoup=lambda content, parser: _Soup(content.decode('utf-8', 'replace')))

sys.path.insert(0, ROOT)
from parsers import imdb, trakt, openrouter  # noqa: E402

m = imdb.IMDB.__new__(imdb.IMDB)

assert m.classify('Movie') == 'movies'
assert m.classify('TV Series') == 'tvshows'
assert m.classify('tvMiniSeries') == 'tvshows'
assert m.classify('TV Episode') == 'episodes'
assert m.classify('Video') is None
assert m.classify('') is None
assert m.classify(None) is None

CSV = ('\ufeffPosition,Const,Created,Modified,Description,Title,URL,Title Type,IMDb Rating,Runtime (mins),Year,Genres,Num Votes,Release Date,Directors\n'
       '1,tt0111161,,,,"The Shawshank Redemption",https://www.imdb.com/title/tt0111161/,Movie,9.3,142,1994,"Drama, Crime",2870496,1994-10-14,Frank Darabont\n'
       '2,tt0944947,,,,"Game of Thrones",https://www.imdb.com/title/tt0944947/,TV Series,9.2,57,2011,"Action, Adventure, Drama",2369769,2011-04-17,David Benioff\n'
       '3,tt1480055,,,,"The Walking Dead",https://www.imdb.com/title/tt1480055/,TV Mini Series,8.2,45,2010,"Drama, Horror",1144290,2010-10-31,Frank Darabont\n'
       '4,tt0944947,,,,"Winter Is Coming",https://www.imdb.com/title/tt1480055/,TV Episode,9.0,57,2011,"Action, Adventure, Drama",2369769,2011-04-17,Timothy Van Patten\n'
       '5,tt0111161,,,,"Some Video",https://www.imdb.com/title/tt0111161/,Video,5.0,10,2000,"X",1,,John')
d = m._parse_csv(CSV)
assert sorted(d) == ['episodes', 'movies', 'tvshows'], sorted(d)
assert d['movies'][0]['uniqueid'] == {'imdb': 'tt0111161'}
assert len(d['movies']) == 1 and len(d['tvshows']) == 2 and len(d['episodes']) == 1

PAGE = ('{"props":{"pageProps":{"contentData":{"list":{"items":['
        '{"item":{"id":"tt1","titleText":{"text":"A"},"titleType":{"id":"movie"}}},'
        '{"item":{"id":"tt2","titleText":{"text":"B"},"titleType":{"id":"tvSeries"}}},'
        '{"item":{"id":"tt3","titleText":{"text":"C"},"titleType":{"id":"video"}}}'
        ']}}}}}').encode('utf-8')
RESP['ls123'] = FakeResp(PAGE)
d2 = m._parse_page('ls123', {})
assert sorted(d2) == ['movies', 'tvshows'], sorted(d2)
assert d2['movies'][0]['uniqueid'] == {'imdb': 'tt1'}

PAGE_NEW = ('{"props":{"pageProps":{"mainColumnData":{"list":{"titleListItemSearch":{"edges":['
            '{"listItem":{"id":"tt0092455","titleText":{"text":"STTNG"},"titleType":{"id":"tvSeries"},"releaseYear":{"year":1987}}},'
            '{"listItem":{"id":"tt0102975","titleText":{"text":"STVI"},"titleType":{"id":"movie"},"releaseYear":{"year":1991}}}'
            ']}}}}}}').encode('utf-8')
RESP['ls4173525176'] = FakeResp(PAGE_NEW)
d2b = m._parse_page('ls4173525176', {})
assert sorted(d2b) == ['movies', 'tvshows'], sorted(d2b)
assert d2b['tvshows'][0]['uniqueid'] == {'imdb': 'tt0092455'} and d2b['tvshows'][0]['year'] == 1987
assert d2b['movies'][0]['uniqueid'] == {'imdb': 'tt0102975'} and d2b['movies'][0]['year'] == 1991

LISTS_NEW = ('{"props":{"pageProps":{"mainColumnData":{"userListSearch":{"edges":['
             '{"node":{"id":"ls4173525176","name":{"originalText":"Star Trek TV/Movie"},"description":null}},'
             '{"node":{"id":"ls2","name":{"originalText":"Other List"},"description":{"plainText":"desc"}}}'
             ']}}}}}').encode('utf-8')
RESP['/user/false/lists'] = FakeResp(LISTS_NEW)
imdb_user = imdb.IMDB.__new__(imdb.IMDB)
imdb_user.enabled = True
imdb_user.logo = 'imdb.png'
lst = imdb.IMDB.get_lists.__wrapped__(imdb_user)
assert lst == [{'name': 'Other List', 'description': 'desc', 'id': 'ls2', 'icon': 'imdb.png'},
               {'name': 'Star Trek TV/Movie', 'description': '', 'id': 'ls4173525176', 'icon': 'imdb.png'}], lst

assert m._parse_csv('<html><body>blocked</body></html>') == {}

t = trakt.Trakt.__new__(trakt.Trakt)
t.monitor = Mon()

PERSON = [{'type': 'person', 'person': {'name': 'Tom Hanks', 'ids': {'trakt': 100, 'slug': 'tom-hanks'}}}]
MOVIES = [{'type': 'movie', 'movie': {'title': 'Toy Story', 'year': 1995, 'ids': {'trakt': 1, 'imdb': 'tt0114709'}}}]
SHOWS  = [{'type': 'show',  'show':  {'title': 'The Pacific', 'year': 2010, 'ids': {'trakt': 2, 'imdb': 'tt0374463'}}}]
SEASONS= [{'type': 'season', 'season': {'number': 1, 'ids': {'trakt': 3}}, 'show': {'title': 'The Pacific', 'ids': {'trakt': 2}}}]
EPS    = [{'type': 'episode', 'episode': {'title': 'Part One', 'number': 1, 'ids': {'trakt': 4, 'imdb': 'tt1480055'}}}]
RESP['/items/movie'] = FakeResp(json.dumps(MOVIES).encode())
RESP['/items/show'] = FakeResp(json.dumps(SHOWS).encode())
RESP['/items/season'] = FakeResp(json.dumps(SEASONS).encode())
RESP['/items/episode'] = FakeResp(json.dumps(EPS).encode())
RESP['/items/person'] = FakeResp(json.dumps(PERSON).encode())

out = trakt.Trakt.get_list_items.__wrapped__(t, '123')
assert out['persons'] == [{'name': 'Tom Hanks', 'id': '100'}], out['persons']
assert out['movies'][0]['uniqueid'] == {'trakt': 1, 'imdb': 'tt0114709'}
assert out['tvshows'][0]['uniqueid'] == {'trakt': 2, 'imdb': 'tt0374463'}

PCAST = {'cast': [{'character': 'Woody', 'movie': {'title': 'Toy Story', 'year': 1995, 'ids': {'imdb': 'tt0114709'}}}],
         'crew': [{'job': 'Director', 'movie': {'title': 'Crew Film', 'ids': {'imdb': 'tt0000000'}}}]}
SCAST = {'cast': [{'character': 'Colonel', 'show': {'title': 'The Pacific', 'year': 2010, 'ids': {'imdb': 'tt0374463'}}}],
         'crew': [{'job': 'Creator', 'show': {'title': 'Crew Show', 'ids': {'imdb': 'tt0000001'}}}]}
RESP['/people/100/movies'] = FakeResp(json.dumps(PCAST).encode())
RESP['/people/100/shows'] = FakeResp(json.dumps(SCAST).encode())

credits = trakt.Trakt.get_trakt_person.__wrapped__(t, '100')
assert sorted(credits) == ['movies', 'tvshows'], credits
assert len(credits['movies']) == 1 and credits['movies'][0]['title'] == 'Toy Story'
assert credits['movies'][0]['uniqueid'] == {'imdb': 'tt0114709'}
assert len(credits['tvshows']) == 1 and credits['tvshows'][0]['title'] == 'The Pacific'
assert not any('Crew' in item['title'] for key in credits for item in credits[key])

t2 = trakt.Trakt.__new__(trakt.Trakt)
t2.monitor = Mon()
t2.enabled = False
assert trakt.Trakt.get_lists.__wrapped__(t2) == []

t3 = trakt.Trakt.__new__(trakt.Trakt)
t3.monitor = Mon()
t3.enabled = True
t3.logo = 'trakt.png'
RESP['/users/false/lists'] = FakeResp(json.dumps(
    [{'name': 'My List', 'description': 'desc', 'ids': {'trakt': 42}}]).encode())
lst = trakt.Trakt.get_lists.__wrapped__(t3)
assert lst == [{'name': 'My List', 'description': 'desc', 'id': '42', 'icon': 'trakt.png'}], lst

import default as default_mod  # noqa: E402


def _serial_poolit(method):
    def wrapper(items=[], *args, **kwargs):
        return [method(item, *args, **kwargs) for item in items]
    return wrapper


default_mod.poolit = _serial_poolit


class FakeKodi:
    def progressBGDialog(self, *a, **k): return None
    def get_kodi_movies(self): return KODI_MOVIES
    def get_kodi_tvshows(self): return []
    def get_kodi_episodes(self): return KODI_EPISODES
    def get_kodi_seasons(self, *a, **k): return []


KODI_MOVIES = [{'title': 'RED', 'year': 2010, 'uniqueid': {'imdb': 'tt1245526', 'tmdb': '39514'}},
               {'title': 'Toy Story', 'year': 1995, 'uniqueid': {'imdb': 'tt0114709'}}]
KODI_EPISODES = [
    {'title': 'The Man Trap', 'showtitle': 'Star Trek', 'season': 1, 'episode': 1, 'file': 'smb://TV/Star Trek S01E01.mkv', 'uniqueid': {}},
    {'title': 'The Man Trap', 'showtitle': 'Other Show', 'season': 1, 'episode': 1, 'file': 'smb://TV/Other S01E01.mkv', 'uniqueid': {}},
    {'title': 'Charlie X', 'showtitle': 'Star Trek', 'season': 1, 'episode': 2, 'file': 'smb://TV/Star Trek S01E02.mkv', 'uniqueid': {}},
]
sp = default_mod.SPGenerator.__new__(default_mod.SPGenerator)
sp.kodi = FakeKodi()
sp.dia = None
sp.msg = 'Matching'
sp.pct = 0
sp.cntpct = 0
sp.cnt = 0
sp.tot = 0

out = sp.match_items({'movies': [
    {'title': 'Bad', 'uniqueid': {'imdb': {'nested': 'x'}}},
    {'title': 'RED', 'uniqueid': {'imdb': 'tt1245526'}},
]})
assert [m['title'] for m in out['movies']] == ['RED'], out

ai = openrouter.OpenRouter.__new__(openrouter.OpenRouter)
RAW = ('```json\n{"movies":[{"title":"RED","year":2010,"uniqueid":{"imdb":"tt1245526"}},'
       '{"title":"Interstellar","year":2014,"uniqueid":{"imdb":"tt0816692"}}],'
       '"tvshows":[{"title":"The Expanse","year":2015,"uniqueid":{"imdb":"tt3230854"}}],'
       '"episodes":[],"seasons":[],"layout":"random"}\n```')
parsed = ai._parse(RAW)
assert sorted(parsed) == ['episodes', 'movies', 'seasons', 'tvshows'], sorted(parsed)
assert parsed['movies'][0]['uniqueid'] == {'imdb': 'tt1245526'}
assert len(parsed['movies']) == 2 and len(parsed['tvshows']) == 1
assert parsed['episodes'] == [] and parsed['seasons'] == []
assert ai._parse('no json here') == {}

BIG = '{"movies":[' + ','.join('{"title":"M%d","uniqueid":{}}' % i for i in range(50)) + ']}'
assert len(ai._parse(BIG)['movies']) == 50, 'AI list must not be capped'

assert ai._hasAccess({'endpoints': [{'is_provider_allowlisted': True}]})
assert not ai._hasAccess({'endpoints': [{'is_provider_allowlisted': False}]})
assert not ai._hasAccess({'endpoints': [{'is_provider_allowlisted': False}, {'is_provider_allowlisted': False}]})
assert ai._hasAccess({'endpoints': [{'is_provider_allowlisted': False}, {'is_provider_allowlisted': True}]})
assert ai._hasAccess({'endpoints': [{'api_base_url': 'x'}]})
assert ai._hasAccess({})

assert ai._is_free({'id': 'x:free', 'pricing': {}})
assert ai._is_free({'id': 'x', 'pricing': {'prompt': '0', 'completion': '0'}})
assert not ai._is_free({'id': 'x', 'pricing': {'prompt': '0.5', 'completion': '0.5'}})
assert not ai._is_free({'id': 'x', 'pricing': {}})
assert ai._display_name({'name': 'Llama 3.3', 'id': 'x:free'}) == 'Llama 3.3 (Free)'
assert ai._display_name({'name': 'Some Model', 'id': 'x', 'pricing': {'prompt': '1'}}) == 'Some Model'

assert ai._is_byok({'endpoints': [{'is_byok': True}]})
assert not ai._is_byok({'endpoints': [{'is_byok': False}]})
assert not ai._is_byok({})
assert ai._display_name({'name': 'Custom', 'endpoints': [{'is_byok': True}]}) == 'Custom (BYOK)'
assert ai._display_name({'name': 'Gem', 'id': 'g:free', 'endpoints': [{'is_byok': True}]}) == 'Gem (Free) (BYOK)'

MODELS_SORT = [
    {'name': 'Z Paid', 'id': 'z', 'pricing': {'prompt': '1'}},
    {'name': 'B Free', 'id': 'b:free'},
    {'name': 'A BYOK', 'endpoints': [{'is_byok': True}], 'pricing': {'prompt': '1'}},
]
ordered = sorted(MODELS_SORT, key=openrouter.OpenRouter._sort_key)
assert [m['name'] for m in ordered] == ['B Free', 'A BYOK', 'Z Paid'], ordered

sp3 = default_mod.SPGenerator.__new__(default_mod.SPGenerator)
sp3.kodi = FakeKodi()
sp3.dia = None
sp3.msg = ''
sp3.pct = 0
sp3.cntpct = 0
sp3.cnt = 0
sp3.tot = 0
out2 = sp3.match_items({'movies': [
    {'title': 'red', 'uniqueid': {}},
    {'title': 'Unknown Film', 'uniqueid': {}},
]}, by_title=True)
assert [m['title'] for m in out2['movies']] == ['RED'], out2
out3 = sp3.match_items({'movies': [{'title': 'RED', 'uniqueid': {}}]})
assert 'movies' not in out3, out3

out4 = sp3.match_items({'movies': [
    {'title': 'RED', 'year': 2010, 'uniqueid': {}},
    {'title': 'RED', 'year': 1990, 'uniqueid': {}},
]}, by_title=True)
assert [m['title'] for m in out4['movies']] == ['RED'], 'wrong-year title must not match'
out5 = sp3.match_items({'movies': [
    {'title': 'Totally Wrong', 'year': 1999, 'uniqueid': {'imdb': 'tt1245526'}},
]}, by_title=True)
assert [m['title'] for m in out5['movies']] == ['RED'], 'uniqueid match must win over title'

ep6 = sp3.match_items({'episodes': [
    {'title': 'The Man Trap', 'showtitle': 'Star Trek', 'season': 1, 'episode': 1, 'uniqueid': {}},
    {'title': 'The Man Trap', 'showtitle': 'Other Show', 'season': 1, 'episode': 1, 'uniqueid': {}},
    {'title': 'Charlie X', 'showtitle': 'Star Trek', 'season': 1, 'episode': 2, 'uniqueid': {}},
]}, by_title=True)
assert [e['showtitle'] for e in ep6['episodes']] == ['Star Trek', 'Other Show', 'Star Trek'], ep6
assert [e['episode'] for e in ep6['episodes']] == [1, 1, 2], ep6

EP_RAW = '{"episodes":[{"title":"The Man Trap","year":1966,"season":1,"episode":1,"showtitle":"Star Trek","uniqueid":{"imdb":"tt0060028"}}]}'
ep_item = ai._parse(EP_RAW)['episodes'][0]
assert ep_item['season'] == 1 and ep_item['episode'] == 1 and ep_item['showtitle'] == 'Star Trek' and ep_item['year'] == 1966
assert ep_item['uniqueid'] == {'imdb': 'tt0060028'}

from contextlib import contextmanager  # noqa: E402


assert default_mod.redact('Authorization: Bearer sk-or-v1-abc123-XYZ_-/secret') == 'Authorization: Bearer ***'
assert default_mod.redact("{'Authorization': 'Bearer sk-abcd'}") == "{'Authorization': 'Bearer ***'}"
assert default_mod.redact("{'trakt-api-key': 'a1b2c3d4e5'}") == "{'trakt-api-key': '***'}"
assert default_mod.redact('trakt-api-key=a1b2c3d4e5') == 'trakt-api-key=***'
assert default_mod.redact('plain text here') == 'plain text here'


class FakeCache:
    def __init__(self):
        self.data = {}
    def get(self, key, checksum='', json_data=False):
        return self.data.get(key)
    def set(self, key, value, checksum='', life=None, json_data=False):
        self.data[key] = value


or2 = openrouter.OpenRouter.__new__(openrouter.OpenRouter)
or2.cache = FakeCache()
or2.name = 'OpenRouter'
or2.logo = 'icon'
or2._select({'id': 'x', 'name': 'P', 'prompt': 'q'})
sel_key = 'plugin.program.smartplaylist.generator.OpenRouter'
assert or2.cache.data[sel_key] == [{'name': 'P', 'id': 'x', 'icon': 'icon'}], or2.cache.data[sel_key]
or2._select({'id': 'x', 'name': 'P', 'prompt': 'q'})
or2._select({'id': 'y', 'name': 'Q', 'prompt': 'r'})
assert len(or2.cache.data[sel_key]) == 2, or2.cache.data[sel_key]

import xsp as xsp_mod  # noqa: E402

xw = xsp_mod.XSP.__new__(xsp_mod.XSP)
xw._manifest = {}
xw.cache = FakeCache()
P = 'C:/pl/Star Trek - Movies.xsp'
assert xw._unique_path(P, 'Trakt.30159960') == P
assert xw._unique_path(P, 'OpenRouter.uuid') == 'C:/pl/Star Trek - Movies - 2.xsp'
assert xw._unique_path(P, 'Trakt.30159960') == P, 'same list rebuild must keep its file'
assert xw._unique_path(P, 'OpenRouter.uuid2') == 'C:/pl/Star Trek - Movies - 3.xsp'
assert xw.cache.data['xsp.manifest'][P] == 'Trakt.30159960'

written = []
xw.kodi = types.SimpleNamespace(hasPseudoTV=False, notificationDialog=lambda *a: None)
xw._write = lambda root, path, list_name, pretty_print: written.append((root, path, list_name))
MOVIES = [{'title': 'B', 'year': 2000}, {'title': 'A', 'year': 1980}, {'title': 'C', 'year': 2010}]
xw.create('Order', {'movies': MOVIES}, uid='x')
root, path, _ = written[-1]
assert os.path.basename(path) == 'Order - Movies.xsp', path
assert [v.text for v in root.findall('rule/value')] == ['B', 'A', 'C'], 'API order must be preserved'


class RunModule:
    def __init__(self):
        self.built = 0
    def get_list_items(self, list_id):
        self.built += 1
        return {'movies': [{'title': 'RED', 'uniqueid': {'imdb': 'tt1245526'}}]}


class RunKodi(FakeKodi):
    def __init__(self):
        self.cache = {}
    def isRunning(self, key): return False
    @contextmanager
    def setRunning(self, key): yield
    def getCacheSetting(self, key, checksum=1, json_data=False, revive=True, default=[]):
        if key == 'plugin.program.smartplaylist.generator.Trakt':
            return [{'name': 'My List', 'id': '42'}]
        return self.cache.get(key, default)
    def setCacheSetting(self, key, value, checksum=1, life=None, json_data=False):
        self.cache[key] = value
        return value
    def progressBGDialog(self, percent=0, control=None, message='', header=''):
        return None
    def notificationDialog(self, *a, **k): pass
    def executebuiltin(self, *a, **k): pass


sp2 = default_mod.SPGenerator.__new__(default_mod.SPGenerator)
sp2.kodi = RunKodi()
sp2.xsp = types.SimpleNamespace(create=lambda *a, **k: None)
sp2.modules = {'Trakt': RunModule()}
sp2.dia = None
sp2.pct = 0
sp2.msg = ''
sp2.cntpct = 0
sp2.cnt = 0
sp2.tot = 0
default_mod.REAL_SETTINGS.getSettingBool = lambda k: True
default_mod.REAL_SETTINGS.getSettingInt = lambda k: 1
default_mod.REAL_SETTINGS.getSetting = lambda k: 'false'
default_mod.REAL_SETTINGS.setSetting = lambda *a: None

sp2.run('Build_Trakt_auto')
assert sp2.modules['Trakt'].built == 1
assert 'plugin.program.smartplaylist.generator.BuildTime.42' in sp2.kodi.cache
sp2.run('Build_Trakt_auto')
assert sp2.modules['Trakt'].built == 1, 'auto build should skip when recently built'
sp2.run('Build_Trakt')
assert sp2.modules['Trakt'].built == 2, 'manual build should always rebuild'

orig_listdir = getattr(sys.modules['xbmcvfs'], 'listdir', None)
def empty_listdir(path):
    return [], []
sys.modules['xbmcvfs'].listdir = empty_listdir
try:
    sp2.run('Build_Trakt_auto')
finally:
    if orig_listdir is None:
        del sys.modules['xbmcvfs'].listdir
    else:
        sys.modules['xbmcvfs'].listdir = orig_listdir
assert sp2.modules['Trakt'].built == 3, 'missing xsp files must force an auto rebuild'

RESP['/chat/completions'] = FakeResp(json.dumps({'choices': [
    {'message': {'content': '{"name":"Sci-Fi Marathon","prompt":"sci-fi movies from the 2010s, random order"}'}}]}).encode())
or3 = openrouter.OpenRouter.__new__(openrouter.OpenRouter)
or3.log = lambda *a, **k: None
or3.cache = FakeCache()
fixed = or3._proofread('sci fi', 'sci fi movies random order')
assert fixed == {'name': 'Sci-Fi Marathon', 'prompt': 'sci-fi movies from the 2010s, random order'}, fixed
RESP['/chat/completions'] = FakeResp(json.dumps({'choices': [{'message': {'content': 'no json'}}]}).encode())
assert or3._proofread('x', 'y') is None

or4 = openrouter.OpenRouter.__new__(openrouter.OpenRouter)
or4.log = lambda *a, **k: None
or4.cache = FakeCache()
chain = or4._model_chain()
assert chain[0] == 'false', chain
assert chain[1] == 'cohere/north-mini-code:free', chain
assert len(chain) == len(set(chain))
RESP.pop('/chat/completions', None)
RESP['cohere/north-mini-code:free'] = FakeResp(json.dumps(
    {'choices': [{'message': {'content': '{"movies":[{"title":"RED","uniqueid":{}}]}'}}]}).encode())
data = or4._chat([{'role': 'user', 'content': 'x'}])
assert data == {'movies': [{'title': 'RED', 'uniqueid': {}}]}, data

or5 = openrouter.OpenRouter.__new__(openrouter.OpenRouter)
or5.log = lambda *a, **k: None
or5.cache = FakeCache()
MODELS_PAYLOAD = {'data': [
    {'id': 'a/model:free', 'name': 'A Free', 'architecture': {'output_modalities': ['text']}, 'pricing': {'prompt': '0', 'completion': '0'}},
    {'id': 'b/paid', 'name': 'B Paid', 'architecture': {'output_modalities': ['text']}, 'pricing': {'prompt': '1', 'completion': '1'}},
    {'id': 'c/image', 'name': 'C Image', 'architecture': {'output_modalities': ['image']}, 'pricing': {'prompt': '0', 'completion': '0'}},
    {'id': 'd/byok:free', 'name': 'D BYOK', 'architecture': {'output_modalities': ['text']}, 'pricing': {'prompt': '0', 'completion': '0'}, 'endpoints': [{'is_byok': True, 'is_provider_allowlisted': False}]},
    {'id': 'e/byok-paid', 'name': 'E BYOK Paid', 'architecture': {'output_modalities': ['text']}, 'pricing': {'prompt': '1', 'completion': '1'}, 'endpoints': [{'is_byok': True, 'is_provider_allowlisted': False}]},
]}
RESP['/api/v1/models'] = FakeResp(json.dumps(MODELS_PAYLOAD).encode())
assert or5._free_models() == ['a/model:free', 'd/byok:free'], or5._free_models()
assert or5.cache.data['openrouter.free_models'] == ['a/model:free', 'd/byok:free']

or6 = openrouter.OpenRouter.__new__(openrouter.OpenRouter)
calls = []
orig_exec = sys.modules['xbmc'].executebuiltin
def fake_exec(cmd, *a, **k):
    calls.append(cmd)
sys.modules['xbmc'].executebuiltin = fake_exec
try:
    or6._build()
finally:
    sys.modules['xbmc'].executebuiltin = orig_exec
assert calls and 'Build_OpenRouter' in calls[0], calls

print('test_smartplaylist OK')
