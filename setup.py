#!/usr/bin/env python2.7
from distutils.core import setup

setup(
    name='diyshoot',
    version='0.1.0',
    author='Johannes Baiter',
    author_email='johannes.baiter@gmail.com',
    packages=['diyshoot', 'diyshoot.cameras'],
    scripts=['bin/diyshoot', ],
    url='http://github.com/jbaiter/diyshoot',
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
