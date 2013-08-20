Frequently Asked Questions
==========================

Workflow
--------

... I'm confused about the labelling of the cameras

    As a rule of thumb, assign the ``left`` and ``right`` labels according to
    your most often used way of shooting. Should you decide to switch the
    cameras or change your setup (i.e. switching to paperback mode on the
    DIYBookScanner), use the ``--first-page`` and ``--rotate-inverse``
    options to tell spreads about it during the ``download`` and ``postprocess``
    steps.

.. TODO: Be a bit more clear... Diagrams?

CHDK Cameras
------------

... I'm getting a lot of ``Script raised an error`` or ``Script timed out`` warnings

    This is a known issue when both cameras are connected to the same USB hub.
    It seems to occur less frequently with powered USB hubs, but the safest
    way to avoid these hickups is to connect each device to a separate USB
    hub. You might also want to try another USB cable.
