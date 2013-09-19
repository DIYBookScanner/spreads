import itertools
import logging

from spreads import plugin


logger = logging.getLogger('spreadsplug.web.common')


def get_relevant_extensions(hooks):
    # NOTE: This one is wicked... The goal is to find all extensions that
    #       implement one of the steps relevant to this component.
    #       To do so, we compare the code objects for the appropriate
    #       hook method with the same method in the HookPlugin base class.
    #       If the two are not the same, we can (somewhat) safely assume
    #       that the extension implements this hook and is thus relevant
    #       to us.
    #       Yes, this is not ideal and is due to our somewhat sloppy
    #       plugin interface. That's why...
    # TODO: Refactor plugin interface to make this less painful
    for ext in plugin.get_pluginmanager():
        relevant = any(
            getattr(ext.plugin, hook).func_code is not
            getattr(plugin.HookPlugin, hook).func_code
            for hook in hooks
        )
        if relevant:
            yield ext


def get_configuration_template(hooks):
    out_dict = {'general': {}}
    if 'capture' in hooks:
        out_dict['general']['dpi'] = {'value': 300,
                                      'docstring': "Device resolution",
                                      'selectable': False}
    if 'download' in hooks:
        out_dict['download'] = {
            'keep': {'value': False,
                     'docstring': 'Keep files on devices after download',
                     'selectable': False}
        }
    relevant_extensions = get_relevant_extensions(hooks)
    device_extensions = (x[0] for x in plugin._get_device_extension_matches())
    logger.debug("Relevant extensions: {0}"
                 .format([ext.name for ext in relevant_extensions]))
    for ext in itertools.chain(relevant_extensions, device_extensions):
        tmpl = ext.plugin.configuration_template()
        if not tmpl:
            continue
        out_dict[ext.name] = {k: {'value': v.value, 'docstring': v.docstring,
                                  'selectable': v.selectable}
                              for k, v in tmpl.iteritems()}
    return out_dict
