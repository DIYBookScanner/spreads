diyshoot: *They shoot pages, don't they?*
=========================================

This small Python tool tries to help establishing a quick and painless
scanning workflow for users of the DIYBookScanner_.

Features
--------
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
* Interactive Wizard-Mode that handles the full workflow from image
  capturing to post-processing

Requirements
------------
* Python 2.7
* The `clint library`_ (used for the console interface)
* Two cameras running CHDK (development was done using two Canon A2200s,
  no further cameras were tested, but should work in theory)
* A version of `ptpcam modified for CHDK`_ in /usr/bin
* gphoto2

Usage
-----
configure
*********
``diyshoot.py configure``
Sets up your cameras for shooting by assigning every connected camera with a 'left' or 'right' label. This step only has to be performed once, as the information is permanently stored on the cameras.

shoot
*****
``diyshoot.py shoot [--iso <int>] [--shutter <int>] [--zoom <int>]``
Launches a shooting loop. You can set values for ISO, shutter speed and zoom level. ISO and shutter speed have to be provided as APEX96 values, see the CHDK wiki (ISO_, shutter_) for more information. Please be careful not to specify a zoom level that is outside of your camera's range, as the program currently does not check for that. Capture an image by pressing 'b' and stop the shooting process by pressing any other key.

download
********
``diyshoot.py download <destination-path>``
Downloads the images from both cameras to *left* and *right* subdirectories of the *destination-path*. Once the download is completed, the images will be removed from the cameras to save space.

merge
*****
``diyshoot.py merge <image-path>``
Combines the images stored in the *left* and *right* subdirectories of *image-path* to a new *combined* directory.

.. _DIYBookScanner: http://diybookscanner.org
.. _ppmunwarp: http://diybookscanner.org/forum/viewtopic.php?f=19&t=2589&p=14281#p14281
.. _graycard and imagemagick: http://diybookscanner.org/forum/viewtopic.php?f=20&t=2848
.. _clint library: https://github.com/kennethreitz/clint
.. _ptpcam modified for CHDK: http://forum.chdk-treff.de/download/file.php?id=1640
.. _ISO: http://chdk.wikia.com/wiki/CHDK_scripting#set_sv96
.. _shutter: http://chdk.wikia.com/wiki/CHDK_scripting#set_tv96_direct
