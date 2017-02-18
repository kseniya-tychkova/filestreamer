import ntpath
import os
import stat
import datetime as dt
from uuid import uuid4

from concurrent import futures
import gevent.event
import gevent.fileobject
import gevent.local


class GreenTaskExecutor(futures.ThreadPoolExecutor):
    """ This class describes tasks executor. """

    @staticmethod
    def future_result_to_async_result(async_result, future):
        try:
            result = future.result()
        except Exception as e:
            async_result.set_exception(e)
        else:
            async_result.set(result)

    def green_submit(self, fn, *args, **kwargs):
        async_result = gevent.event.AsyncResult()
        future = self.submit(fn, *args, **kwargs)
        delay = 0.001
        while not future.done():
            gevent.sleep(delay)
            delay = delay * 2 if delay < 1 else 1
        self.future_result_to_async_result(async_result, future)
        return async_result


class GreenTask(object):
    """ This class allows to do all operations with files. """

    def __init__(self):
        self.CHUNK_SIZE = 512 * 1024
        self.id = str(uuid4())
        self.status = None

        self._pool = GreenTaskExecutor(
            max_workers=10)

    def blocking_listdir(self, path, fields):
        """ This function returns the list of files in the upload dir. """

        try:
            objects = os.listdir(path)
        except OSError:
            return None

        result = [self.blocking_stat(os.path.join(path, name), fields)
                  for name in objects]
        return result

    def blocking_stat(self, path, fields):
        """ This function returns the attributes of file. """

        head, tail = ntpath.split(path)
        name = tail or ntpath.basename(head)
        full_result = {'name': name}
        try:
            info_stat = os.stat(path)
        except OSError:
            full_result.update({
                'exists': False,
                'type': 'file',
            })
        else:
            full_result.update({
                'exists': True,
                'type': ('directory' if stat.S_ISDIR(info_stat.st_mode)
                         else 'file'),
                'name': name,
                'mode': info_stat.st_mode,
                'size': info_stat.st_size,
                'atime': dt.datetime.fromtimestamp(info_stat.st_atime).strftime('%d-%m-%Y %H:%M:%S'),
                'mtime': dt.datetime.fromtimestamp(info_stat.st_mtime).strftime('%d-%m-%Y %H:%M:%S'),
                'ctime': dt.datetime.fromtimestamp(info_stat.st_ctime).strftime('%d-%m-%Y %H:%M:%S')
            })
        return {field: full_result.get(field) for field in fields}

    def blocking_path_exists(self, path):
        return os.path.exists(path)

    def blocking_save_file_by_chunks(self, data, session):
        """ This function reads stream data and saves it to file. """

        full_path = session[self.id]['full_file_name']

        with open(full_path, "wb") as f:
            while True:
                chunk = data.stream.read(self.CHUNK_SIZE)

                if len(chunk) == 0:
                    break

                f.write(chunk)

    def save_file_by_chunks(self, data, session):
        """ This function will create a separate thread to upload file. """

        return self._pool.green_submit(self.blocking_save_file_by_chunks,
                                       data, session).get()

    def blocking_parse_file(self, session):
        """ This function calculates the count of characters in file. """

        progress = 0
        results = []

        file_name = session[self.id]['full_file_name']
        file_size = os.path.getsize(file_name)
        chunks_total = 1 + file_size / self.CHUNK_SIZE

        with open(file_name) as f:
            # we need to slice large file to chunks to avoid
            # RAM over ussage:
            data = iter(lambda: f.read(self.CHUNK_SIZE), '')

            for chunk in data:
                chunk = chunk.replace('\n', '').replace('\r', '')
                results.append(len(chunk))

                progress += 1
                session[self.id]['progress'] = 100.0 * progress / chunks_total

        return sum(results)

    def parse_file(self, session):
        """ This function will run parsing of file in a separate thread. """

        return self._pool.green_submit(self.blocking_parse_file, session).get()

    def listdir(self, path, fields):
        return self._pool.green_submit(self.blocking_listdir, path, fields).get()

    def stat(self, path, fields):
        return self._pool.green_submit(self.blocking_stat, path, fields).get()

    def path_exists(self, path):
        return self._pool.green_submit(self.blocking_path_exists, path).get()

    def stream_file(self, mounted_path):
        """ This is a generator which returns large files in small chunks. """

        with open(mounted_path, 'rb') as fobj:
            stream = gevent.fileobject.FileObjectThread(fobj)
            while True:
                try:
                    chunk = stream.read(self.CHUNK_SIZE)
                except IOError as e:
                    return
                if chunk:
                    received = len(chunk)/1024
                    yield chunk
                else:
                    return
