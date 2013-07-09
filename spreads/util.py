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

from __future__ import division, unicode_literals

import abc
import itertools
import os
import sys


class SpreadsException(Exception):
    pass


class DeviceException(SpreadsException):
    pass


def find_in_path(name):
    """ Find executable in $PATH.

    :param name:  name of the executable
    :type name:   unicode
    :returns:     bool -- True if *name* is found or False

    """
    return name in itertools.chain(*tuple(os.listdir(x)
                                   for x in os.environ.get('PATH').split(':')
                                   if os.path.exists(x)))


class _instancemethodwrapper(object):
    def __init__(self, callable):
        self.callable = callable
        self.__dontcall__ = False

    def __getattr__(self, key):
        return getattr(self.callable, key)

    def __call__(self, *args, **kwargs):
        if self.__dontcall__:
            raise TypeError('Attempted to call abstract method.')
        return self.callable(*args, **kwargs)


class _classmethod(classmethod):
    def __init__(self, func):
        super(_classmethod, self).__init__(func)
        isabstractmethod = getattr(func, '__isabstractmethod__', False)
        if isabstractmethod:
            self.__isabstractmethod__ = isabstractmethod

    def __get__(self, instance, owner):
        result = _instancemethodwrapper(super(_classmethod, self)
                                        .__get__(instance, owner))
        isabstractmethod = getattr(self, '__isabstractmethod__', False)
        if isabstractmethod:
            result.__isabstractmethod__ = isabstractmethod
            abstractmethods = getattr(owner, '__abstractmethods__', None)
            if abstractmethods and result.__name__ in abstractmethods:
                result.__dontcall__ = True
        return result


class abstractclassmethod(_classmethod):
    """ New decorator class that implements the @abstractclassmethod decorator
        added in Python 3.3 for Python 2.7.

        Kudos to http://stackoverflow.com/a/13640018/487903

    """
    def __init__(self, func):
        func = abc.abstractmethod(func)
        super(abstractclassmethod, self).__init__(func)
