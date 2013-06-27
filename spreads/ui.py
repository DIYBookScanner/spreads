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

"""
spreads UI code.
"""

from __future__ import division, unicode_literals

import argparse
import logging

import spreads.commands as commands
from spreads import config
from spreads.plugin import pluginmanager

parser = argparse.ArgumentParser(
    description="Scanning Tool for  DIY Book Scanner")
subparsers = parser.add_subparsers()

parser.add_argument(
    '--verbose', '-v', dest="verbose", action="store_true")

config_parser = subparsers.add_parser(
    'configure', help="Perform initial configuration of the devices.")
config_parser.set_defaults(func=commands.configure)

capture_parser = subparsers.add_parser(
    'capture', help="Start the capturing workflow")
capture_parser.set_defaults(func=commands.capture)
# Add arguments from plugins
pluginmanager.map(lambda x, y, z: x.plugin.add_arguments(y, z),
                  'capture', capture_parser)

# Add arguments from devices
#devices = get_devices()
#for device in devices:
#    device.add_arguments(capture_parser)

download_parser = subparsers.add_parser(
    'download', help="Download scanned images.")
download_parser.add_argument(
    "path", help="Path where scanned images are to be stored")
download_parser.add_argument(
    "--keep", "-k", dest="keep", action="store_true",
    help="Keep files on devices after download")
download_parser.set_defaults(func=commands.download)
# Add arguments from plugins
pluginmanager.map(lambda x, y, z: x.plugin.add_arguments(y, z),
                  'download', download_parser)

postprocess_parser = subparsers.add_parser(
    'postprocess',
    help="Postprocess scanned images.")
postprocess_parser.add_argument(
    "path", help="Path where scanned images are stored")
postprocess_parser.add_argument(
    "--jobs", "-j", dest="jobs", type=int, default=None,
    metavar="<int>", help="Number of concurrent processes")
postprocess_parser.set_defaults(func=commands.postprocess)
# Add arguments from plugins
pluginmanager.map(lambda x, y, z: x.plugin.add_arguments(y, z),
                  'postprocess', postprocess_parser)

wizard_parser = subparsers.add_parser(
    'wizard', help="Interactive mode")
wizard_parser.add_argument(
    "path", help="Path where scanned images are to be stored")
wizard_parser.set_defaults(func=commands.wizard)


def main():
    args = parser.parse_args()
    config.set_args(args)
    loglevel = config['loglevel'].as_choice({
        'none':     logging.NOTSET,
        'info':     logging.INFO,
        'debug':    logging.DEBUG,
        'warning':  logging.WARNING,
        'error':    logging.ERROR,
        'critical': logging.CRITICAL,
    })
    if args.verbose:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)
    args.func(args)
