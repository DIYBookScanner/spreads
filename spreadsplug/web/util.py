from functools import wraps

from flask import request, url_for, abort
from werkzeug.contrib.cache import SimpleCache
from werkzeug.routing import BaseConverter, ValidationError

from persistence import get_workflow

logger = logging.getLogger('spreadsplug.web.util')


class WorkflowConverter(BaseConverter):
    def to_python(self, value):
        workflow_id = None
        try:
            workflow_id = int(value)
        except ValueError:
            raise ValidationError()
        workflow = get_workflow(workflow_id)
        if workflow is None:
            abort(404)
        return workflow

    def to_url(self, value):
        return unicode(value.id)


# NOTE: The cache object is global
cache = SimpleCache()


def cached(timeout=5 * 60, key='view/%s'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key % request.path
            rv = cache.get(cache_key)
            if rv is not None:
                return rv
            rv = f(*args, **kwargs)
            cache.set(cache_key, rv, timeout=timeout)
            return rv
        return decorated_function
    return decorator


def workflow_to_dict(workflow):
    out_dict = dict()
    out_dict['id'] = workflow.id
    out_dict['name'] = workflow.path.name
    out_dict['step'] = workflow.step
    out_dict['step_done'] = workflow.step_done
    out_dict['images'] = [get_image_url(workflow, x)
                          for x in workflow.images] if workflow.images else []
    out_dict['out_files'] = ([unicode(path) for path in workflow.out_files]
                             if workflow.out_files else [])
    out_dict['capture_start'] = workflow.capture_start
    out_dict['config'] = workflow.config.flatten()
    return out_dict


def get_image_url(workflow, img_path):
    img_num = int(img_path.stem)
    return url_for('.get_workflow_image', workflow=workflow, img_num=img_num)


def get_thumbnail(img_path):
    """ Return thumbnail for image.

    :param img_path:  Path to image
    :type img_path:   pathlib.Path
    :return:          The thumbnail
    :rtype:           bytestring
    """
    try:
        import pyexiv2
        logger.debug("Extracting EXIF thumbnail for {0}".format(img_path))
        metadata = pyexiv2.ImageMetadata(unicode(img_path))
        metadata.read()
        return metadata.previews[0].data
    except (IndexError, ImportError):
        logger.debug("Generating thumbnail for {0}".format(img_path))
        from wand.image import Image
        with Image(filename=unicode(img_path)) as img:
            thumb_width = int(200/(img.width/float(img.height)))
            img.sample(200, thumb_width)
            return img.make_blob()
