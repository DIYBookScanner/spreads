SpreadPi Setup
--------------

Materials needed:

- Raspberry Pi (Model B+ recommended)
- network cable
- Class10 SD Card (lower clases will slow down operations *significantly*).
  See `this list`_ for SD cards known to work well with the Raspberry Pi.
- free ethernet port in your router/switch

1. Download the latest version of the SpreadPi disk image of SpreadPi from the
   buildbot_. It contains a fully configured Linux operating system and a
   complete installation of Spreads, ready to run.

2. Extract the image with 7-Zip_ and follow the tutorial matching your
   operating system to copy SpreadPi to the SD-Card that goes into the
   Raspberry Pi: Windows_ / `OS X`_ / Linux_.

.. note::

    For most situations, this is all you need to configure the Pi. For advanced
    users and occasional problematic setups, it is possible to SSH into the Pi
    and configure it manually. You have to use the following credentials:

    Username:
        `spreads`
    Password
        `spreads`
    Root-Password:
        `raspberry`

.. TODO: Add link to chdk documentation

3. Now that the Pi has an operating system, we need to configure our devices.
   SpreadPi currently assumes that the user is running CHDK devices, so check
   the driver documentation for how to correctly set up the cameras.

5. Connect the network cable to the Pi and your router or switch. Connect all
   devices.  Turn on the devices first, and only then turn on the Pi. The Pi
   takes a few minutes to boot for the first time - be patient. It will reboot
   once to resize the image to fit the whole SD-Card. Spreads is getting an IP
   address from your network and will display that IP address on the screens of
   your cameras for you when it is ready to begin.

.. TODO: Add link to web plugin documentation

6. Spreads has an easy-to-use web interface. Open a browser on any device that
   is on the same network as your scanner. If your smartphone or tablet is on
   your home WiFi network, you can use it to the scanner. To connect to it,
   enter the IP address that was displayed on the camera screen. Refer to the
   web plugin documentation for more information on how to use the interface.

.. _buildbot: http://buildbot.diybookscanner.org/nightly
.. _this list: http://elinux.org/RPi_SD_cards#SD_card_performance
.. _7-Zip: http://www.7-zip.org/download.html
.. _Windows: http://elinux.org/RPi_Easy_SD_Card_Setup#Flashing_the_SD_Card_using_Windows
.. _OS X:  http://elinux.org/RPi_Easy_SD_Card_Setup#Flashing_the_SD_card_using_Mac_OSX
.. _Linux: http://elinux.org/RPi_Easy_SD_Card_Setup#Flashing_the_SD_Card_using_Linux_.28including_on_a_Pi.21.29
