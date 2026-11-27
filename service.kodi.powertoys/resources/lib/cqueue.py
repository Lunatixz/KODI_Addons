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
import heapq
import threading
import time
from globals import *

class Task:
    __slots__ = ('func', 'args', 'kwargs', 'priority', 'counter')
    def __init__(self, func, args, kwargs, priority, counter):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.priority = priority
        self.counter = counter
    def __lt__(self, other):
        return (self.priority, self.counter) < (other.priority, other.counter)

class CustomQueue:
    def __init__(self, service):
        self.service = service
        self.monitor = service.monitor
        self.lock = threading.Lock()
        self.heap = []
        self.counter = 0
        self.pending = set()
        self._blocked = None
        self.current_task = None
        self._wake = threading.Event()
        self.thread = threading.Thread(target=self._loop, name=f"{ADDON_ID}.queue", daemon=True)

    def log(self, msg, level=xbmc.LOGDEBUG):
        log(f'CustomQueue: {msg}', level)

    def push(self, package, priority=3):
        func, args, kwargs = package
        if kwargs is None: kwargs = {}
        # repr(): args may contain lists (cleanMovies gets a dup-group) - raw tuples
        # are unhashable and made every such push die with TypeError before queueing
        key = (func.__name__, repr(args))
        with self.lock:
            if key in self.pending:
                return
            self.pending.add(key)
            self.counter += 1
            heapq.heappush(self.heap, Task(func, args, kwargs, priority, self.counter))
        self._wake.set()
        if not self.thread.is_alive():
            self.thread = threading.Thread(target=self._loop, name=f"{ADDON_ID}.queue", daemon=True)
            self.thread.start()

    def _loop(self):
        while not self.monitor.abortRequested():
            if isScanning():
                with self.lock:
                    has_work = bool(self.heap)
                if has_work and self._blocked != 'scan':
                    # explain the silence: tasks are queued but a library scan owns the box
                    self._blocked = 'scan'
                    notification('%s: waiting for the library scan to finish...' % ADDON_NAME)
                if self.monitor.waitForAbort(1.0): break
                continue
            if self.service._isPlaying():
                if self.monitor.waitForAbort(10.0): break
                continue
            task = None
            with self.lock:
                if self.heap:
                    task = heapq.heappop(self.heap)
                    key = (task.func.__name__, repr(task.args))
                    self.pending.discard(key)
                else:
                    self._wake.clear()
            if task is None:
                self._wake.wait(5.0)
                continue
            if self.service._isPlaying():
                # playback started between the check above and popping the task; re-queue it
                self.push((task.func, task.args, task.kwargs), task.priority)
                if self.monitor.waitForAbort(10.0): break
                continue
            self._blocked = None
            self.current_task = task.func.__name__
            self.log(f"execute, {self.current_task} (Priority: {task.priority})")
            try:
                task.func(*task.args, **task.kwargs)
            except Exception as e:
                self.log(f"execute failed: {e}", xbmc.LOGERROR)
                # surface crashes - otherwise a failing task is invisible to the user
                notification('%s: %s failed: %s' % (ADDON_NAME, self.current_task, e), icon=xbmcgui.NOTIFICATION_ERROR)
            finally:
                self.current_task = None
            delay = 2.0 if task.func.__name__ in ('refreshTVshow', 'refreshMovie') else 1.0
            if self.monitor.waitForAbort(delay): break

    def snapshot(self):
        with self.lock:
            return [(t.func.__name__, t.args) for t in self.heap]
