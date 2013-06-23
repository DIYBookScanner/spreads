#!/usr/bin/env python2.7
from setuptools import setup, find_packages

setup(
    name='spreads',
    version='0.1',
    author='Johannes Baiter',
    author_email='johannes.baiter@gmail.com',
    #packages=['spreads', 'spreadsplug'],
    packages=find_packages(),
    include_package_data = True,
    scripts=['spread', ],
    url='http://github.com/jbaiter/spreads',
    license='MIT',
    description='Tool to facilitate book digitization with the DIY Book '
                'Scanner',
    long_description=open('README.rst').read(),
    install_requires=[
        "Pillow >=2.0.0",
        "clint >= 0.3.1",
        "pyusb >=1.0.0a3",
        "PyYAML>=3.10",
        "setuptools-git>=1.0",
    ],
)
