DESIGN NOTES
============

General
-------
* RESTful API to control workflow
* Single page web application to communicate with API
* Workflows are stored in a queue that is persisted in a SQLite database
* Only one `capture` can be active at the same time, this information is
  stored in a global application lock
* Primary Goal: Run on RPi as scanning station, controlled via browser,
                run on more powerful machine for postprocessing + output
                generation

Issues
------
* Handling device locks is going to be a problem, we have to store somewhere
  globally accessible which USB ports are in use and prevent the creation of
  SpreadsDevice objects for them.

Technologies
------------
* Server-side: Flask
* Client-side: AngularJS

Steps
-----
* Workflow steps are invoked by their name on a given workflow object
  (e.g. `/api/workflow/1/capture`)
* `capture` will trigger a single capture
* On first invocation of `postprocess` and `output`, the step will be launched,
  on subsequent requests the status of the step will be returned.
* In plugin configuration, the user can select `scanner`, `finalizer`,
  `combined`  modes, the first will only expose `capture`, the second
  only `postprocess` and `output` and the third all workflow steps.
* A GET on `/api/workflow/<id>` will always return the current workflow object,
  enriched with information about the current step and the status of the step

Base Entity: Workflow
+++++++++++++++++++++
+ Sample workflow JSON::

  { 'id': 1,
    'name': 'test_workflow',
    'current_step': 'capture',
    'workflow_status': {
        'pages_shot': 20,
        'capture_start': 1387227964.216523,
        'captured_images': ['001.jpg', '002.jpg', '003.jpg', '004.jpg']
    }
    'config': {
        'device': {
            'zoom_level': 2
        }
    }
  }



'scanner'-mode
++++++++++++++
* Expose capture step
* API-Flow:
    - User submits a workflow JSON to `/api/workflow`, gets back workflow id
    - Notify via error message if devices couldn't be found
    - User can trigger captures via a GET request on
      `/api/workflow/<id>/capture`
    - User can obtain a preview image via `/preview[/<target_page>]`
    - User can download captured images via `/images/<pagenum>.<ext>`
    - User can download zip of whole project (config+files) from `/download`
    - If only `scanner`: User can directly submit the project to postprocessing
      via `/submit`, gets returned the API endpoint for the workflow on the
      postprocessing machine

'finalizer'-mode
++++++++++++++++
* Expose postprocess, output steps
* Flow:
  - If only `finalizer`:

    * Create new workflow by POSTing workflow JSON to `/api/workflow`, get
      back workflow id
    * Set workflow status to `upload`
    * Upload individual images to `/api/workflow/<id>/images`
    * GET `/api/workflow/<id>/postprocess`

  - User GETs `/postprocess`, workflow will be put into the postprocess/output
    queue, where it will sit until its turn
  - Perform postprocess workflow steps
  - Perform output workflow steps
  - When a workflow has finished, it's status will be `done` and the user
    can see the available output files in the status, download them via
    `/download/<fname>`
