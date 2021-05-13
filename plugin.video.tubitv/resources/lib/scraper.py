# -*- coding: utf-8 -*-
# KodiAddon (tubitv)
#
from t1mlib import t1mAddon
import re
import urllib.parse
import xbmcplugin
import xbmcgui
import xbmc
import html.parser
import sys
import os
import requests

UNESCAPE = html.parser.HTMLParser().unescape
uqp = urllib.parse.unquote_plus
qp  = urllib.parse.quote_plus

class myAddon(t1mAddon):

  def getAddonMenu(self,url,ilist):
    a = requests.get('https://tubitv.com/oz/containers?isKidsModeEnabled=false&groupStart=0', headers=self.defaultHeaders).json()
    for key,b in a['hash'].items():
        url = b['slug']
        name = b['title']
        thumb = b.get('thumbnail')
        infoList = {'Title': name,
                    'Plot': b.get('description')}
        ilist = self.addMenuItem(name,'GS', ilist, url, thumb, thumb, infoList, isFolder=True)
    ilist = self.addMenuItem(self.localLang(30010),'GM', ilist, 'https://tubitv.com/oz/search/', self.addonIcon, self.addonFanart, infoList, isFolder=True)
    return(ilist)


  def getAddonShows(self,url,ilist):
    if not '/search/' in url:
       try:
           catid = url.rsplit('/',1)[1]
       except:
           catid = url
    else:
       catid = url
    if 'parentId=' in url:
       catid = url.split('/containers/',1)[1]
       catid = catid.split('/',1)[0]


    catid = catid.split('?',1)[0]

    if not url.startswith('http'):
        url = url.split('?',1)[0]
        url = 'https://tubitv.com/oz/containers/%s/content?cursor=0&limit=400&expand=0' % url
    c  = requests.get(url, headers=self.defaultHeaders).json()
    if not url.startswith('https://tubitv.com/oz/search/'):
        a = c['containersHash'][catid]['children']
    else:
        a = c
    for b in a:
           if not catid.startswith('https://tubitv.com/oz/search/'):
                d = c['contents'].get(b)
                if d is None:
                    d = c['containersHash'][b]
                b = d
           infoList={}
           infoList['Plot']  = b.get('description')
           infoList['Year']  = b.get('year')
           infoList['duration'] = b.get('duration')
           infoList['cast'] = b.get('actors',[])
           genres = b.get('tags',[])
           genre = ''
           for g in genres:
              if genre != '':
                  genre = ''.join([genre,' / '])
              genre = ''.join([genre, g])
           infoList['genre'] = genre
           directors = b.get('directors',[])
           if len(directors) > 0:
               infoList['director'] = directors[0]
           mpaa = b.get('ratings')
           if len(mpaa) > 0:
               infoList['MPAA'] = mpaa[0].get('value')
           url = b['id']
           if b.get('backgrounds') != [] and not (b.get('backgrounds') is None):
               fanart = b['backgrounds'][0]
               if not fanart.startswith('http'):
                   fanart = 'https:'+fanart
           else:
               fanart = self.addonFanart
           contextMenu = [('Add Movie To Library','RunPlugin(%s?mode=AM&url=%s)' % (sys.argv[0], url))]

           if b['type'] == 's':
              mode = 'GE'
              name = b['title'] + ' (Series)'
              infoList['Title'] = name
              infoList['mediatype'] = 'tvshow'
              img = b.get('posterarts')
              if not img is None:
                  img = img[0]
                  if not img.startswith('http'):
                      img = 'https:'+img
              else:
                  img = b.get('thumbnail')
                  mode = 'GS'
                  url = catid+'/'+url
              contextMenu = [('Add Show To Library','RunPlugin(%s?mode=AS&url=%s)' % (sys.argv[0], url))]
              ilist = self.addMenuItem(name, mode, ilist, url, img, fanart, infoList, isFolder=True, cm=contextMenu)
           else:
              mode = 'GV'
              folderType = False
              name = b['title']
              infoList['Title'] = name
              infoList['mediatype'] = 'movie'
              img = b.get('posterarts')
              if not img is None:
                  img = img[0]
                  if not img.startswith('http'):
                      img = 'https:'+img
              else:
                  img = b.get('thumbnail')
                  mode = 'GS'
                  url = 'https://tubitv.com/oz/containers/%s/content?parentId=%s&cursor=0&limit=50&expand=0' % (url, catid)
                  folderType = True
              ilist = self.addMenuItem(name, mode, ilist, url, img, fanart, infoList, isFolder=folderType, cm=contextMenu)
    return(ilist)

  def getAddonEpisodes(self,url,ilist):
     url = 'https://tubitv.com/oz/videos/0%s/content' % url
     a = requests.get(url, headers=self.defaultHeaders).json()
     sname  = xbmc.getInfoLabel('ListItem.Title')
     for b in a["children"]:
      for c in b["children"]:
       infoList = {}
       name = c.get("title")
       img  = c.get("thumbnails")
       img = img[0]
       url = c.get("id")
       if c['backgrounds'] != []:
           fanart = c['backgrounds'][0]
           if not fanart.startswith('http'):
               fanart = 'https:'+fanart
       else:
           fanart = None

       z = re.compile('S(..)\:E(..) ').search(name)
       if z is not None:
           season, episode = z.groups()
           title = name.split(':',1)[1].split(' ',1)[1].strip(' \t-')
       else:
           season, episode, title = [0, 0, name]
       name = title  
       infoList['TVShowTitle']   = sname
       infoList['Title']    = title
       infoList['Season']   = season
       infoList['Episode']  = episode
       infoList['Plot']     = c.get("description")
       infoList['cast'] = c.get('actors',[])
       mpaa = c.get('ratings')
       if len(mpaa) > 0: infoList['MPAA'] = mpaa[0].get('value')
       infoList["duration"] = c.get("duration")
       infoList["Year"] = c.get("year")
       infoList['mediatype']= 'episode'
       if not img.startswith('http'):
           img = 'https:'+img
       ilist = self.addMenuItem(name,'GV', ilist, qp(url), img, fanart, infoList, isFolder=False)
     return(ilist)


  def getAddonMovies(self,url,ilist):
     keyb = xbmc.Keyboard('', 'Search')
     keyb.doModal()
     if (keyb.isConfirmed()):
        answer = keyb.getText()
        if len(answer) > 0:
           url += uqp(answer)
           ilist = self.getAddonShows(url, ilist)
     return(ilist)


  def doFunctionXXX(self, url):
    func = url[0:2]
    url  = url[2:]
    if func == 'AL':
      name  = xbmc.getInfoLabel('ListItem.Title').replace(':','')
      profile = self.addon.getAddonInfo('profile')
      if '(Series)' in name:
        moviesDir  = xbmc.translatePath(os.path.join(profile,'TV Shows'))
        movieDir  = xbmc.translatePath(os.path.join(moviesDir, name.replace(' (Series)','')))
        if not os.path.isdir(movieDir):
           os.makedirs(movieDir)

        url = 'https://tubitv.com/oz/videos/0%s/content' % url
        a = requests.get(url, headers=self.defaultHeaders).json()
        for b in a["children"]:
           for c in b["children"]:
             name = c.get("title")
             name = name+' '
             xurl = c.get("id")
             z = re.compile('S(..)\:E(..) ').search(name)
             if z is None: 
                 continue
             season, episode = z.groups()
             se = 'S%sE%s' % (season, episode)
             strmFile = xbmc.translatePath(os.path.join(movieDir, se+'.strm'))
             with open(strmFile, 'w') as outfile:
                outfile.write('%s?mode=GV&url=%s' %(sys.argv[0], qp(xurl)))
      else:
        moviesDir  = xbmc.translatePath(os.path.join(profile,'Movies'))
        movieDir  = xbmc.translatePath(os.path.join(moviesDir, name))
        if not os.path.isdir(movieDir):
           os.makedirs(movieDir)
        strmFile = xbmc.translatePath(os.path.join(movieDir, name+'.strm'))
        with open(strmFile, 'w') as outfile:
            outfile.write('%s?mode=GV&url=%s' %(sys.argv[0], qp(url)))
    json_cmd = '{"jsonrpc":"2.0","method":"VideoLibrary.Scan", "params": {"directory":"%s/"},"id":1}' % movieDir.replace('\\','/')
    jsonRespond = xbmc.executeJSONRPC(json_cmd)

  def getAddonVideo(self,url):
   url = uqp(url)
   subtitles = []
   a = requests.get('https://tubitv.com/oz/videos/%s/content' % url, headers=self.defaultHeaders).json()
   url = a.get("url", None)
   if url != None:
       subs = a["subtitles"]
       for sub in subs:
           subtitles.append(sub["url"])
       liz = xbmcgui.ListItem(path=url, offscreen=True)
       liz.setSubtitles(subtitles)
       xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
