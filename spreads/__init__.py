"""
spreads package

This is the core package for spreads. Except for the :py:mod:`spreads.cli`
and :py:mod:`spreads.main` modules (which contain the logic for the `spread`
command-line application) everything in this package is UI-agnostic and designed
to be used from plugins in the `spreadsplug` namespace.

It includes the following modules (in no particular order):

:py:mod:`spreads.main`
    Core logic for application startup and parsing of command-line arguments

:py:mod:`spreads.cli`
    Implementation of the command-line interface, i.e. the `configure`,
    `capture`, `postprocess`, `output` and `wizard` subcommands.

:py:mod:`spreads.config`
    Classes for working with configuration, both per-workflow and
    application-wide. Most important for plugin developers is the
    :py:class:`spreads.config.OptionTemplate` class, which allows for the
    UI-agnostic declaration of configuration options.

:py:mod:`spreads.workflow`
    This is by far the largest module in the core and contains the
    :py:class:`spreads.workflow.Workflow` class that is the central entity
    in the application. Also included are classes for representing single
    page entities and TOC-entries, as well as various signals that can be
    emitted by a workflow entity.

:py:mod:`spreads.metadata`
    Contains the :py:class:`spreads.metadata.Metadata` entity class that
    manages the reading and writing of metadata values.

:py:mod:`spreads.plugin`
    The most important module for plugin authors. It contains the various
    interfaces (all inheriting from :py:class:`spreads.plugin.SpreadsPlugin`)
    that plugins and device drivers can implement, as well as functions
    (intended for use by the core) to enumerate and initialize plugins and
    device drivers.

:py:mod:`spreads.util`
    Various helper functions that can be useful for both plugin authors and
    the core. Also contains the various :py:class:`Exception` subclasses
    used throughout the core and the plugin interface.

:py:mod:`spreads.tkconfigure`
    Implementation of the graphical configuration dialog (accessible via the
    `guiconfigure` subcommand), using the Tkinter bindings from Python's
    standard library.
"""
