import gevent.pywsgi
import gevent.pool
import signal
import os
import urllib
from flask import Flask, abort, make_response, render_template, request, Response
from werkzeug.utils import secure_filename
from uuid import uuid4

from task import GreenTask


UPLOAD_FOLDER = "/home/xusha/dev/test"


def files():
    task = GreenTask()
    global_path = UPLOAD_FOLDER
    unquoted_path = urllib.unquote(global_path)
    fields = ("type", "name", "size", "ctime", "mtime", "exists")

    result = task.listdir(unquoted_path, list(fields))

    if result is None:
        abort(404)
    return render_template('files.html', files=result)


def get_file(filename):
    task = GreenTask()
    unquoted_path = urllib.unquote(filename)
    global_path = UPLOAD_FOLDER
    mounted_path = os.path.join(global_path, unquoted_path)
    if not task.path_exists(mounted_path):
        raise abort(404)

    file_stat = task.stat(mounted_path, ('name', 'size'))
    stream = task.stream_file(mounted_path)

    def generate():
        while True:
            chunk = next(stream)
            if chunk:
                yield chunk
            else:
                break
    response = Response(generate())
    response.headers['Content-Type'] ='application/octet-stream'
    response.headers['Content-Disposition'] = 'attachment; filename=' + urllib.quote(file_stat['name'])
    response.headers['Content-Length'] = file_stat['size']
    response.headers['Cache-Control'] = 'must-revalidate'
    return response


def upload_file():
    if request.method == 'GET':
        return render_template('upload_file.html')
    if request.method == 'POST':
        print request
        if 'file' in request.files:
            data_file = request.files['file']
            print data_file.filename
            if data_file.filename > '':
                session = uuid4()
                print session
                filename = secure_filename(data_file.filename)
                task = GreenTask()
                task.local.session = session
                task.blocking_save_file(data_file, UPLOAD_FOLDER, filename)
                return render_template('upload_file.html')
                #return Response()
                #return render_template('upload_file_progress.html', session=session)


def upload_file_progress():
    if request.method == 'GET':
        task = GreenTask()
        return render_template('status.html', id=task.local.session)



def create_app():
    app = Flask(__name__)
    app.add_url_rule('/', 'files', files)
    app.add_url_rule('/download/<filename>', 'get_file', get_file)
    app.add_url_rule('/upload', 'upload_file', upload_file, methods=['GET', 'POST'])
    app.add_url_rule('/status', 'upload_file_progress', upload_file_progress)
    return app


def shutdown(server):
    server.close()


def run():
    app = create_app()
    pool = gevent.pool.Pool(10)
    server = gevent.pywsgi.WSGIServer(('0.0.0.0', 8080),
                                      application=app, spawn=pool)
    gevent.signal(signal.SIGTERM, shutdown, server)
    gevent.signal(signal.SIGINT, shutdown, server)
    server.serve_forever()


def main():
    run()

if __name__ == "__main__":
    main()