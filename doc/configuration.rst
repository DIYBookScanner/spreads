Configuration
=============

Initial configuration
---------------------
To perform the initial configuration, launch the `configure` subcommand::

    $ spread configure

You will be asked to select a device driver and some plugins. Next, configure
the order in which your postprocessing plugins should be invoked. Think of
it as a pipelining system, where each of the plugin gets fed the output
of its predecessor.

Next, if you are using two cameras for scanning, your can the target pages for
each of your cameras. This is necessary, as the application has to:

* combine the images from both cameras to a single directory in the right order
* set the correct rotation for the captured images

To do both of these things automatically, the application needs to know if the
image is showing an odd or even page. Don't worry, you only have to perform
this step once, the orientation is stored on the camera's memory card (under
`A/OWN.TXT`). Should you later wish to briefly flip the target pages, you can
do so via the `--flip-target-pages` command-line flag.

.. note::
    If you are using a DIYBookScanner and the book is facing you, the device
    for *odd* pages is the camera on the **left**, the one for *even* pages on
    the **right**.

After that, you can choose to setup the *focus* for your devices. By default,
the focus will be automatically detected on each shot. But this can lead to
problems: Since the camera uses the center of the frame to obtain its focus,
your images will be out of focus in cases where the center of the page does not
have any text on it, e.g. in chapter endings. This step is therefore
recommended for most users. Before you continue, make sure that you have loaded
a book into the scanner, and that the pages facing the camera are evenly filled
with text or illustrations.

Once you're done, you can find the configuration file in the `.config/spreads`
folder in your home directory.


Configuration file
------------------
Upon first launch, *spreads* writes a configuration file to
`~/.config/spreads/config.yaml`. In it, you can change all of the available
settings to your liking. The configuration options are the same ones that
you can set on the command-line, so just call `spreads <command> --help`
to view the documentation. Command-line flags that begin with `--no-...`
should be entered without the `no` prefix and have `yes` or `no` as their
value.

.. code-block:: yaml

    # Names of activated plugins, postprocessing plugins will be called
    # in the order that they are entered here
    plugins: [gui, autorotate, scantailor]

    # Name of the device driver
    driver: chdkcamera

    core:
        # Enable verbose output on command-line
        verbose: no
        # Keys that trigger a capture in command-line interface
        capture_keys: [' ', b]
        # Path to logfile
        logfile: ~/.config/spreads/spreads.log
        # Loglevel for logfile
        loglevel: info

    # Device settings
    device:
        parallel_capture: yes
        flip_target_pages: no

    # Plugin settings
    tesseract:
        language: deu-frak

    scantailor:
        autopilot: no
