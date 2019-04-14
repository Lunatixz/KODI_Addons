#   Copyright (C) 2019 Lunatixz
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
import sys
import xbmc
import default

if __name__ == '__main__':
    selectItem = {"type":xbmc.getInfoLabel('ListItem.DBTYPE'),"id":xbmc.getInfoLabel('ListItem.DBID'),"label":xbmc.getInfoLabel('ListItem.Label'),"showtitle":xbmc.getInfoLabel('ListItem.TVShowTitle')}
    tvshow = selectItem['showtitle']
    if selectItem['type'] in ['tvshow','season','episode'] and len(tvshow) > 0:
        TVShowList = default.MM().getUserList()
        TVShowList.append(tvshow)
        default.MM().setUserList(TVShowList)
        default.MM().notificationDialog(default.LANGUAGE(30043)%(tvshow))