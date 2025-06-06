#   Copyright (C) 2025 Lunatixz
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

import re, os, sys, time, json
import platform, subprocess, textwrap, requests

try:
    import multiprocessing
    cpu_count   = multiprocessing.cpu_count()
    ENABLE_POOL = True
except:
    ENABLE_POOL = False
    cpu_count   = os.cpu_count()

from resources.lib import pystone
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

LIMIT = 45
LINE  = 90
LOOP  = 50000

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
try:
    system_info   = platform.uname()
    sys_processor = system_info.processor 
    sys_machine   = system_info.machine
    sys_system    = system_info.system
    sys_release   = system_info.release
    sys_version   = system_info.version
except:
    system_info   = None
    sys_processor = None
    sys_machine   = None
    sys_system    = None
    sys_release   = None
    sys_version   = None

cpu_name              = (sys_processor or platform.processor())
os_name               = (sys_system    or platform.system()) # Get the OS name
machine_arch          = (sys_machine   or platform.machine())# Get the machine architecture
os_version            = (sys_release   or platform.release())# Get the OS version
platform_version      = (sys_version   or platform.version())
platform_info         = platform.platform()
python_implementation = platform.python_implementation()# Get the Python implementation
python_version        = platform.python_version()# Get the Python version
architecture          = ' '.join(platform.architecture()) if isinstance(platform.architecture(),(list,tuple)) else platform.architecture()
kodi_info             = xbmc.getInfoLabel('System.BuildVersion')
kodi_mem_free         = xbmc.getInfoLabel('System.FreeMemory')
kodi_mem_total        = xbmc.getInfoLabel('System.Memory(total)')
is_arm                = True if 'arm' in machine_arch.lower() else False

def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
        
def isScanning():
    return (xbmc.getCondVisibility('Library.IsScanningVideo') & xbmc.getCondVisibility('Library.IsScanningMusic'))
       
def isPlaying():
    return xbmc.getCondVisibility('Player.Playing')
       
def _repeat(length=LIMIT, fill='█'):
   length = int(round(length))
   return (fill * int((length/len(fill))+1))[:length]
   
def replace_with_k(number_string):
    number = int(number_string)
    if number >= 1000: return f"{number // 1000}k"
    else:              return number_string
    
def progress_bar(iteration, total, length=LIMIT, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    if filled_length > 10: bar_with_percent = f"{bar[:length//2 - len(percent)//2]}{percent}%{bar[length//2 - len(percent)//2 + len(percent):]}"
    else:                  bar_with_percent = bar
    return f'|{bar_with_percent[:length]}|'

def score_bar(stones, pyseed, pydur, avg, length=LIMIT):
    def _insert(value, score):
        fill   = _repeat(length-4)
        if value >= 100: value = 90
        value  = (100-value)
        sindex = int(length * ((length / 100) * value / length))
        colors = ['green','yellow','orange','red','dimgrey']
        chunks = textwrap.wrap(fill[:sindex - len(score)//2] + score + fill[sindex + len(score)//2:], length//4)
        bars   = ''.join([LANGUAGE(30004)%(colors.pop(0),chunk) for chunk in chunks if len(colors) > 0 ])
        return f'|{bars}| %s secs'%("{0:.2f}".format(pydur))
    return _insert(avg, f'| {stones} |')

def get_load(core):
    if ENABLE_POOL:
        load = float(xbmc.getInfoLabel('System.CoreUsage(%i)'%(core)).replace('Not available','0'))
        if int(load) > 0: return load#arm doesn't return core %?
    return float(xbmc.getInfoLabel('System.CpuUsage').replace('Not available','0').replace('%',''))

def get_info():   
    def __running():
        return json.loads(xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"addons://running/"},"id":ADDON_ID}))).get("result",{}).get("limits",{}).get("total",0)
    
    def __rpi():
        try: # Attempt to retrieve CPU frequency (Pi only, from /proc/device-tree/model)
            with open("/proc/device-tree/model", "r") as f:
                return f.read().strip()
        except Exception as e: log("__rpi, failed! %s"%(e), xbmc.LOGERROR)
        return ''
 
    def __cpu():
        try:
            if is_arm or "linux" in os_name.lower():# Attempt to retrieve CPU frequency (Linux only, from /proc/cpuinfo)
                with open("/proc/cpuinfo", "r") as f:
                    cpu_info = re.search(r'model name\s*:\s*(.+)', f.read()).group(1).strip()
                    if is_arm: return '%s %s'%(cpu_info,__rpi())
                    else:      return cpu_info
            elif "darwin" in os_name.lower():
                return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
            elif "windows" in os_name.lower():
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Hardware\Description\System\CentralProcessor\0")
                cpu_info = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                winreg.CloseKey(key)
                return cpu_info
        except Exception as e: log("__cpu, failed! %s"%(e), xbmc.LOGERROR)
        return cpu_name
        
    return '[CR]'.join([
                      (f"Processor: [B]{__cpu()}[/B]"),
                      (f"Machine Architecture: [B]{machine_arch} {architecture}[/B]"),
                      (f"Logical CPU Cores (including Hyperthreading if applicable): [B]{cpu_count}[/B]"),
                      (LANGUAGE(30004)%('dimgrey',_repeat(LINE,'_'))),
                      (f"Operating System: [B]{os_name} v.{os_version} ({platform_info})[/B]"),
                      (f"Free Memory: [B]{kodi_mem_free} / {kodi_mem_total}[/B]"),
                      (LANGUAGE(30004)%('dimgrey',_repeat(LINE,'_'))),
                      (f"Kodi Build: [B]{kodi_info}[/B]"),
                      (f"Running Services: [B]{__running()}[/B]"),
                      (LANGUAGE(30004)%('dimgrey',_repeat(LINE,'_'))),
                      (f"Python: [B]{python_implementation} v.{python_version}[/B]"),
                      (f"Benchmark: [B]pystone v.{pystone.__version__}[/B] n={LOOP} | Multiprocessing: [B]Disabled[/B]"),#{{True:"Enabled",False:"Disabled"}[ENABLE_POOL]}
                      (LANGUAGE(30004)%('dimgrey',_repeat(LINE,'_'))),
                      ])
                      
def OKAY(msg, heading=ADDON_NAME,):
    return xbmcgui.Dialog().ok(heading, msg)
        
class TEXTVIEW(xbmcgui.WindowXMLDialog):
    textbox = None
    
    def __init__(self, *args, **kwargs):
        self.head = f'{ADDON_NAME} v.{ADDON_VERSION}'
        self.text = get_info()
        self.url  = None
        if not isScanning() and not isPlaying(): self.doModal()
        else: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (self.head, LANGUAGE(30006), 4000, ICON))
            
    def _updateText(self, txt):
        try:
            self.textbox.setText(txt)
            xbmc.executebuiltin('ActivateWindowAndFocus(WINDOW_DIALOG_TEXT_VIEWER, 3000)')
            xbmc.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
            xbmc.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
        except Exception as e: log("_updateText, failed! %s"%(e), xbmc.LOGERROR)

    def onInit(self):
        try:
            self.getControl(1).setLabel(self.head)
            self.textbox = self.getControl(5)
            self._updateText(self.text)
            self._run([LOOP for i in range(cpu_count)]) #todo multiprocessing? each pass to induvial core.
        except Exception as e:
            log("onInit, failed! %s"%(e), xbmc.LOGERROR)
            if self.url: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (self.head, self.url, 8000, ICON))
            self.close()

    def onClick(self, control_id):
        pass

    def onFocus(self, control_id):
        pass

    def onAction(self, action):
        if action in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK]:
            self.close()

    def _run(self, seeds=[50000]):
        ranks = []
        for i, pyseed in enumerate(seeds):
            prog = progress_bar(i, len(seeds))
            self._updateText(f"{self.text}[CR]{prog}")
            load = int(round(get_load(i)))
            pydur, pystonefloat = pystone.pystones(pyseed)
            ranks.append({'core':i,'seed':pyseed,'duration':pydur,'score':pystonefloat,'load':load})
            if len(seeds) > 1:
                self.text = f'{self.text}[CR]Pass {i+1}{self._rank(int(pystonefloat),pyseed,pydur)} @ {load}%'
                self._updateText(self.text)
        self._updateText(self._score(ranks))

    def _rank(self, stones, pyseed, pydur, maxseed=200000):
        return score_bar(stones,pyseed, pydur,((stones) * 100) // maxseed)

    def _score(self, ranks):
        seeds     = []
        scores    = []
        durations = []
        loads     = []
        for i, rank in enumerate(ranks):
            if "load"     in rank: loads.append(rank["load"])
            if "seed"     in rank: seeds.append(rank["seed"])
            if "score"    in rank: scores.append(rank["score"])
            if "duration" in rank: durations.append(rank["duration"])
            
        rank = self._rank(int(sum(scores) / len(scores)), int(sum(seeds) / len(seeds)), (sum(durations) / len(durations)))
        text = '[CR]'.join([
                          (f"{self.text}[CR]Score {rank} @ {int(sum(loads) / len(loads))}%"),
                          (LANGUAGE(30004)%('dimgrey',_repeat(LINE,'_'))),
                          ])
                          
        post, link = self._post(text)
        exit = '[CR]'.join([
                          (LANGUAGE(30004)%('white',LANGUAGE(30007).format(loop=replace_with_k(str(LOOP)),duration="{0:.2f}".format(sum(durations) / len(durations)),load=int(sum(loads) / len(loads))))),
                          (LANGUAGE(30004)%('white',f"{LANGUAGE(30003)}: [B]{link}[/B]")),
                          (LANGUAGE(30004)%('dimgrey',LANGUAGE(30005))),
                          ])
                          
        return f"{text}[CR]{exit}"
             
    def _post(self, data):
        def __clean(text):
            text = text.replace('[CR]','\n')
            text = re.sub(r'\[COLOR=(.+?)\]', '', text)
            text = re.sub(r'\[/COLOR\]', '', text)
            text = text.replace("[B]",'').replace("[/B]",'')
            text = text.replace("[I]",'').replace("[/I]",'')
            return text
        try:
            session = requests.Session()
            response = session.post('https://paste.kodi.tv/' + 'documents', data=__clean('%s[CR]%s'%(self.head,data)).encode('utf-8'), headers={'User-Agent':'%s: %s'%(ADDON_ID, ADDON_VERSION)})
            if 'key' in response.json(): 
                url = 'https://paste.kodi.tv/' + response.json()['key']
                log('_post, successful url = %s'%(url))
                return True, url
            elif 'message' in response.json():
                log('_post, upload failed, paste may be too large')
                return False, response.json()['message']
            else:
                log('_post failed! %s'%response.text)
                return False, LANGUAGE(30009)
        except:
            log('_post, unable to retrieve the paste url')
            return False, LANGUAGE(30010)
              