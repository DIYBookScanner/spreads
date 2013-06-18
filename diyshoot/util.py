# -*- coding: utf-8 -*-

# Copyright (c) 2013 Johannes Baiter. All rights reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" Various utility functions.
"""

import multiprocessing
import sys

# Kudos to http://stackoverflow.com/a/1394994/487903
try:
    from msvcrt import getch
except ImportError:
    def getch():
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def run_parallel(jobs, num_procs=None):
    class Worker(multiprocessing.Process):
        def __init__(self, queue):
            super(Worker, self).__init__()
            self.queue = queue

        def run(self):
            for job in iter(self.queue.get, None):
                job['func'](*job['args'], **job['kwargs'])

    if not num_procs:
        num_procs = multiprocessing.cpu_count()
    running = []
    queue = multiprocessing.Queue()
    for i in xrange(num_procs):
        w = Worker(queue)
        running.append(w)
        w.start()
    for job in jobs:
        queue.put(job)
    for i in xrange(num_procs):
        queue.put(None)
    for worker in running:
        worker.join()
