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

    def green_submit_nowait(self, fn, *args, **kwargs):
        async_result = gevent.event.AsyncResult()
        future = self.submit(fn, *args, **kwargs)
        return async_result


class GreenTask(object):
    CHUNK_SIZE = 512 * 1024

    def __init__(self):
        self.id = str(uuid4())
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

    def blocking_save_file_by_chunks(self, data, session):
        chunk_size = 2<<12

        full_path = session[self.id]['full_file_name']
        with open(full_path, "wb") as f:
            while True:
                chunk = data.stream.read(chunk_size)
                if len(chunk) == 0:
                    break

                f.write(chunk)

    def save_file_by_chunks(self, data, session):
        return self._pool.green_submit(self.blocking_save_file_by_chunks,
                                       data, session)

    def blocking_parse_file(self, session):
        print "BBB"
        try:
            progress = 0
            chunk_size = 2<<4 # need to select large chunks to
                          # speedup file processing
            results = []

            file_name = session[self.id]['full_file_name']
            file_size = os.path.getsize(file_name)
            chunks_total = 1 + file_size / chunk_size

            print "file name for parsing:", file_name
            print "chunks total:", chunks_total

            with open(file_name) as f:
                # we need to slice large file to chunks to avoid
                # RAM over ussage:
                data = iter(lambda: f.read(chunk_size), '')

                for chunk in data:
                    chunk = chunk.replace('\n', '').replace('\r', '')
                    results.append(len(chunk))

                    progress += 1
                    session[self.id]['progress'] = 100.0 * progress / chunks_total
                    print "TTTTT", session
                
        except Exception as e:
            print "%$$%$%%$%$%$!!", e

        return sum(results)

    def parse_file(self, session):
        print "AAAA"
        try:
            return self._pool.green_submit(self.blocking_parse_file, session)
        except Exception as e:
            print e

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
