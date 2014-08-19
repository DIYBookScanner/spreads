#!/usr/bin/env python2.7
import os
import re
import shutil
from contextlib import contextmanager
from datetime import datetime
from subprocess import check_call, check_output
from setuptools import setup
from setuptools.command.sdist import sdist as SdistCommand
from setuptools.command.bdist_wininst import bdist_wininst as WininstCommand

import spreads

if os.path.exists('README.rst'):
    description_long = open('README.rst').read()
else:
    description_long = """
spreads is a tool that aims to streamline your book scanning workflow.  It
takes care of every step=Setting up your capturing devices, handling the
capturing process, downloading the images to your machine, post-processing them
and finally assembling a variety of output formats.

Along the way you can always fine-tune the auto-generated results either by
supplying arguments or changing the configuration beforehand, or by inspecting
the output and applying your modifications.

It is meant to be fully customizable. This means, adding support for new
devices is made as painless as possible. You can also hook into any of the
commands by implementing one of the available plugin hooks or even implement
your own custom sub-commands.
"""

VERSION = '0.5git{0}.{1}'.format(
    datetime.today().strftime('%Y%m%d'),
    check_output('git rev-parse HEAD'.split())[:4])


def build_frontend_bundles():
    check_call(['make', '-C', 'spreadsplug/web/client', 'production',
                'development'])


class CustomSdistCommand(SdistCommand):
    @contextmanager
    def override_setup_version(self):
        # Hardcode version in distribution's setup.py
        with open('setup.py', 'r') as fp:
            old_setup = fp.read()
        new_setup = re.sub(r'VERSION = (.*?)\n\n',
                           "VERSION = '{0}'\n\n".format(VERSION),
                           old_setup, count=1, flags=re.DOTALL)
        with open('setup.py', 'w') as fp:
            fp.write(new_setup)
        yield
        with open('setup.py', 'w') as fp:
            fp.write(old_setup)

    def run(self):
        build_frontend_bundles()
        if not 'git' in VERSION:
            return SdistCommand.run(self)
        with self.override_setup_version():
            return SdistCommand.run(self)


class CustomWininstCommand(WininstCommand):
    def run(self):
        from buildmsi import build_msi
        build_frontend_bundles()
        build_msi(bitness=32)
        if not os.path.exists('./dist'):
            os.mkdir('./dist')
        shutil.copy(
            './build/msi32/spreads_{0}.exe'.format(spreads.__version__),
            './dist')

setup(
    name="spreads",
    version=VERSION,
    author="Johannes Baiter",
    author_email="johannes.baiter@gmail.com",
    url="http://spreads.readthedocs.org",
    description="Book digitization workflow suite",
    long_description=description_long,
    license="GNU AGPLv3",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        ("License :: OSI Approved :: GNU Affero General Public License v3 or "
         "later (AGPLv3+)"),
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2.7",
        "Topic :: Multimedia :: Graphics :: Capture",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
    ],
    keywords=[
        "digitization",
        "scanning",
        "chdk",
        "diybookscanner",
        "bookscanning",
    ],
    packages=[
        "spreads",
        "spreads.vendor",
        "spreads.vendor.huey",
        "spreads.vendor.huey.backends",
        "spreadsplug",
        "spreadsplug.dev",
        "spreadsplug.gui",
        "spreadsplug.web",
    ],
    package_data={
        'spreadsplug.gui': ['pixmaps/monk.png'],
        'spreadsplug.web': ['client/index.html', 'client/build/*']
    },
    entry_points={
        'console_scripts': [
            'spread = spreads.main:main',
        ],
        'spreadsplug.devices': [
            "chdkcamera=spreadsplug.dev.chdkcamera:CHDKCameraDevice",
            "gphoto2camera=spreadsplug.dev.gphoto2camera:GPhoto2CameraDevice",
            "dummy=spreadsplug.dev.dummy:DummyDevice"
        ],
        'spreadsplug.hooks': [
            "autorotate     =spreadsplug.autorotate:AutoRotatePlugin",
            "scantailor     =spreadsplug.scantailor:ScanTailorPlugin",
            "pdfbeads       =spreadsplug.pdfbeads:PDFBeadsPlugin",
            "djvubind       =spreadsplug.djvubind:DjvuBindPlugin",
            "tesseract      =spreadsplug.tesseract:TesseractPlugin",
            "gui            =spreadsplug.gui:GuiCommand",
            "web            =spreadsplug.web:WebCommands",
            "intervaltrigger=spreadsplug.intervaltrigger:IntervalTrigger",
            "hidtrigger     =spreadsplug.hidtrigger:HidTrigger",
        ]
    },
    install_requires=[
        "colorama >= 0.2.4",
        "PyYAML >= 3.10",
        "futures >= 2.1",
        "blinker >= 1.3",
        "roman >= 2.0.0",
        "psutil >= 2.0.0",
        "isbnlib >= 3.3.8",
    ],
    extras_require={
        "chdkcamera": ["pyusb >= 1.0.0b1", "jpegtran-cffi >= 0.4"],
        "gphoto2camera": ["piggyphoto >= 0.1"],
        "autorotate": ["jpegtran-cffi >= 0.4"],
        "gui": ["PySide >= 1.2.1"],
        "hidtrigger": ["hidapi-cffi >= 0.1"],
        "web": [
            "Flask >= 0.10.1",
            "jpegtran-cffi >= 0.4",
            "requests >= 2.2.0",
            "zipstream >= 1.0.2",
            "tornado >= 3.1",
            "Wand >= 0.3.5",
        ]
    },
    cmdclass={'sdist': CustomSdistCommand,
              'bdist_wininst': CustomWininstCommand}
)
