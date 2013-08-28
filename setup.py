#!/usr/bin/env python2.7
from setuptools import setup

setup(
    name='spreads',
    version='0.3.3',
    author='Johannes Baiter',
    author_email='johannes.baiter@gmail.com',
    packages=['spreads', 'spreadsplug', 'spreadsplug.dev'],
    include_package_data=True,
    scripts=['spread', ],
    url='http://github.com/jbaiter/spreads',
    license='MIT',
    description='Book digitization workflow assistant',
    long_description=open('README.rst').read(),
    install_requires=[
        "colorama >= 0.2.5",
        "pyusb >= 1.0.0a3",
        "pyptpchdk >= 0.2.1",
        "PyYAML >= 3.10",
        "Wand >= 0.3.1",
        "stevedore >= 0.9.1",
        "futures >= 2.1.4",
        "pexif >= 0.13",
        "Pillow >= 2.0.0",
    ],
    entry_points={
        'spreadsplug.devices': [
            'chdkcamera = spreadsplug.dev.chdkcamera:CHDKCameraDevice',
            'a2200      = spreadsplug.dev.chdkcamera:CanonA2200CameraDevice',
        ],
        'spreadsplug.hooks': [
            'combine    = spreadsplug.combine:CombinePlugin',
            'autorotate = spreadsplug.autorotate:AutoRotatePlugin',
            'scantailor = spreadsplug.scantailor:ScanTailorPlugin',
            'pdfbeads   = spreadsplug.pdfbeads:PDFBeadsPlugin',
            'djvubind   = spreadsplug.djvubind:DjvuBindPlugin',
            'colorcorrect = spreadsplug.colorcorrect:ColorCorrectionPlugin',
            'tesseract = spreadsplug.tesseract:TesseractPlugin',
            'gui        = spreadsplug.gui:GuiCommand',
        ],
    },
    test_suite='nose.collector',
)
