#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of PlutoTV.
#
# PlutoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PlutoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Channels DVR.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

#entrypoint
import sys
from resources.lib.plutotv import *

class Context:    
    def __init__(self, sysARG=sys.argv):
        log('Context: __init__, sysARG = ' + str(sysARG))
        self.sysARG = sysARG
        
        
    def run(self): 
        params  = json.loads(urllib.parse.unquote(self.sysARG[1]))
        log('Context: run, param = %s'%(params))
        mode   = (params.get("mode",'')     or None)
        chname = (params.get("chname",'')   or '')
        chnum  = int(params.get("chnum",'') or '-1')
        if mode == None : return 
        if mode == 'add': addFavorite(chname,chnum)
        if mode == 'del': delFavorite(chname,chnum)
        
if __name__ == '__main__': Context(sys.argv).run()