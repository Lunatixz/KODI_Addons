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
        self.thread = threading.Thread(target=self._loop, name=f"{ADDON_ID}.queue", daemon=True)

    def log(self, msg, level=xbmc.LOGDEBUG):
        log(f'CustomQueue: {msg}', level)

    def push(self, package, priority=3):
        func, args, kwargs = package
        if kwargs is None: kwargs = {}
        key = (func.__name__, args)
        with self.lock:
            if key in self.pending:
                return
            self.pending.add(key)
            self.counter += 1
            heapq.heappush(self.heap, Task(func, args, kwargs, priority, self.counter))
        if not self.thread.is_alive():
            self.thread = threading.Thread(target=self._loop, name=f"{ADDON_ID}.queue", daemon=True)
            self.thread.start()

    def _loop(self):
        while not self.monitor.abortRequested():
            if isScanning():
                if self.monitor.waitForAbort(1.0): break
                continue
            if self.service._playing:
                if self.monitor.waitForAbort(1.0): break
                continue
            task = None
            with self.lock:
                if self.heap:
                    task = heapq.heappop(self.heap)
                    key = (task.func.__name__, task.args)
                    self.pending.discard(key)
            if task is None:
                if self.monitor.waitForAbort(2.0):
                    break
                continue
            self.log(f"execute, {task.func.__name__} (Priority: {task.priority})")
            try:
                task.func(*task.args, **task.kwargs)
            except Exception as e:
                self.log(f"execute failed: {e}", xbmc.LOGERROR)
            if self.monitor.waitForAbort(1.0): break

    def shutdown(self):
        pass

    def snapshot(self):
        with self.lock:
            return [(t.func.__name__, t.args) for t in self.heap]
