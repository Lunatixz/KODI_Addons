#   Copyright (C) 2021 Lunatixz
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
from default import *

if __name__ == '__main__':
    liz = sys.listitem
    print(liz.getVideoInfoTag().getProperty('type'))
    if liz.getProperty('type') in ['tvshow','season','episode'] and len(liz.getProperty('showtitle')) > 0:
        with busy_dialog():
            mediaMaint = MM()
            TVShowList = mediaMaint.getUserList()
            if (liz.getProperty('year') or 0) > 0: label = '%s (%d)'%(liz.getProperty('showtitle'),liz.getProperty('year'))
            else: label = liz.getProperty('showtitle')
            TVShowList.append({'type':'series','label':label,'title':liz.getProperty('showtitle'),'year':liz.getProperty('year'),'dbid':liz.getProperty('tvshowid')})
            mediaMaint.setUserList(TVShowList)
        notificationDialog(default.LANGUAGE(30043)%(liz.getProperty('showtitle')))