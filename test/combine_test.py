from mock import call, patch, MagicMock as Mock

import spreads
import spreadsplug.combine as combine

spreads.util.find_in_path = Mock(return_value=True)


class TestCombine(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['first_page'] = 'left'
        self.plug = combine.CombinePlugin(spreads.config)

    @patch('os.path.exists')
    @patch('os.mkdir')
    @patch('os.listdir')
    def test_combine(self, exists, mkdir, listdir):
        exists.return_value = False
        listdir.side_effect = (['a.jpg', 'b.jpg', 'c.jpg', 'd.jpg'],
                               ['a.jpg', 'b.jpg', 'c.jpg', 'd.jpg'])
        combine.os.path.exists = exists
        combine.os.mkdir = mkdir
        combine.os.listdir = listdir
        combine.shutil = Mock()
        mock_cams = [Mock(), Mock()]
        self.plug.download(mock_cams, '/tmp/foo')
        out_tree = [x[0][1] for x in combine.shutil.copyfile.call_args_list]
        assert out_tree == ['/tmp/foo/raw/0000.jpg', '/tmp/foo/raw/0001.jpg',
                            '/tmp/foo/raw/0002.jpg', '/tmp/foo/raw/0003.jpg',
                            '/tmp/foo/raw/0004.jpg', '/tmp/foo/raw/0005.jpg',
                            '/tmp/foo/raw/0006.jpg', '/tmp/foo/raw/0007.jpg']
        assert combine.shutil.rmtree.call_count == 2

    @patch('os.path.exists')
    @patch('os.mkdir')
    @patch('os.listdir')
    def test_combine_inequal(self, exists, mkdir, listdir):
        exists.return_value = False
        listdir.side_effect = (['a.jpg', 'b.jpg', 'c.jpg'],
                               ['a.jpg', 'b.jpg', 'c.jpg', 'd.jpg'])
        combine.os.path.exists = exists
        combine.os.mkdir = mkdir
        combine.os.listdir = listdir
        combine.shutil = Mock()
        mock_cams = [Mock(), Mock()]
        self.plug.download(mock_cams, '/tmp/foo')
        out_tree = [x[0][1] for x in combine.shutil.copyfile.call_args_list]
        assert out_tree == []
        assert combine.shutil.rmtree.call_count == 0
