#!/bin/bash
set -e

VERSION=$(grep "__version__" spreads/__init__.py |sed -e "s/.* = \"\(.*\)\"/\1/g")

mkdir -p debian_build
python setup.py sdist
cp dist/spreads-$VERSION.tar.gz debian_build/spreads_$VERSION.orig.tar.gz
tar xf dist/spreads-$VERSION.tar.gz -C debian_build
cp -R debian debian_build/spreads-$VERSION
cd debian_build/spreads-$VERSION
debuild -S -us -uc
cd ../../
mv debian_build/*dsc debian_build/*.orig.tar.gz debian_build/*.debian.tar.* dist/
rm -rf debian_build
