diyshoot: *They shoot pages, don't they?*
=========================================

This small Python tool tries to help establishing a quick and painless
scanning workflow for users of the DIYBookScanner_.

The following features are supported:
    * Configure the cameras for shooting (i.e. configure which camera is left,
      which is right)
    * Shoot with both cameras **simultaneously**
    * Download images from cameras
    * Merge left and right images into a combined directory

The following features are on the agenda, but not implemented yet:
    * Automatically dewarp the scanned images using ppmunwarp_
    * Do color-correction using a `graycard and imagemagick`_
    * Create a ScanTailor project file that the user can either further edit
      or run automatically

Requirements
------------
    * Python 2.7
    * The `clint library`_ (used for the console interface)
    * Two cameras running CHDK (development was done using two Canon A2200s,
      no further cameras were tested, but should work in theory)
    * A version of `ptpcam modified for CHDK`_ in /usr/local/bin
    * gphoto2

.. _DIYBookScanner: http://diybookscanner.org
.. _ppmunwarp: http://diybookscanner.org/forum/viewtopic.php?f=19&t=2589&p=14281#p14281
.. _graycard and imagemagick: http://diybookscanner.org/forum/viewtopic.php?f=20&t=2848
.. _clint library: https://github.com/kennethreitz/clint
.. _ptpcam modified for CHDK: http://forum.chdk-treff.de/download/file.php?id=1640
