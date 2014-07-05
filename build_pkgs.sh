#!/bin/bash
set -e

GIT_VERSION=$(head -n 1 debian/changelog | sed -e "s/^spreads (\(.*\)-.*) unstable; urgency=low/\1/g")
PY_VERSION=$(grep "__version__" spreads/__init__.py |sed -e "s/.* = \"\(.*\)\"/\1/g")

mkdir -p debian_build
rm -rf dist/
python setup.py sdist
cp dist/spreads-$PY_VERSION.tar.gz debian_build/spreads_$GIT_VERSION.orig.tar.gz
mkdir debian_build/spreads-$GIT_VERSION
tar xf dist/spreads-$PY_VERSION.tar.gz -C debian_build/spreads-$GIT_VERSION --strip-components 1
cp -R debian debian_build/spreads-$GIT_VERSION
cd debian_build/spreads-$GIT_VERSION
debuild -S -us -uc
cd ../../
mv debian_build/*dsc debian_build/*.orig.tar.gz debian_build/*.debian.tar.* dist/
rm -rf debian_build
