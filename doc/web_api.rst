HTTP API
--------
The web plugin also exposes all of its functions through a REST-ish API.
You can use it to write small scripts or even for a full-blown Android
or iPhone application, if you feel so inclined.

.. autoflask:: spreadsplug.web.app:app
   :undoc-endpoints: index, redirect_pushstate
