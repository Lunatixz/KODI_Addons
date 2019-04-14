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
    selectItem = {"folder":xbmc.getInfoLabel('ListItem.Path'),"file":xbmc.getInfoLabel('ListItem.FileNameAndPath'),"type":xbmc.getInfoLabel('ListItem.DBTYPE'),"id":xbmc.getInfoLabel('ListItem.DBID'),"label":xbmc.getInfoLabel('ListItem.Label'),"showtitle":xbmc.getInfoLabel('ListItem.TVShowTitle'),"episodes":xbmc.getInfoLabel('ListItem.Property(TotalEpisodes)')}
    default.MM().removeContent(default.MM().requestFile(xbmc.getInfoLabel('ListItem.FileNameAndPath'),fallback=selectItem),bypass=True)