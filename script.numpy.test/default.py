import sys, xbmc, xbmcgui, xbmcaddon, traceback

REAL_SETTINGS  = xbmcaddon.Addon()
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
    
def log(msg, level=xbmc.LOGERROR):
    msg = '%s: %s, %s'%(ADDON_NAME,msg,traceback.format_exc())
    xbmc.log(msg,level)

def text(msg):
    xbmcgui.Dialog().textviewer(ADDON_NAME, msg, usemono=True)
    
try:
    import numpy as np 
    msg =  "NumPy version %s \n"%(np.__version__)
    relaxed_strides = np.ones((10, 1), order="C").flags.f_contiguous
    msg += "NumPy relaxed strides checking option: %s"%(relaxed_strides)
    text(msg)
except Exception as e: 
    log(str(e), xbmc.LOGERROR)
    text(str(e))