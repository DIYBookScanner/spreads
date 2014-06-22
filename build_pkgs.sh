#!/bin/bash
set -e

VERSION=$(grep "__version__" spreads/__init__.py |sed -e "s/.* = \"\(.*\)\"/\1/g")

mkdir -p debian_build
python setup.py sdist
cp dist/spreads-$VERSION.tar.gz debian_build/spreads_$VERSION.orig.tar.gz
tar xf dist/spreads-$VERSION.tar.gz -C debian_build
cp -R debian debian_build/spreads-$VERSION
cd debian_build/spreads-$VERSION
dpkg-buildpackage -us -uc
cd ../../
mv debian_build/*deb dist/
rm -rf debian_build
