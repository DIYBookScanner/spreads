from mock import call, patch, MagicMock as Mock

import spreads.confit as confit
import spreads.plugin as plugin
import spreads.util
spreads.util.find_in_path = Mock(return_value=True)
import spreadsplug.autorotate as autorotate


class TestAutorotate(object):
    def setUp(self):
        self.config = confit.Configuration('test_autorotate')
        self.config['autorotate']['rotate_odd'] = -90
        self.config['autorotate']['rotate_even'] = 90

    @patch('os.listdir')
    def test_process(self, listdir):
        listdir.return_value = ['odd.jpg', 'even.jpg', 'invalid.jpg']
        mock_exifs = [Mock(), Mock(), Mock()]
        for item, orient in zip(mock_exifs, (6, 8, -1)):
            item.exif.primary.Orientation = [orient]
        autorotate.os.listdir = listdir
        autorotate.JpegFile = Mock()
        autorotate.JpegFile.fromFile = Mock(side_effect=mock_exifs)
        mock_pool = Mock()
        autorotate.futures.ProcessPoolExecutor = Mock(return_value=mock_pool)
        plug = autorotate.AutoRotatePlugin(self.config)
        plug.process('/tmp/foobar')
        assert autorotate.JpegFile.fromFile.call_count == 3
        assert mock_pool.__enter__().submit.call_args_list == [
            call(autorotate.rotate_image, '/tmp/foobar/raw/odd.jpg',
                 rotation=90),
            call(autorotate.rotate_image, '/tmp/foobar/raw/even.jpg',
                 rotation=-90)
        ]

    @patch('os.listdir')
    def test_process_inverse(self, listdir):
        listdir.return_value = ['foo.jpg']
        mock_exif = Mock()
        mock_exif.exif.primary.Orientation = [6]
        autorotate.os.listdir = listdir
        autorotate.JpegFile = Mock()
        autorotate.JpegFile.fromFile = Mock(return_value=mock_exif)
        mock_pool = Mock()
        autorotate.futures.ProcessPoolExecutor = Mock(return_value=mock_pool)
        self.config['autorotate']['rotate_odd'] = 90
        self.config['autorotate']['rotate_even'] = -90
        plug = autorotate.AutoRotatePlugin(self.config)
        plug.process('/tmp/foobar')
        assert mock_pool.__enter__().submit.call_args_list == [
            call(autorotate.rotate_image, '/tmp/foobar/raw/foo.jpg',
                 rotation=-90)
        ]

    def test_rotate_image(self):
        mock_img = Mock()
        mock_img.__enter__().height = 200
        mock_img.__enter__().width = 800
        autorotate.wand.image.Image = Mock(return_value=mock_img)
        autorotate.rotate_image('foo.jpg', 90)
        assert mock_img.__enter__().rotate.call_args_list == [call(90)]
        assert mock_img.__enter__().save.call_args_list == [
            call(filename='foo.jpg')]
