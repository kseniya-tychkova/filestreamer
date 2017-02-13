from concurrent import futures
import ntpath
import time
import datetime as dt
import stat
import gevent.event
import gevent.fileobject
import gevent.local
import os
from uuid import uuid4


class GreenTaskExecutor(futures.ThreadPoolExecutor):

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
    CHUNK_SIZE = 512 * 1024

    def __init__(self):
        self.id = uuid4()
        self.status = None
        self._pool = GreenTaskExecutor(
            max_workers=10)

    def blocking_listdir(self, path, fields):
        try:
            objects = os.listdir(path)
        except OSError:
            return None

        result = [self.blocking_stat(os.path.join(path, name), fields)
                  for name in objects]
        return result

    @staticmethod
    def blocking_stat(path, fields):
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

    @staticmethod
    def blocking_path_exists(path):
        return os.path.exists(path)

    @staticmethod
    def blocking_save_file(file_, path, name):
        file_.save(os.path.join(path, name))

    def listdir(self, path, fields):
        return self._pool.green_submit(self.blocking_listdir, path, fields).get()

    def stat(self, path, fields):
        return self._pool.green_submit(self.blocking_stat, path, fields).get()

    def path_exists(self, path):
        return self._pool.green_submit(self.blocking_path_exists, path).get()

    def stream_file(self, mounted_path):
        with open(mounted_path, 'rb') as fobj:
            stream = gevent.fileobject.FileObjectThread(fobj)
            while True:
                try:
                    start = time.time()
                    chunk = stream.read(self.CHUNK_SIZE)
                    speed = 1. * len(chunk)/1024. / (time.time() - start)
                except IOError as e:
                    return
                if chunk:
                    received = len(chunk)/1024
                    yield chunk
                else:
                    return

    def save_file(self, file_, path, name):
        self.status = "60%"
        return self._pool.green_submit(self.blocking_save_file(file_, path, name))