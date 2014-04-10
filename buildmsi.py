#!/usr/bin/env python2.7
""" Build Windows MSI distributions.

Requirements:
    - A 'windeps' folder with all of the *exe installers listed in
      BINARY_PACKAGES, available at http://www.lfd.uci.edu/~gohlke/pythonlibs/
      in both 32 and 64 bit.
    - 'pywin32' installers for 32 and 64 bit in 'windeps' folder, , available
      at http://sourceforge.net/projects/pywin32/files/pywin32/
    - spreads and all of its dependencies installed in the present Python
      environment (*not* with pip's '-e' flag!)
    - 'pynsist' package must be installed in the present Python environment,
       currently (2014/04/11) from GitHub master, not from PyPi.
    - 'nsis' executable must be on $PATH ('apt-get install nsis' on Debian
       systems)

Run:
    $ python buildmsi.py

When complete, MSIs can be found under 'build/msi{32,64}/spreads_{version}.exe'
"""

import os
import shutil
import sys
import tempfile
import zipfile
from collections import namedtuple

import nsist
import pkg_resources
from spreads.vendor.pathlib import Path

import spreads

BINARY_PACKAGES = {
    "cffi": "cffi-0.8.2.{arch}-py2.7.exe",
    "MarkupSafe": "MarkupSafe-0.19.{arch}-py2.7.exe",
    "PIL": "Pillow-2.4.0.{arch}-py2.7.exe",
    "psutil": "psutil-2.1.0.{arch}-py2.7.exe",
    "pyexiv2": "pyexiv2-0.3.2.{arch}-py2.7.exe",
    "PySide": "PySide-1.2.1.{arch}-py2.7.exe",
    "PyYAML": "PyYAML-3.11.{arch}-py2.7.exe",
    "tornado": "tornado-3.2.{arch}-py2.7.exe",
    "setuptools": "setuptools-3.4.1.{arch}-py2.7.exe"
}

SourceDep = namedtuple("SourceDep", ("project_name", "module_name"))
SOURCE_PACKAGES = [
    # project   module
    SourceDep(*("spreads",)*2),
    SourceDep(*(None, "spreadsplug")),
    SourceDep(*("Flask", "flask")),
    SourceDep(*("Jinja2", "jinja2")),
    SourceDep(*("Werkzeug", "werkzeug")),
    SourceDep(*("backports.ssl-match-hostname", "backports")),
    SourceDep(*("blinker",)*2),
    SourceDep(*("colorama",)*2),
    SourceDep(*("futures", "concurrent")),
    SourceDep(*("itsdangerous",)*2),
    SourceDep(*("pyusb", "usb")),
    SourceDep(*("requests",)*2),
    SourceDep(*("waitress",)*2),
    SourceDep(*("zipstream",)*2),
]


def extract_native_pkg(fname, pkg_dir):
    zf = zipfile.ZipFile(unicode(Path('win_deps')/fname))
    tmpdir = Path(tempfile.mkdtemp())
    zf.extractall(unicode(tmpdir))
    fpaths = []
    if (tmpdir/'PLATLIB').exists():
        fpaths += [p for p in (tmpdir/'PLATLIB').iterdir()]
    if (tmpdir/'PURELIB').exists():
        fpaths += [p for p in (tmpdir/'PURELIB').iterdir()]
    for path in fpaths:
        if path.is_dir():
            shutil.copytree(unicode(path), unicode(pkg_dir/path.name))
        else:
            shutil.copy2(unicode(path), unicode(pkg_dir/path.name))
    shutil.rmtree(unicode(tmpdir))


def copy_info(pkg, pkg_dir):
    try:
        dist = pkg_resources.get_distribution(pkg)
    except pkg_resources.DistributionNotFound:
        raise IOError("No distribution could be found for {0}!".format(pkg))
    if dist.location == os.getcwd():
        egg_name = dist.project_name
    else:
        egg_name = dist.egg_name()

    egg_path = Path(dist.location)/(egg_name + ".egg-info")
    dist_path = Path(dist.location)/(dist.project_name + "-" + dist.version
                                     + ".dist-info")
    if egg_path.exists():
        src_path = egg_path
    elif dist_path.exists():
        src_path = dist_path
    else:
        raise IOError("No egg-info or dist-info could be found for {0}!"
                      .format(pkg))
    if src_path.is_dir():
        shutil.copytree(unicode(src_path), unicode(pkg_dir/src_path.name))
    else:
        shutil.copy2(unicode(src_path), unicode(pkg_dir/src_path.name))


def build_msi(bitness=32):
    build_path = Path('build')
    if not build_path.exists():
        build_path.mkdir()
    pkg_dir = build_path/'pynsist_pkgs'
    if pkg_dir.exists():
        shutil.rmtree(unicode(pkg_dir))
    pkg_dir.mkdir()
    for pkg in BINARY_PACKAGES.itervalues():
        arch = 'win32' if bitness == 32 else 'win-amd64'
        extract_native_pkg(pkg.format(arch=arch), pkg_dir)

    for pkg in (x.project_name for x in SOURCE_PACKAGES
                if x.project_name is not None):
        copy_info(pkg, pkg_dir)

    icon = os.path.abspath("spreads.ico")
    extra_files = [
        os.path.join(os.path.abspath('win_deps'),
                     'pywin32-2.7.6{0}.exe'
                     .format('.amd64' if bitness == 64 else '')
                     )]
    nsi_template = os.path.abspath("template.nsi")

    # NOTE: We need to remove the working directory from sys.path to force
    # pynsist to copy all of our modules, including 'spreads' and 'spreadsplug'
    # from the site-packages. Additionally, we need to change into the
    # build directory.
    if os.getcwd() in sys.path:
        sys.path.remove(os.getcwd())
    os.chdir(unicode(build_path))
    nsist.all_steps(
        appname="spreads",
        version=spreads.__version__,
        script=None,
        entry_point="spreads.main:main",
        icon=icon,
        console=False,
        packages=[x.module_name for x in SOURCE_PACKAGES],
        extra_files=extra_files,
        py_version="2.7.6",
        py_bitness=bitness,
        build_dir='msi{0}'.format(bitness),
        installer_name=None,
        nsi_template=nsi_template
    )
    os.chdir('..')

if __name__ == '__main__':
    if os.path.exists('spreads.egg-info'):
        shutil.rmtree('spreads.egg-info')
    for bitness in (32, 64):
        build_msi(bitness)
