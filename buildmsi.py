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

import pkg_resources
from nsist import InstallerBuilder
from spreads.vendor.pathlib import Path

import spreads

class SourceDep(namedtuple('SourceDep', ['project_name', 'module_name'])):
    def __new__(cls, project_name, module_name=None):
        if module_name is None:
            module_name = project_name
        return super(SourceDep, cls).__new__(cls, project_name, module_name)

BINARY_PACKAGES = {
    "MarkupSafe": "MarkupSafe-0.19.{arch}-py2.7.exe",
    "psutil": "psutil-2.1.0.{arch}-py2.7.exe",
    "PyYAML": "PyYAML-3.11.{arch}-py2.7.exe",
    "tornado": "tornado-3.2.{arch}-py2.7.exe",
    "setuptools": "setuptools-3.4.1.{arch}-py2.7.exe"
}


SOURCE_PACKAGES = [
    SourceDep("spreads"),
    SourceDep(None, "spreadsplug"),
    SourceDep("Flask", "flask"),
    SourceDep("Jinja2", "jinja2"),
    SourceDep("Werkzeug", "werkzeug"),
    SourceDep("backports.ssl-match-hostname", "backports"),
    SourceDep("blinker"),
    SourceDep("colorama"),
    SourceDep("futures", "concurrent"),
    SourceDep("itsdangerous"),
    SourceDep("pyusb", "usb"),
    SourceDep("requests"),
    SourceDep("waitress"),
    SourceDep("zipstream"),
    SourceDep("roman"),
    SourceDep("Wand", "wand"),
]

EXTRA_FILES = [
    "ImageMagick-6.5.6-8-Q8-windows-dll.exe",
    "pyexiv2-0.3.2{arch}.exe",
    "pywin32-2.7.6{arch}.exe",
    "scantailor-enhanced-20140214-32bit-install.exe",
    "tesseract-ocr-setup-3.02.02.exe",
    "chdkptp",
    "pdfbeads.exe",
    "jbig2.exe",
]


def extract_native_pkg(fname, pkg_dir):
    zf = zipfile.ZipFile(unicode(Path('win_deps')/'python'/fname))
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
    extra_files = [(unicode((Path('win_deps')/'extra'/
                            x.format(arch='.amd64' if bitness == 64 else ''))
                           .absolute()), None) for x in EXTRA_FILES]
    nsi_template = os.path.abspath("template.nsi")

    # NOTE: We need to remove the working directory from sys.path to force
    # pynsist to copy all of our modules, including 'spreads' and 'spreadsplug'
    # from the site-packages. Additionally, we need to change into the
    # build directory.
    if os.getcwd() in sys.path:
        sys.path.remove(os.getcwd())
    os.chdir(unicode(build_path))
    builder = InstallerBuilder(
        appname="spreads",
        version=spreads.__version__,
        packages=[x.module_name for x in SOURCE_PACKAGES],
        extra_files=extra_files,
        py_version="2.7.6",
        py_bitness=bitness,
        build_dir='msi{0}'.format(bitness),
        installer_name=None,
        nsi_template=nsi_template,
        icon=icon,
        shortcuts={
            'Configure spreads': {
                'entry_point': 'spreads.main:run_config_windows',
                'icon': icon,
                'console': False},
            'Spreads Web Service': {
                'entry_point': 'spreads.main:run_service_windows',
                'icon': icon,
                'console': False}
        }
    )
    builder.run()
    os.chdir('..')

if __name__ == '__main__':
    for bitness in (32,64):
        build_msi(bitness)
