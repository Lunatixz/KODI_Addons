import traceback, os, sys
from six.moves import urllib
from kodi_six  import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

# Plugin Info
ADDON_ID            = 'plugin.video.seektest'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE            = REAL_SETTINGS.getLocalizedString
VIDEO               = os.path.join(ADDON_PATH,'test.mp4')

def log(msg, level=xbmc.LOGDEBUG):
    if   level == xbmc.LOGERROR: msg = '%s, %s'%((msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)

class TEST():
    def __init__(self, sysARG=sys.argv):
        log('__init__, sysARG = ' + str(sysARG))
        self.sysARG = sysARG
        
    def playChannel(self):
        progress = 15 #sec
        runtime  = 1  #min
        liz = xbmcgui.ListItem()
        liz.setPath(VIDEO)
        liz.setProperty('totaltime'  , str((runtime * 60)))
        liz.setProperty('resumetime' , str(progress))
        liz.setProperty('startoffset', str(progress))
        liz.setProperty("IsPlayable" ,"true")
        log('playChannel setting resume seek, video = %s, totaltime = %s, startoffset = %s'%(VIDEO,(runtime * 60),progress))
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)
        
        
    def getParams(self):
        return dict(urllib.parse.parse_qsl(self.sysARG[2][1:]))
        
    def run(self): 
        params  = self.getParams()
        log('run, params = %s'%(params))
        url = (params.get("url",'') or None)
        
        if url is None:
            name = '15s seek test in 60s video, resume at 45s'
            liz=xbmcgui.ListItem(name)
            liz.setProperty("IsPlayable" ,"true")
            liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
            log('addLink, name = %s'%(name))
            u=self.sysARG[0]+"?url=%s"%(VIDEO)
            xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,totalItems=1)
            xbmcplugin.endOfDirectory(int(self.sysARG[1]), cacheToDisc=True)
        else: 
            self.playChannel()
            
if __name__ == '__main__':  
    TEST(sys.argv).run()