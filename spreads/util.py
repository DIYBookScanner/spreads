# -*- coding: utf-8 -*-

# Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Various utility functions and classes.
"""

from __future__ import division, unicode_literals, print_function

import abc
import glob
import json
import logging
import os
import pkg_resources
import platform
import re
import subprocess
from unicodedata import normalize

import blinker
import colorama
import psutil
import roman
from colorama import Fore, Back, Style
from spreads.vendor.pathlib import Path


class SpreadsException(Exception):
    """ General exception """
    pass


class DeviceException(SpreadsException):
    """ Raised when a device-related error occured. """
    pass


class MissingDependencyException(SpreadsException):
    """ Raised when a dependency for a plugin is missing. """
    pass


def get_version():
    """ Get installed version via pkg_resources. """
    return pkg_resources.require('spreads')[0].version


def find_in_path(name):
    """ Find executable in $PATH.

    :param name:    name of the executable
    :type name:     unicode
    :returns:       Path to executable or None if not found
    :rtype:         unicode or None

    """
    candidates = None
    if is_os('windows'):
        import _winreg
        if name.startswith('scantailor'):
            try:
                cmd = _winreg.QueryValue(
                    _winreg.HKEY_CLASSES_ROOT,
                    'Scan Tailor Project\\shell\\open\\command')
                bin_path = cmd.split('" "')[0][1:]
                if name.endswith('-cli'):
                    bin_path = bin_path[:-4] + "-cli.exe"
                return bin_path if os.path.exists(bin_path) else None
            except OSError:
                return None
        else:
            path_dirs = os.environ.get('PATH').split(';')
            path_dirs.append(os.getcwd())
            path_exts = os.environ.get('PATHEXT').split(';')
            candidates = (os.path.join(p, name + e)
                          for p in path_dirs
                          for e in path_exts)
    else:
        candidates = (os.path.join(p, name)
                      for p in os.environ.get('PATH').split(':'))
    return next((c for c in candidates if os.path.exists(c)), None)


def is_os(osname):
    """ Check if the current operating system matches the expected.

    :param osname:  Operating system name as returned by
                    :py:func:`platform.system`
    :returns:       Whether the OS matches or not
    :rtype:         bool
    """
    return platform.system().lower() == osname


def check_futures_exceptions(futures):
    """" Go through passed :py:class:`concurrent.futures._base.Future` objects
         and re-reaise the first Exception raised by any one of them.

    :param futures: Iterable that contains the futures to be checked
    :type futures:  iterable with :py:class:`concurrent.futures._base.Future`
                    instances
    """
    if any(x.exception() for x in futures):
        exc = next(x for x in futures if x.exception()).exception()
        raise exc


def get_free_space(path):
    """ Return free space on file-system underlying the passed path.

    :param path:    Path on file-system the free space of which is desired
    :type path;     unicode
    :return:        Free space in bytes
    :rtype:         int
    """
    return psutil.disk_usage(unicode(path)).free


def get_subprocess(cmdline, **kwargs):
    """ Get a :py:class:`subprocess.Popen` instance.

    On Windows systems, the process will be ran in the background and won't
    open a cmd-window or appear in the taskbar.
    The function signature matches that of the :py:class:`subprocess.Popen`
    initialization method.
    """
    if subprocess.mswindows and 'startupinfo' not in kwargs:
        su = subprocess.STARTUPINFO()
        su.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        su.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = su
    return subprocess.Popen(cmdline, **kwargs)


def wildcardify(pathnames):
    """ Try to generate a single path with wildcards that matches all
        `pathnames`.

    :param pathnames:   List of pathnames to find a wildcard string for
    :type pathanmes:    List of str/unicode
    :return:            The wildcard string or None if none was found
    :rtype:             unicode or None
    """
    wildcard_str = ""
    for idx, char in enumerate(pathnames[0]):
        if all(p[idx] == char for p in pathnames[1:]):
            wildcard_str += char
        elif not wildcard_str or wildcard_str[-1] != "*":
            wildcard_str += "*"
    matched_paths = glob.glob(wildcard_str)
    if not sorted(pathnames) == sorted(matched_paths):
        return None
    return wildcard_str


def diff_dicts(old, new):
    """ Get the difference between two dictionaries.

    :param old: Dictionary to base comparison on
    :type old:  dict
    :param new: Dictionary to compare with
    :type new:  dict
    :return:    A (possibly nested) dictionary containing all items from `new`
                that differ from the ones in `old`
    :rtype:     dict
    """
    out = {}
    for key, value in old.iteritems():
        if new[key] != value:
            out[key] = new[key]
        elif isinstance(value, dict):
            diff = diff_dicts(value, new[key])
            if diff:
                out[key] = diff
    return out


def slugify(text, delimiter=u'-'):
    """Generates an ASCII-only slug.

    Code adapted from Flask snipped by Armin Ronacher:
    http://flask.pocoo.org/snippets/5/

    :param text:        Text to create slug for
    :type text:         unicode
    :param delimiter:   Delimiter to use in slug
    :type delimiter:    unicode
    :return:            The generated slug
    :rtype:             unicode
    """
    punctuation_re = r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+'
    result = []
    for word in re.split(punctuation_re, text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delimiter.join(result))


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


class ColourStreamHandler(logging.StreamHandler):
    """ A colorized output StreamHandler
    Kudos to Leigh MacDonald:
    http://leigh.cudd.li/article/Cross_Platform_Colorized_Logger_Output_Using_\
    Pythons_logging_Module_And_Colorama
    """

    # Some basic colour scheme defaults
    colours = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARN': Fore.YELLOW,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRIT': Back.RED + Fore.WHITE,
        'CRITICAL': Back.RED + Fore.WHITE
    }

    @property
    def is_tty(self):
        """ Check if we are using a "real" TTY. If we are not using a TTY it
        means that the colour output should be disabled.

        :return: Using a TTY status
        :rtype: bool
        """
        try:
            return getattr(self.stream, 'isatty', None)()
        except:
            return False

    def emit(self, record):
        try:
            message = self.format(record)
            if not self.is_tty:
                self.stream.write(message)
            else:
                self.stream.write(self.colours[record.levelname]
                                  + message + Style.RESET_ALL)
            self.stream.write(getattr(self, 'terminator', '\n'))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class EventHandler(logging.Handler):
    """ Subclass of :py:class:`logging.Handler` that emits a
        :py:class:`blinker.base.Signal` whenever a new record is emitted.
    """
    signals = blinker.Namespace()
    on_log_emit = signals.signal('logrecord', doc="""\
    Sent when a log record was emitted.

    :keyword :class:`logging.LogRecord` record: the LogRecord
    """)

    def emit(self, record):
        self.on_log_emit.send(record=record)


def get_data_dir(create=False):
    """ Return (and optionally create) the user's default data directory.

    :param create:  Create the data directory if it doesn't exist
    :type create:   bool
    :return:        Path to the default data directory
    :rtype:         unicode
    """
    UNIX_DIR_VAR = 'XDG_DATA_HOME'
    UNIX_DIR_FALLBACK = '~/.config'
    WINDOWS_DIR_VAR = 'APPDATA'
    WINDOWS_DIR_FALLBACK = '~\\AppData\\Roaming'
    MAC_DIR = '~/Library/Application Support'
    base_dir = None
    if is_os('darwin'):
        if Path(UNIX_DIR_FALLBACK).exists:
            base_dir = UNIX_DIR_FALLBACK
        else:
            base_dir = MAC_DIR
    elif is_os('windows'):
        if WINDOWS_DIR_VAR in os.environ:
            base_dir = os.environ[WINDOWS_DIR_VAR]
        else:
            base_dir = WINDOWS_DIR_FALLBACK
    else:
        if UNIX_DIR_VAR in os.environ:
            base_dir = os.environ[UNIX_DIR_VAR]
        else:
            base_dir = UNIX_DIR_FALLBACK
    app_path = Path(base_dir)/'spreads'
    if create and not app_path.exists():
        app_path.mkdir()
    return unicode(app_path)


def colorize(text, color):
    """ Return text with a new ANSI foreground color.

    :param text:    Text to be wrapped
    :param color:   ANSI color to wrap text in
    :type color:    str (from :py:class:`colorama.ansi.AnsiCodes`)
    :return:        Colorized text
    """
    return color + text + colorama.Fore.RESET


class RomanNumeral(object):
    """ Number type that represents integers as Roman numerals and that
        can be used in all arithmetic operations applicable to integers.
    """
    @staticmethod
    def is_roman(value):
        """ Check if `value` is a valid Roman numeral.

        :param value:   Value to be checked
        :type value:    unicode
        :returns:       Whether the value is valid or not
        :rtype:         bool
        """
        return bool(roman.romanNumeralPattern.match(value))

    def __init__(self, value, case='upper'):
        """ Create a new instance.

        :param value:   Value of the instance
        :type value:    int, unicode containing valid Roman numeral or
                        :py:class:`RomanNumeral`
        """
        self._val = self._to_int(value)
        self._case = case
        if isinstance(value, basestring) and not self.is_roman(value):
            self._case = 'lower'
        elif isinstance(value, RomanNumeral):
            self._case = value._case

    def _to_int(self, value):
        if isinstance(value, int):
            return value
        elif isinstance(value, basestring) and self.is_roman(value.upper()):
            return roman.fromRoman(value.upper())
        elif isinstance(value, RomanNumeral):
            return value._val
        else:
            raise ValueError("Value must be a valid roman numeral, a string"
                             " representing one or an integer: '{0}'"
                             .format(value))

    def __cmp__(self, other):
        if self._val > self._to_int(other):
            return 1
        elif self._val == self._to_int(other):
            return 0
        elif self._val < self._to_int(other):
            return -1

    def __add__(self, other):
        return RomanNumeral(self._val + self._to_int(other), self._case)

    def __sub__(self, other):
        return RomanNumeral(self._val - self._to_int(other), self._case)

    def __int__(self):
        return self._val

    def __str__(self):
        strval = roman.toRoman(self._val)
        if self._case == 'lower':
            return strval.lower()
        else:
            return strval

    def __unicode__(self):
        return unicode(str(self))

    def __repr__(self):
        return str(self)


class CustomJSONEncoder(json.JSONEncoder):
    """ Custom :py:class:`json.JSONEncoder`.

        Uses an object's `to_dict` method if present for serialization.

        Serializes :py:class:`pathlib.Path` instances to the string
        representation of their relative path to a BagIt-compliant directory or
        their absolute path if not applicable.
    """
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if isinstance(obj, Path):
            # Serialize paths that belong to a workflow as paths relative to
            # its base directory
            base = next((p for p in obj.parents if (p/'bagit.txt').exists()),
                        None)
            if base:
                return unicode(obj.relative_to(base))
            else:
                return unicode(obj.absolute())
        return json.JSONEncoder.default(self, obj)
