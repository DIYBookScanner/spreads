import shutil
import tempfile
import unittest

from mock import call, patch, MagicMock as Mock
from spreads.vendor.pathlib import Path

import spreads.confit as confit
import spreads.plugin as plugin
import spreads.util
spreads.util.find_in_path = Mock(return_value=True)
import spreadsplug.autorotate as autorotate


class TestAutorotate(unittest.TestCase):
    def setUp(self):
        self.config = confit.Configuration('test_autorotate')
        self.config['autorotate']['rotate_odd'] = -90
        self.config['autorotate']['rotate_even'] = 90
        self.path = Path(tempfile.mkdtemp())
        (self.path / 'raw').mkdir()

    def tearDown(self):
        shutil.rmtree(unicode(self.path))

    def test_process(self):
        test_files = [self.path / 'raw' / x
                      for x in ('000.jpg', '001.jpg', '002.jpg')]
        map(lambda x: x.touch(), test_files)
        mock_exifs = [Mock(), Mock(), Mock()]
        for item, orient in zip(mock_exifs, (6, 8, -1)):
            item.exif.primary.Orientation = [orient]
        autorotate.JpegFile = Mock()
        autorotate.JpegFile.fromFile = Mock(side_effect=mock_exifs)
        mock_pool = Mock()
        autorotate.futures.ProcessPoolExecutor = Mock(return_value=mock_pool)
        plug = autorotate.AutoRotatePlugin(self.config)
        plug.process(self.path)
        assert autorotate.JpegFile.fromFile.call_count == 3
        mock_pool.__enter__().submit.assert_has_calls([
            call(autorotate.rotate_image, test_files[0], rotation=90),
            call(autorotate.rotate_image, test_files[1], rotation=-90)
        ])

    def test_process_inverse(self):
        test_files = [self.path / 'raw' / '000.jpg']
        map(lambda x: x.touch(), test_files)
        mock_exif = Mock()
        mock_exif.exif.primary.Orientation = [6]
        autorotate.JpegFile = Mock()
        autorotate.JpegFile.fromFile = Mock(return_value=mock_exif)
        mock_pool = Mock()
        autorotate.futures.ProcessPoolExecutor = Mock(return_value=mock_pool)
        self.config['autorotate']['rotate_odd'] = 90
        self.config['autorotate']['rotate_even'] = -90
        plug = autorotate.AutoRotatePlugin(self.config)
        plug.process(self.path)
        mock_pool.__enter__().submit.assert_called_with(
            autorotate.rotate_image, test_files[0], rotation=-90
        )

    def test_rotate_image(self):
        mock_img = Mock()
        mock_img.__enter__().height = 200
        mock_img.__enter__().width = 800
        autorotate.wand.image.Image = Mock(return_value=mock_img)
        autorotate.rotate_image('foo.jpg', 90)
        assert mock_img.__enter__().rotate.call_args_list == [call(90)]
        assert mock_img.__enter__().save.call_args_list == [
            call(filename='foo.jpg')]
