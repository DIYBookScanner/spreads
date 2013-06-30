#!/usr/bin/env python2.7
from setuptools import setup, find_packages

setup(
    name='spreads',
    version='0.2',
    author='Johannes Baiter',
    author_email='johannes.baiter@gmail.com',
    packages=['spreads', 'spreadsplug'],
    include_package_data=True,
    scripts=['spread', ],
    url='http://github.com/jbaiter/spreads',
    license='MIT',
    description='Tool to facilitate book digitization with the DIY Book '
                'Scanner',
    long_description=open('README.rst').read(),
    install_requires=[
        "clint >= 0.3.1",
        "pyusb >= 1.0.0a3",
        "pyptpchdk >= 0.2.1",
        "PyYAML >= 3.10",
        "Wand >= 0.3.1",
        "stevedore >= 0.9.1",
    ],
    entry_points={
        'spreadsplug.devices': [
            'chdkcamera = spreadsplug.chdkcamera:CHDKCameraDevice',
            'a2200      = spreadsplug.chdkcamera:CanonA2200CameraDevice',
        ],
        'spreadsplug.hooks': [
            'combine    = spreadsplug.combine:CombinePlugin',
            'autorotate = spreadsplug.autorotate:AutoRotatePlugin',
            'scantailor = spreadsplug.scantailor:ScanTailorPlugin',
            'pdfbeads   = spreadsplug.pdfbeads:PDFBeadsPlugin',
            'djvubind   = spreadsplug.djvubind:DjvuBindPlugin',
            'colorcorrect = spreadsplug.colorcorrect:ColorCorrectionPlugin',
        ],
    },

)
