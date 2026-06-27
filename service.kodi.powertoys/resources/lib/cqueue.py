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
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, TimeoutError, as_completed

class ExecutorPool:
    def __init__(self, workers=THREAD_WORKERS):
        self._workers  = workers
        self._executor = ThreadPoolExecutor(max_workers=workers)
    
    def __del__(self):
        self.shutdown()

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def isShutdown(self):
        return getattr(self._executor, "_shutdown", False)

    def shutdown(self, wait=False, cancel=True):
        try: 
            self._executor.shutdown(wait=wait, cancel=cancel)
            self.log("shutdown, _executor")
        except Exception: pass
        
    def getTimeout(self):
        try: return int(REAL_SETTINGS.getSetting('API_Timeout') or REAL_SETTINGS.getSetting('Start_Delay') or 15)
        except Exception: return 15

    def getUseExecutor(self):
        value = REAL_SETTINGS.getSetting('Enable_Executor')
        if value == '': return True
        return value.lower() == "true"
            
    def executor(self, func, timeout=None, *args, **kwargs):
        if timeout is None: timeout = self.getTimeout()
        useExecutor = self.getUseExecutor()
        if not useExecutor and xbmc.getCondVisibility('Player.Playing'): useExecutor = True
        if useExecutor:
            if self.isShutdown(): 
                self._executor = ThreadPoolExecutor(max_workers=self._workers)
                
            with timeit(func):
                try:
                    future = self._executor.submit(func, *args, **kwargs)
                    return future.result(timeout=float(timeout) )
                except TimeoutError:
                    self.log(f"executor, func = {func.__name__} timed out after {timeout}s", xbmc.LOGWARNING)
                    future.cancel()
                except Exception as e: 
                    self.log(f"executor, func = {func.__name__} failed! {e}", xbmc.LOGERROR)
        return self.execute(func, *args, **kwargs)

    def execute(self, func, *args, **kwargs):
        try:
            with timeit(func):
                return func(*args, **kwargs)
        except Exception as e: self.log(f"execute, func = {func.__name__} failed! {e}", xbmc.LOGERROR)

    def _wrapped_partial(self, func, *args, **kwargs):
        partial_func = partial(func, *args, **kwargs)
        update_wrapper(partial_func, func)
        return partial_func
        
    def executors(self, func, items=[], timeout=None, *args, **kwargs):
        if timeout is None: timeout = self.getTimeout()
        useExecutor = self.getUseExecutor()
        if not useExecutor and xbmc.getCondVisibility('Player.Playing'): useExecutor = True
        if useExecutor:
            if self.isShutdown(): 
                self._executor = ThreadPoolExecutor(max_workers=self._workers)
                
            with timeit(func):
                futures = {self._executor.submit(self._wrapped_partial(func, *args, **kwargs), i): i for i in items}
                results = []
                for future in as_completed(futures, timeout=float(timeout)):
                    try: results.append(future.result())
                    except Exception as e: self.log(f"executors, func = {func.__name__} failed! {e}", xbmc.LOGERROR)
                if results: return results
        return self.generator(func, items, *args, **kwargs)

    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try:
            with timeit(func):
                results = [self._wrapped_partial(func, *args, **kwargs)(i) for i in items]
                return [r for r in results if r is not None]
        except Exception as e: self.log(f"generator, func = {func.__name__} failed! {e}", xbmc.LOGERROR) 
        return []

@contextmanager
def timeit(method):
    start_time = time.time()
    try: yield
    finally:
        end_time = time.time()
        log('%s timeit => %.2f ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))

def poolit(method):
    @wraps(method)
    def wrapper(items=None, wait=None, *args, **kwargs):
        if wait is None: wait = int(REAL_SETTINGS.getSetting('Start_Delay') or 15)
        monitor = xbmc.Monitor()
        if monitor.abortRequested(): return None
        if items is None: items = []
        execution_state = { 'result': None, 'error': None }
        
        def __worker():
            try:
                if monitor.abortRequested(): return
                execution_state['result'] = ExecutorPool().executors(method, items, wait, *args, **kwargs)
                xbmc.log(f"{method.__qualname__} pool completed on {current_thread().name}", xbmc.LOGINFO)
            except Exception: execution_state['error'] = traceback.format_exc()

        if monitor.abortRequested(): return None
        thread = Thread(target=__worker)
        thread.name = f"{ADDON_ID}.poolit.{method.__qualname__}"
        thread.daemon = True
        thread.start()
        
        xbmc.log(f"{method.__name__} supervisor thread started: {thread.name}", xbmc.LOGDEBUG)
        thread.join(timeout=float(wait))
        if thread.is_alive():
            xbmc.log(f"{method.__name__} pool timed out! Background supervisor abandoned.", xbmc.LOGWARNING)
            return None
        if execution_state['error']:
            xbmc.log(f"{method.__name__} pool failed with errors:\n{execution_state['error']}", xbmc.LOGERROR)
            return None
        return execution_state['result']
    return wrapper
    
class Task(object):
    def __init__(self, func, args=(), kwargs=None, priority=3, execute_at=0):
        self.func         = func
        self.args         = args
        self.kwargs       = kwargs if kwargs is not None else {}
        self.priority     = priority
        self.execute_at   = execute_at
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def __lt__(self, other):
        # Tie-breaker logic (won't be reached if counters are unique, but standard safety)
        return self.priority < other.priority

class CustomQueue(object):
    def __init__(self, service, workers=THREAD_WORKERS):
        self.service  = service
        self.monitor  = service.monitor
        self.cache    = service.cache
        self.pool      = ExecutorPool()
        self.lock     = Lock()
        self.wake     = Event()
        
        self.heap     = []
        self.pending  = {}
        self.counter  = 0
        
        self.useExecutor = True#SETTINGS.getSettingBool('Enable_Executor')
        self.queueThread = Thread(target=self.execute, name=f"{ADDON_ID}.priorityQUE")
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f'{self.__class__.__name__}: {msg}', level)
        
    def _freeze(self, obj):
        if isinstance(obj, list): return tuple(self._freeze(item) for item in obj)
        if isinstance(obj, dict): return tuple(sorted((k, self._freeze(v)) for k, v in obj.items()))
        if isinstance(obj, set):  return frozenset(self._freeze(item) for item in obj)
        return obj
        
    def _get_task_key(self, func, args, kwargs):
        return (func.__name__, tuple(self._freeze(arg) for arg in args), tuple(sorted((k, self._freeze(v)) for k, v in kwargs.items())) if kwargs else ())

    def push(self, package: tuple, priority: int = 3, delay: int = 0, timer: int = 0):
        now = time.time()
        if   timer: execute_at = timer
        elif delay: execute_at = now + delay
        else:       execute_at = now
            
        func, args, kwargs = package
        if kwargs is None: kwargs = {}
        task_key = self._get_task_key(func, args, kwargs)
        if task_key:
            priority = max(1, min(5, int(priority)))
            with self.lock:
                if task_key in self.pending:
                    existing_task = self.pending[task_key]
                    # Lower numerical value means HIGHER priority (1 is highest, 5 is lowest)
                    if priority < existing_task.priority:
                        self.log(f"push, Upgrading {func.__name__} priority from {existing_task.priority} to {priority}.", xbmc.LOGDEBUG)
                        existing_task.cancel()  # Cancel lower-priority duplicate
                        new_task = Task(func, args, kwargs, priority, execute_at)
                        self.pending[task_key] = new_task
                        self.counter += 1
                        heapq.heappush(self.heap, (priority, self.counter, new_task))
                    else: self.log(f"push, Task {func.__name__} ignored (already queued with higher/equal priority {existing_task.priority}).", xbmc.LOGDEBUG)
                else:
                    new_task = Task(func, args, kwargs, priority, execute_at)
                    self.pending[task_key] = new_task
                    self.counter += 1
                    heapq.heappush(self.heap, (priority, self.counter, new_task))
                    self.log(f"push, Pushed task {func.__name__} (Priority: {priority}).", xbmc.LOGDEBUG)

            if not self.monitor.abortRequested() and not self.queueThread.is_alive():
                self.useExecutor = True#SETTINGS.getSettingBool('Enable_Executor')
                self.queueThread = Thread(target=self.execute, name=f"{ADDON_ID}.queueThread")
                self.queueThread.daemon = True
                self.queueThread.start()

    def pop(self):
        with self.lock:
            while not self.monitor.abortRequested() and self.heap:
                _, _, task = heapq.heappop(self.heap)
                task_key = self._get_task_key(task.func, task.args, task.kwargs)
                if task.is_cancelled: continue
                if self.pending.get(task_key) is task:
                    self.pending.pop(task_key, None)
                return task
            return None

    def execute(self):
        self.log("execute, Thread execution loop active.", xbmc.LOGINFO)
        while not self.monitor.abortRequested():
            if self.monitor.waitForAbort(2.0):
                self.log("execute, Shutdown/Abort requested. Exiting queue.", xbmc.LOGINFO)
                break
            else:
                task = self.pop()
                if task is None:
                    self.monitor.waitForAbort(2.0)
                    continue
                    
                if task.execute_at and task.execute_at > time.time():
                    with self.lock:
                        self.counter += 1
                        heapq.heappush(self.heap, (task.priority, self.counter, task))
                    self.monitor.waitForAbort(min(0.5, max(0.0, task.execute_at - time.time())))
                    continue
                        
                self.log(f"execute, Dispatching {task.func.__name__} (Priority: {task.priority}) to ThreadPool.", xbmc.LOGDEBUG)
                try:
                    with timeit(task.func):
                        if self.useExecutor:
                            future = self.pool._executor.submit(task.func, *task.args, **task.kwargs)
                            future.result()
                        else: 
                            task.func(*task.args, **task.kwargs)
                except Exception as e: self.log(f"execute, failed! {e}", xbmc.LOGERROR)
        self.shutdown()
        self.log("execute, finished: shutting down...")

    def _future_callback(self, future):
        try: 
            return future.result()
        except Exception as e: 
            self.log(f"_future_callback, failed! {e}", xbmc.LOGERROR)
            return future.cancel()

    def shutdown(self, wait=False, cancel=True):
        try: 
            self.pool._executor.shutdown(wait=wait, cancel_futures=cancel)
            self.log("shutdown, pool")
        except Exception: pass
            
