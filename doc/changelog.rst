Changelog
=========

0.3 (in development)
--------------------
* Plugins can add completely new subcommands.
* GUI plugin that provides a graphical workflow wizard.
* Tesseract plugin that can perform OCR on captured images.
* pdfbeads plugin can include recognized text in a hidden layer if OCR has
  been performed beforehand.
* Use EXIF tags to persist orientation information instead of JPEG comments.
* Better logging
* Simplified multithreading/multiprocessing code

0.2 (2013/06/30)
----------------
* New plugin system based on Doug Hellmann's `stevedore` package,
  allows packages to extend spreads without being included in the core
  distribution
* The driver for CHDK cameras no longer relies on gphoto2 and ptpcam,
  but relies on Abel Deuring's `pyptpchdk` package to communicate with
  the cameras.
* `Wand` is now used to deal with image data instead of `Pillow`
* New 'colorcorrection' plugin allows users to automatically correct
  white balance.
* Improved tutorial

0.1 (2013/06/23)
----------------
* Initial release
