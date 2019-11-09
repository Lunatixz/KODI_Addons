import sys, xbmc, xbmcgui, xbmcaddon, json
ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
ICON = xbmcaddon.Addon().getAddonInfo('icon')
asset = [{'type':'directory','logo':ICON,'path':'plugin://plugin.video.uncrate/?mode=1&name=Latest&url=http%3a%2f%2fwww.uncrate.com%2ftv','label':'Latest from Uncrate','description':'Latest videos from Uncrate'},
         {'type':'directory','logo':ICON,'path':'plugin://plugin.video.uncrate/?mode=1&name=Random&url=http%3a%2f%2fwww.uncrate.com%2ftv%2frandom','label':'Random Videos from Uncrate','description':'Random videos from Uncrate'}]
xbmcgui.Window(10000).setProperty('PseudoTV_Recommend.%s'%(ADDON_ID), json.dumps(asset))
sys.exit()

####### README #######
# type: 
#       file = single item
#       directory = single folder containing links (recursive).
#       browse = special case, seek example online.
#       network = special case, seek example online.
