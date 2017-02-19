import unittest
import mock

from uuid import uuid4
from bs4 import BeautifulSoup
from StringIO import StringIO

from filestreamer import application


class FilestreamerWebUITestCase(unittest.TestCase):

    def setUp(self):
        app = application.create_app()
        app.config['TESTING'] = True
        self.app = app.test_client()

    def test_get_index_page(self):
        rv = self.app.get('/')
        data = BeautifulSoup(rv.data, 'html.parser')
        assert data.title.string == "Filestreamer"

    def test_get_index_page_and_verify_table(self):
        rv = self.app.get('/')
        data = BeautifulSoup(rv.data, 'html.parser')

        table_captions = data.find_all('th')
        captions_list = [i.string for i in table_captions]

        expected_list = ['Filename', 'Date', 'Size', None] 

        assert captions_list == expected_list

    def test_get_upload_page(self):
        rv = self.app.get('/upload')
        data = BeautifulSoup(rv.data, 'html.parser')
        input_file = data.find(type='file')
        assert input_file['name'] == 'file'

    @mock.patch('filestreamer.task.open')
    def test_post_upload_page(self, mopen): 

        session_id = str(uuid4())

        expected_write_calls = [mock.call.write('my file contents')]
        data = {'file': (StringIO('my file contents'), 'test.txt'),
                'task_id': session_id}

        self.app.post('/upload', data=data, follow_redirects=True)

        # verify that all expected data was saved to the mock file object:
        handle = mopen().__enter__()
        handle.assert_has_calls(expected_write_calls)
