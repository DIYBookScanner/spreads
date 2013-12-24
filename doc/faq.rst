Frequently Asked Questions
==========================

CHDK Cameras
------------

... When capturing, the commands frequently time out.

    This is a known issue when both cameras are connected to the same USB hub.
    It seems to occur less frequently with powered USB hubs, but the safest
    way to avoid these hickups is to connect each device to a separate USB
    hub/port. You might also want to try another USB cable.

... ``USBError: [Errno 13] Access denied (insufficient permissions)``

    This means that your user is not allowed to write to the camera devices.
    To temporarily fix this, run ``$ sudo chmod -R a+rw /dev/bus/usb/*``.
    To permanently fix the permissions, create a new udev rule that sets
    the permissions when the devices are plugged in.
