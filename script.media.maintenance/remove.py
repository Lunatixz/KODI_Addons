#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of Media Maintenance.
#
# Media Maintenance is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Media Maintenance is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Media Maintenance.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys
import xbmc
import default

if __name__ == '__main__':
    liz   = sys.listitem
    if liz.getLabel() == xbmc.getInfoLabel('ListItem.Label'):
        info  = liz.getVideoInfoTag()
        dbid  = info.getDbId() if info.getDbId() else liz.getProperty('dbid')
        fpath = xbmc.getInfoLabel('ListItem.FileNameAndPath') #xbmcvfs.translatePath(os.path.join(liz.getPath(),liz.getfilename()))
        selectItem = {"folder":liz.getPath(),"file":fpath,"type":info.getMediaType(),"id":dbid,"label":liz.getLabel(),"showtitle":info.getTVShowTitle(),"episodes":liz.getProperty('TotalEpisodes)')}
        default.MM().removeContent(default.MM().requestFile(fpath,fallback=selectItem),bypass=True)