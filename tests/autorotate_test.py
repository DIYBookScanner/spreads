import mock

from spreads.vendor.pathlib import Path

import spreadsplug.autorotate as autorotate


def test_process():
    # No need for confit.Configuration, since the plugin doesn't have any
    # configuration
    config = {'autorotate': None}
    path = mock.MagicMock(wraps=Path('/tmp/foobar'))
    files = [u'001.jpg', u'002.jpg', u'003.jpg', u'004.jpg', u'foo.txt']
    (path/'raw').iterdir.return_value = files

    with mock.patch('concurrent.futures.ProcessPoolExecutor') as mockctx:
        plugin = autorotate.AutoRotatePlugin(config)
        pool = mockctx.return_value.__enter__.return_value
        plugin.process(path)
        # The text file should not have been passed
        assert pool.submit.call_count == 4
        # We only want the second parameter to submit, the first is the
        # function to call
        assert sorted(files[:-1]) == (
            sorted(x[0][1] for x in pool.submit.call_args_list))


def test_autorotate_image():
    path = '/tmp/foo.jpg'

    with mock.patch('spreadsplug.autorotate.JPEGImage') as mockcls:
        img = mock.Mock()
        mockcls.return_value = img
        img.exif_orientation = 1
        autorotate.autorotate_image(path)
        assert img.exif_autotransform.call_count == 0

        img.exif_orientation = None
        autorotate.autorotate_image(path)
        assert img.exif_autotransform.call_count == 0

        img.exif_orientation = 6
        autorotate.autorotate_image(path)
        assert img.exif_autotransform.call_count == 1
