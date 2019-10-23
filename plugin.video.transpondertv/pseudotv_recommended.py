import sys, xbmc, xbmcgui, xbmcaddon, json
ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
ADDON_NAME = xbmcaddon.Addon().getAddonInfo('name')
ADDON_DESC = xbmcaddon.Addon().getAddonInfo('description')
ICON = xbmcaddon.Addon().getAddonInfo('icon')
asset = [{'type':'network','logo':ICON,'path':'plugin://%s/?mode=2&name=Lineup'%(ADDON_ID),'label':'%s LiveTV'%(ADDON_NAME),'description':'LiveTV from %s'%(ADDON_NAME)}]
xbmcgui.Window(10000).setProperty('PseudoTV_Recommend.%s'%(ADDON_ID), json.dumps(asset))
sys.exit()

####### README #######
# type: 
#       file = single item
#       directory = single folder containing links (recursive).
#       browse = special case, seek example online.
#       network = special case, seek example online.
