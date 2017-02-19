import unittest
import mock
from uuid import uuid4

from filestreamer import task


class TaskTestCase(unittest.TestCase):
    
    def test_task_executor(self):
        """ This test checks that we can create instance of
            GreenTaskExecutor class, run test function and get
            the result of execution of this function.
        """

        def test_function(a):
            return a*2

        test_data = 25
        expected_result = test_function(test_data)

        # create GreenTaskExecutor instance and test function
        # in the separate thread:
        task_executor = task.GreenTaskExecutor(max_workers=1)
        result = task_executor.green_submit(test_function, test_data)

        # verify the result of the execution is correct:
        assert result.value == expected_result

    def test_green_task_uuid(self):
        """ This test checks that different tasks have different ids. """

        t1 = task.GreenTask()
        t2 = task.GreenTask()

        assert t1.id != t2.id

    @mock.patch('filestreamer.task.stat.S_ISDIR')
    @mock.patch('filestreamer.task.os.stat')
    @mock.patch('filestreamer.task.os.listdir')
    def test_list_dir(self, os_list, os_stat, check_dir):
        """ This test checks listdir method. """

        files_list = ['test1', 'test2']
        expected_result = [{'name': 'test1', 'size': 1.0},
                           {'name': 'test2', 'size': 1.0}] 

        # configure mock to get proper expected data:
        files_list = ['test1', 'test2']
        os_list.return_value = files_list
        os_stat.return_value = mock.MagicMock(st_size=1.0)
        check_dir.return_value = False

        t1 = task.GreenTask()

        # get list of files:
        result = t1.listdir('/tmp', ['name', 'size'])

        # make sure we got expected data with all required keys:
        assert result == expected_result

    @mock.patch('filestreamer.task.open', new_callable=mock.mock_open,
                read_data="test")
    @mock.patch('filestreamer.task.os.path.getsize', return_value=4)
    def test_parse_file(self, mget_size, mopen):
        """ This test checks parse_file method. """

        t1 = task.GreenTask()
        session = {t1.id: {'full_file_name': 'test'}}

        result = t1.parse_file(session)

        # we expect that parse_file will return "4" because it is
        # length of data which was described in read_data parameter for
        # mock_open object:
        assert result == 4

    def test_stat(self):
        """ This test checks stat method. """

        missed_fields = []
        required_fields = ['exists', 'type', 'name', 'mode', 'size',
                           'atime', 'mtime', 'ctime']

        # get infromation about test file:
        t1 = task.GreenTask()
        result = t1.stat('test_file', required_fields)

        # make sure we got all required information:
        for field in required_fields:
            if field not in result:
                missed_fields.append(field)

        assert missed_fields == []

    def test_path_exists(self):
        """ This test checks path_exists method. """

        test_paths = {'/': True, str(uuid4()): False}
        expected_results = [i for i in test_paths.values()]

        # get the infomration about existing and non existing paths:
        t1 = task.GreenTask()
        results = [t1.path_exists(i) for i in test_paths.keys()]

        # verify that results are correct:
        assert results == expected_results

    @mock.patch('filestreamer.task.gevent.fileobject.FileObjectThread',
                new_callable=mock.mock_open, read_data="test data")
    @mock.patch('filestreamer.task.open')
    def test_stream_file(self, mopen, obj_thread):
        """ This test checks stream_file method. """

        expected_data = 'test data'

        # read data from mock file:
        t1 = task.GreenTask()
        results = t1.stream_file('test')

        data = ''.join([r for r in results])

        # verify that stream_file method returns correct data:
        assert data == expected_data

