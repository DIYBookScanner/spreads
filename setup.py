#!/usr/bin/env python2.7
from distutils.core import setup

setup(
    name='spreads',
    version='0.1.0',
    author='Johannes Baiter',
    author_email='johannes.baiter@gmail.com',
    packages=['spreads', 'spreadsplug'],
    scripts=['spread', ],
    url='http://github.com/jbaiter/spreads',
    license='LICENSE.txt',
    description='Tool to facilitate book digitization with the DIY Book '
                'Scanner',
    long_description=open('README.rst').read(),
    install_requires=[
        "Pillow >=2.0.0",
        "clint >= 0.3.1",
        "pyusb >=1.0.0a3",
    ],
)
