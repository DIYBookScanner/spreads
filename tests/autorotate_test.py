import mock
import shutil

from spreads.vendor.pathlib import Path

import spreadsplug.autorotate as autorotate
from spreads.workflow import Page


# TODO: Test if latest processed_image is rotated if present
# TODO: Test if non-jpg files are skipped


def test_process():
    # No need for confit.Configuration, since the plugin doesn't have any
    # configuration
    config = {'autorotate': None}
    pages = [Page(Path('{0:03}.jpg'.format(idx))) for idx in xrange(4)]
    target_path = Path('/tmp/dummy')

    with mock.patch('spreadsplug.autorotate.ProcessPoolExecutor') as mockctx:
        plugin = autorotate.AutoRotatePlugin(config)
        pool = mockctx.return_value.__enter__.return_value
        plugin.process(pages, target_path)
        # The text file should not have been passed
        assert pool.submit.call_count == 4
        # We only want the second parameter to submit, the first is the
        # function to call
        assert sorted([unicode(p.raw_image) for p in pages]) == (
            sorted(x[0][1] for x in pool.submit.call_args_list))


def test_autorotate_image(tmpdir):
    in_path = tmpdir.join('foo.jpg')
    out_path = tmpdir.join('foo_rotated.jpg')
    shutil.copyfile('./tests/data/odd.jpg', unicode(in_path))

    with mock.patch('spreadsplug.autorotate.JPEGImage') as mockcls:
        img = mock.Mock()
        mockcls.return_value = img
        img.exif_orientation = 1
        autorotate.autorotate_image(unicode(in_path), unicode(out_path))
        assert img.exif_autotransform.call_count == 0
        assert out_path.exists()

        img.exif_orientation = None
        autorotate.autorotate_image(unicode(in_path), unicode(out_path))
        assert img.exif_autotransform.call_count == 0
        assert out_path.exists()

        img.exif_orientation = 6
        img.exif_autotransform.return_value = mock.Mock()
        autorotate.autorotate_image(unicode(in_path), unicode(out_path))
        assert img.exif_autotransform.call_count == 1
        img.exif_autotransform.return_value.save.assert_called_with(
            unicode(out_path))
