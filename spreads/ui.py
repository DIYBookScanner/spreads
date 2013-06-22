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
from spreads.plugin import (DownloadPlugin, ShootPlugin,
                            FilterPlugin, get_plugins)

parser = argparse.ArgumentParser(
    description="Scanning Tool for  DIY Book Scanner")
subparsers = parser.add_subparsers()

parser.add_argument(
    '--verbose', '-v', dest="verbose", action="store_true")

config_parser = subparsers.add_parser(
    'configure', help="Perform initial configuration of the cameras.")
config_parser.set_defaults(func=commands.configure)

shoot_parser = subparsers.add_parser(
    'shoot', help="Start the shooting workflow")
shoot_parser.add_argument(
    '--iso', '-i', dest="iso_value", type=int, metavar="<int>",
    help="ISO sensitivity [default: {0}]".format(
        config['shoot']['sensitivity'].get(int)))
shoot_parser.add_argument(
    "--shutter", '-s', dest="shutter_speed", type=unicode,
    metavar="<int/float/str>", help="Shutter speed [default: {0}]".format(
        config['shoot']['shutter_speed'].get(unicode)))
shoot_parser.add_argument(
    "--zoom", "-z", dest="zoom_value", type=int, metavar="<int>",
    help="Zoom level [default: {0}]".format(config['shoot']['zoom_level']
                                            .get(int)))
shoot_parser.set_defaults(func=commands.shoot)
# Add arguments from plugins
plugin_list = [x for x in config['shoot']['plugins'].all_contents()]
plugin_classes = {x.config_key: x for x in get_plugins(ShootPlugin)}
for key in plugin_list:
    plugin_classes[key].add_arguments(shoot_parser)

download_parser = subparsers.add_parser(
    'download', help="Download scanned images.")
download_parser.add_argument(
    "path", help="Path where scanned images are to be stored")
download_parser.add_argument(
    "--keep", "-k", dest="keep", action="store_true",
    help="Keep files on cameras after download")
download_parser.set_defaults(func=commands.download)
# Add arguments from plugins
plugin_list = [x for x in config['download']['plugins'].all_contents()]
plugin_classes = {x.config_key: x for x in get_plugins(DownloadPlugin)}
for key in plugin_list:
    plugin_classes[key].add_arguments(download_parser)

postprocess_parser = subparsers.add_parser(
    'postprocess',
    help="Postprocess scanned images.")
postprocess_parser.add_argument(
    "path", help="Path where scanned images are stored")
postprocess_parser.add_argument(
    "--jobs", "-j", dest="num_jobs", type=int, default=None,
    metavar="<int>", help="Number of concurrent processes")
postprocess_parser.set_defaults(func=commands.postprocess)
# Add arguments from plugins
plugin_list = [x for x in config['postprocess']['filters'].all_contents()]
plugin_classes = {x.config_key: x for x in get_plugins(FilterPlugin)}
for key in plugin_list:
    plugin_classes[key].add_arguments(postprocess_parser)

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
    func_args = dict(x for x in args._get_kwargs()
                     if x[0] not in ('func', 'verbose'))
    logging.debug(func_args)
    args.func(**func_args)
