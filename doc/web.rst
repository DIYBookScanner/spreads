Web Interface
=============

Installation
------------
To install the required dependencies for the web plugin, run the following
command::

    $ pip install spreads[web]

Alternatively, make sure you have the following modules installed in their
most recent versions:

* Flask
* Flask-Compress
* jpegtran-cffi
* requests
* waitress
* zipstream

To use the JavaScript web interface, make sure you use a recent version of
Firefox or Chrome.

Startup and Configuration
-------------------------
You can launch the web interface with its subcommand::

    $ spread web [OPTIONS]

This will serve the spreads web interface and its RESTish-API on port 5000
for the whole network. There are a number of options with which you can


.. option:: --database <path>

   Location of workflow database, by default `~/.config/spreads/workflows.db`

.. option:: --standalone-device

   Enable standalone mode. This option can be used for devices that are
   dedicated to scanning (e.g. a RaspberryPi that runs spreads and nothing
   else). At the moment the only additional feature it enables is the ability
   to shutdown the device from the web interface and REST API.

.. option:: --debug

   Run the application in debugging mode. This activates source maps in the
   client-side code, which will increase the initial loading time significantly.

.. option:: --project-dir <path>

   Location where workflow files are stored. By default this is `~/scans`.


Interface
---------
You can connect to the interface by opening your browser on an address that
looks like this::

    http://<host-ip-address>:5000

If you are running spreads in your local machine, using `localhost` or
`127.0.0.1` for the IP address will be enough. If you are running it on a
remote machine, you will have to find out its IP address. When you are
using CHDK cameras and have them turned on when you launch spreads, their
displays will show the IP address of the computer they are connected to.

The **initial screen** will list all previously created workflows with a small
preview image and some information on their status. On clicking one of the
workflows, you will be taken to its details page where you can view all
of the images and see more information on it. You can also choose to download
a ZIP file with the workflow, containing all images and a configuration file.

.. TODO: workflow list screenshot

From the navigation bar, you can choose to **create a new workflow**. The only
setting you absolutely have to enter is the workflow name. You can also change
driver and plugin settings for this workflow by selecting either one from the
dropdown menu. When you are done, you can submit the workflow and the
application will take you to the capture screen.

.. TODO: workflow creation screenshot

On the **capture screen**, you can see two small review images with which
you can verify that the last capture went well. Trigger a new capture by
clicking the appropriate button and you will see the images update.
If you spotted an error, you can click the *Rektake* button, which will discard
the last capture and trigger a new one. Once you are done, use the *finish*
button.

.. TODO: Capture interface screenshot
