#   Copyright (C) 2025 Lunatixz
#
#
# This file is part of Kodi PowerToys
#
# Kodi PowerToys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Kodi PowerToys is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kodi PowerToys.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-
from globals            import *
from collections        import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, TimeoutError

try:
    import multiprocessing
    cpu_count   = multiprocessing.cpu_count()
    ENABLE_POOL = False #True force disable multiproc. until monkeypatch/wrapper to fix pickling error. 
except:
    ENABLE_POOL = False
    cpu_count   = os.cpu_count()

class ExecutorPool:
    def __init__(self):
        self.CPUCount = cpu_count
        if ENABLE_POOL: self.pool = ProcessPoolExecutor
        else:           self.pool = ThreadPoolExecutor
        self.log(f"__init__, multiprocessing = {ENABLE_POOL}, CORES = {self.CPUCount}, THREADS = {self._calculate_thread_count()}")


    def _calculate_thread_count(self):
        if ENABLE_POOL: return self.CPUCount
        else:           return int(os.getenv('THREAD_COUNT', self.CPUCount * 2))
            
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def executor(self, func, timeout=None, *args, **kwargs):
        self.log("executor, func = %s, timeout = %s"%(func.__name__,timeout))
        with self.pool(self._calculate_thread_count()) as executor:
            try: return executor.submit(func, *args, **kwargs).result(timeout)
            except Exception as e: self.log("executor, func = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,e,args,kwargs), xbmc.LOGERROR)


    def executors(self, func, items=[], *args, **kwargs):
        self.log("executors, func = %s, items = %s"%(func.__name__,len(items)))
        with self.pool(self._calculate_thread_count()) as executor:
            try: return list(executor.map(wrapped_partial(func, *args, **kwargs), items))
            except Exception as e: self.log("executors, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)


    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try: return [wrapped_partial(func, *args, **kwargs)(i) for i in items]
        except Exception as e: self.log("generator, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)


class LlNode:
    def __init__(self, package: tuple, priority: int=0, timer: int=0):
        self.prev      = None
        self.next      = None
        self.package   = package
        self.priority  = priority
        self.time      = timer


class CustomQueue:
    pool = ExecutorPool()
    
    def __init__(self, fifo: bool=False, lifo: bool=False, priority: bool=False, delay: bool=False, timer: bool=False, service=None):
        self.log("__init__, fifo = %s, lifo = %s, priority = %s, delay = %s, timer = %s"%(fifo, lifo, priority, delay, timer))
        self.isRunning = False
        self.service   = service
        self.fifo      = fifo
        self.lifo      = lifo
        self.priority  = priority
        self.delay     = delay
        self.timer     = timer
        self.head      = None
        self.tail      = None
        self.min_heap  = []
        self.qsize     = 0
        self.nodes     = set()
        self.itemCount = defaultdict(int)
        self.popThread = Thread(target=self._start)
        self.executor  = True
 
 
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _clear(self):
        self.nodes     = set()
        self.head      = None
        self.tail      = None
        self.min_heap  = []
        self.itemCount = defaultdict(int)

        
    def _run(self):
        self.log("_run")
        if self.popThread.is_alive():
            if hasattr(self.popThread, 'cancel'): self.popThread.cancel()
            try: self.popThread.join()
            except: pass
        self.popThread = Thread(target=self._start)
        self.popThread.daemon = True
        self.popThread.start()


    def _wait(self, package):
        self.log(f"_wait, func = {package[0].__name__}")
        self._exe(package[0],*package[1],**package[2])
           

    def _exe(self, func, *args, **kwargs):
        self.log(f"_exe, func = {func.__name__}, executor = {self.executor}")
        try:
            if    self.executor: self.pool.executor(func, None, *args, **kwargs)
            else: Thread(target=func, args=args, kwargs=kwargs).start()
        except Exception as e:
            self.log(f"_exe, func = {func.__name__} failed! {e}\nargs = {args}, kwargs = {kwargs}", xbmc.LOGERROR)
               
               
    def _exists(self, package: tuple, priority: int = 0, timer: int = 0):
        if priority:
            for idx, item in enumerate(self.min_heap):
                epriority,_,epackage = item
                if package == epackage:
                    if priority < epriority:
                        try:
                            self.min_heap.pop(idx)
                            heapq.heapify(self.min_heap)  # Ensure heap property is maintained
                            self.log("_exists, replacing queue: func = %s, priority %s => %s"%(epackage[0].__name__,epriority,priority))
                        except: self.log("_exists, replacing queue: func = %s, idx = %s failed!"%(epackage[0].__name__,idx))
                    else: return True
        elif timer:
            for idx, func in enumerate(self.nodes):
                if func == package[0].__name__: return True
            self.nodes.add(package[0].__name__)
        return False
        
             
    def _push(self, package: tuple, priority: int = 0, delay: int = 0, timer: int = 0):
        if   priority == -1: priority = self.qsize + 1 #lazy FIFO
        elif delay: #lazy timer
            if not timer: timer = time.time()
            timer += delay
        
        if self.priority:
            if not self._exists(package, priority, timer):
                try:
                    self.qsize += 1
                    self.itemCount[priority] += 1
                    self.log(f"_push, func = {package[0].__name__}, priority = {priority}")
                    heapq.heappush(self.min_heap, (priority, self.itemCount[priority], package))
                    if not self.isRunning: self._run()
                except Exception as e:
                    self.log(f"_push, func = {package[0].__name__} failed! {e}", xbmc.LOGFATAL)
        else:
            if timer and self._exists(package, priority, timer): print('%s exists'%(package[0].__name__))
            else:
                node = LlNode(package, priority, timer)
                if self.head:
                    self.tail.next = node
                    node.prev = self.tail
                    self.tail = node
                else:
                    self.head = node
                    self.tail = node
                self.log(f"_push, func = {package[0].__name__}, timer = {timer}")
                if not self.isRunning: self._run()
                

    def _process(self, node, fifo=True):
        package = node.package
        next_node = node.next if fifo else node.prev
        if next_node: next_node.prev = None if fifo else next_node.prev
        if node.prev: node.prev.next = None if fifo else node.prev
        if fifo: self.head = next_node
        else:    self.tail = next_node
        return package
        
        
    def _start(self):
        self.isRunning = True
        while not self.service.monitor.abortRequested():
            if not self.head and not self.priority:
                self.log("_start, The queue is empty!")
                break
            elif self.service.monitor.waitForAbort(0.0001):
                self.log("_start, waitForAbort!")
                break
            elif self.priority:
                if not self.min_heap:
                    self.log("_start, The priority queue is empty!")
                    break
                else:
                    try:
                        priority, _, package = heapq.heappop(self.min_heap)
                        self.qsize -= 1
                        self._exe(package[0],*package[1],**package[2])
                    except Exception as e: self.log("_start, failed! %s"%(e), xbmc.LOGERROR)
            elif self.fifo or self.lifo:
                curr_node = self.head if self.fifo else self.tail
                if curr_node is None: break
                else:
                    try:
                        package = self._process(curr_node, fifo=self.fifo)
                        if self.timer or curr_node.time:
                            if time.time() < curr_node.time: self._push(package, timer=curr_node.time)
                            else:
                                self.nodes.remove((package[0].__name__))
                                self._exe(package[0],*package[1],**package[2])
                        else: self._exe(package[0],*package[1],**package[2])
                    except Exception as e: self.log("_start, failed! %s"%(e), xbmc.LOGERROR)
            else:
                self.log("_start, queue undefined!")
                break
                
        self.isRunning = False
        self.log("_start, finished: shutting down...")