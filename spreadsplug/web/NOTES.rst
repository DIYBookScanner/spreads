DESIGN NOTES
============

General
-------
* RESTful API to control workflow
* Single page web application to communicate with API
* Primary Goal: Run on RPi as scanning station, controlled via browser,
                run on more powerful machine for postprocessing + output
                generation

Issues
------
* Will probably force us to do a refactor of the spreads core:
    - Encapsulate everything project-specific into a "SpreadProject" class
    - Make plugin configuration auto-discoverable, so we don't have to hardcode
      CLI switches, web configuration
* Handling device locks is going to be a problem, we have to store somewhere
  globally accessible which USB ports are in use and prevent the creation of
  SpreadsDevice objects for them.

Technologies
------------
* Server-side: Flask
* Client-side: AngularJS

Modes
-----
* Modes are selectable via their subcommand

web-slave
+++++++++
* Expose prepare, capture, download steps
* Flow:
    - User sets up project configuration
    - Check for cameras, notify users if they're offline
    - Display preview images, logbox and buttons to trigger capture
    - Wait for user to signalize finish, download the images
    - Send project configuration and images to postprocess machine endpoint
* UI:
    - Current workflow step actions and information
    - Option to cancel current workflow
    - Option to edit configuration

web-master
++++++++++
* Expose postprocess, output steps
* Flow:
  - Receive project configuration
  - Receive individual raw images
  - Wait until it's the project's turn in the queueu
  - Perform postprocess workflow steps
    For scantailor: Disable output-generation, make project file downloadable,
    wait for user to upload adjusted project file, then do output generation,
    will have to adapt scantailor-plugin to make this work)
* UI:
  - Project queue with options to cancel, change priority, view information
  - View raw/processed images for each project
  - Download/Upload ScanTailor configuration
  - Download raw package, done package, individual output files

web-full
++++++++
* Expose all workflow steps
* Flow:
  - Same as web-slave and web-master, one after the other
* UI:
  - Both combined
