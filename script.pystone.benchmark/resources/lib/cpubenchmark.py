#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of CPU Benchmark.
#
# CPU Benchmark is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CPU Benchmark is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CPU Benchmark.  If not, see <http://www.gnu.org/licenses/>.
# https://pybenchmarks.org/u64q/performance.php?test=pystone

import re, os, sys, time, platform, subprocess, textwrap

try:
    import multiprocessing
    cpu_count   = multiprocessing.cpu_count()
    ENABLE_POOL = True
except:
    ENABLE_POOL = False
    cpu_count   = os.cpu_count()

from resources.lib import pystone
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

LOOP = 50000

# Plugin Info
ADDON_ID       = 'script.pystone.benchmark'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

# System Info
cpu_count             = os.cpu_count()
cpu_name              = platform.processor()
os_name               = platform.system() # Get the OS name
os_version            = platform.release()# Get the OS version
platform_info         = platform.platform()# Get a general platform identifier
python_implementation = platform.python_implementation()# Get the Python implementation
python_version        = platform.python_version()# Get the Python version
machine_arch          = platform.machine()# Get the machine architecture
system_info           = platform.uname()
architecture          = platform.architecture()
kodi_info             = xbmc.getInfoLabel('System.BuildVersion')

def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    
def replace_with_k(number_string):
    number = int(number_string)
    if number >= 1000: return f"{number // 1000}k"
    else:              return number_string
    
def progress_bar(iteration, total, length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    if filled_length > 10: bar_with_percent = f"{bar[:length//2 - len(percent)//2]}{percent}%{bar[length//2 - len(percent)//2 + len(percent):]}"
    else:                  bar_with_percent = bar
    return f'|{bar_with_percent}|'

def score_bar(stones, pyseed, pydur, avg, length=50):
    def _repeat(length=50, fill='█'):
       length = int(round(length))
       return (fill * int((length/len(fill))+1))[:length]
       
    def _insert(value, score):
        fill   = _repeat(length-4)
        if value >= 100: value = 90
        value  = (100-value)
        sindex = int(length * ((length / 100) * value / length))
        colors = ['green','yellow','orange','red','dimgrey','dimgrey']
        chunks = textwrap.wrap(fill[:sindex - len(score)//2] + score + fill[sindex + len(score)//2:], length//4)
        return '| %s | %s in %ss'%(''.join(['[COLOR=%s]%s[/COLOR]'%(colors.pop(0),chunk) for chunk in chunks if len(colors) > 0 ]),replace_with_k(pyseed),"{0:.2f}".format(pydur))
    return _insert(avg, f'| {stones} |')

def get_info():    
    def __cpu():
        try:
            if system_info.system == "Linux":
                try: # Attempt to retrieve CPU frequency (Pi only, from /proc/device-tree/model)
                    with open("/proc/device-tree/model", "r") as f:
                        return f.read().strip()  # Remove leading/trailing whitespace
                except:  # Attempt to retrieve CPU frequency (Linux only, from /proc/cpuinfo)
                    try:
                        with open("/proc/cpuinfo", "r") as f:
                            return re.search(r'model name\s*:\s*(.+)', f.read()).group(1).strip()
                    except: pass
            elif system_info.system == "Darwin":
                return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
            elif system_info.system == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Hardware\Description\System\CentralProcessor\0")
                cpu_info = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                winreg.CloseKey(key)
                return cpu_info
        except Exception as e: 
            log("__cpu, failed! %s"%(e), xbmc.LOGERROR)
            return "Unknown"

    return '[CR]'.join([
                      (f"Processor: [B]{__cpu() or system_info.processor or cpu_name} MHz[/B]"),
                      (f"Machine Architecture: [B]{(system_info.machine or machine_arch)} {' '.join(architecture)}[/B]"),
                      (f"Logical CPU Cores (including Hyperthreading if applicable): [B]{cpu_count}[/B]"),
                      ('%s')%('_'*75),
                      (f"Operating System: [B]{(system_info.system or os_name)} v.{os_version} ({platform_info})[/B]"),
                      (f"Kodi Build: [B]{kodi_info}[/B]"),
                      (f"Python Implementation: [B]{python_implementation} v.{python_version}[/B]"),
                      ('%s')%('_'*75),
                      ])

class TEXTVIEW(xbmcgui.WindowXMLDialog):
    textbox = None
    
    def __init__(self, *args, **kwargs):
        self.head = kwargs.get('head')
        self.text = kwargs.get('text')
        self.doModal()
            
    def _updateText(self, txt):
        try:
            self.textbox.setText(txt)
            self.textbox.scroll()
            xbmc.executebuiltin('Action(down)')
        except: pass

    def onInit(self):
        self.getControl(1).setLabel(self.head)
        self.textbox = self.getControl(5)
        self._updateText(self.text)
        self._run([LOOP for i in range(cpu_count)])

    def onClick(self, control_id):
        pass

    def onFocus(self, control_id):
        pass

    def onAction(self, action):
        if action in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK]:
            self.close()

    def _run(self, seeds=[50000]):
        ranks      = []
        self.text  = '%s[CR]%s [B]pystone v.%s[/B]'%(self.text,'Benchmark:',pystone.__version__)
        self._updateText(self.text)
        for i, pyseed in enumerate(seeds):
            prog = progress_bar(i, len(seeds))
            self._updateText("%s[CR]%s"%(self.text,prog))
            pydur, pystonefloat = pystone.pystones(pyseed)
            ranks.append({'core':i,'seed':pyseed,'duration':pydur,'score':pystonefloat})
            if len(seeds) > 1:
                self.text = '%s[CR]Pass %s%s'%(self.text,i+1,self._rank(int(pystonefloat),pyseed,pydur))
                self._updateText(self.text)
        self._updateText(self._total(ranks))

    def _rank(self, stones, pyseed, pydur, maxseed=200000):
        return score_bar(stones,pyseed, pydur,((stones) * 100) // maxseed)

    def _total(self, ranks):
        durations = []
        scores    = []
        seeds     = []
        for i, rank in enumerate(ranks):
            if "duration" in rank: durations.append(rank["duration"])
            if "score"    in rank: scores.append(rank["score"])
            if "seed"     in rank: seeds.append(rank["seed"])
        return '%s[CR]%s %s[CR]%s'%(self.text,'Score',self._rank(int(sum(scores) / len(scores)), int(sum(seeds) / len(seeds)), (sum(durations) / len(durations))),LANGUAGE(30004)%('dimgrey',LANGUAGE(30005)))

class CPU():
    def run(self):
        TEXTVIEW("DialogTextViewer.xml", os.getcwd(), "Default", head='%s v.%s'%(ADDON_NAME,ADDON_VERSION), text=get_info())
        
        
        