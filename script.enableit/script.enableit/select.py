#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of Enable it!.
#
# Enable it! is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Enable it! is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Enable it!.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
from globals import *

def selectDialog(label, items, pselect=[-1], uDetails=False):
    select = xbmcgui.Dialog().multiselect(label, items, preselect=pselect, useDetails=uDetails)
    if select: return select
    return None
    
class Select():
    def __init__(self, sysARG):
        self.sysARG = sysARG
        
    def run(self): 
        param = self.sysARG[1]
        if param == None: return
        pselect = [-1]
        items   = {'CONTENTS'      :CONTENTS,
                   'CONTENT_TYPES' :CONTENT_TYPES}[param]
        if param   == 'CONTENTS': 
            try: pselect = list(map(int, REAL_SETTINGS.getSetting('PreSelect_CONTENTS').split('|')))
            except: pass
        elif param == 'CONTENT_TYPES': 
            try: pselect = list(map(int, REAL_SETTINGS.getSetting('PreSelect_CONTENT_TYPES').split('|')))
            except: pass
        select = selectDialog(LANGUAGE(30004),items, pselect=pselect)
        try: sselect = '|'.join(map(str, select))
        except: sselect = ''
        REAL_SETTINGS.setSetting("PreSelect_%s"%(param),sselect)
        REAL_SETTINGS.openSettings()
            
if __name__ == '__main__': Select(sys.argv).run()