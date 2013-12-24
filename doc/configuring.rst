Configuration
=============
Upon first launch, *spreads* writes a configuration file to
`~/.config/spreads/config.yaml`. In it, you can change all of the available
settings to your liking. The configuration options are the same ones that
you can set on the command-line, so just call `spreads <command> --help`
to view the documentation.

.. code-block:: yaml

    # Valid values: 'none', 'debug', 'info', 'warning', 'error', 'critical'
    loglevel: warning
    plugins:
        - autorotate
        - scantailor
        - tesseract
        - gui
        - pdfbeads
        - djvubind

    # Options for 'capture' step
    capture:
         capture_keys: [' ', b]
    driver: dummy
    colorcorrect:
         true_blue: 119
         true_green: 119
         true_red: 119
    device:
         focus_distance: 384
         dpi: 300
         parallel_capture: yes
         chdkptp_path: /usr/local/lib/chdkptp
         zoom_level: 3
         shoot_raw: no
         sensitivity: 80
         flip_target_pages: no
         shutter_speed: 1/25
    tesseract:
         language: deu-frak
    autorotate:
         rotate_even: 90
         rotate_odd: -90
    scantailor:
         margins:
            - 2.5
            - 2.5
            - 2.5
            - 2.5
         auto_margins: yes
         autopilot: no
         split_pages: yes
         deskew: yes
         rotate: no
         detection: content
         content: yes
