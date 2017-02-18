import gevent.pywsgi
import gevent.pool
import signal
import os
import urllib
from flask import Flask, abort, redirect, render_template, request, Response, session, url_for, jsonify
from werkzeug.utils import secure_filename
from uuid import uuid4
from random import randint

from task import GreenTask


UPLOAD_FOLDER = "/tmp/"
FINISHED = list()
RUNNING = dict()
session = dict()


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
    unquoted_path = secure_filename(filename)
    full_path = os.path.join(UPLOAD_FOLDER, unquoted_path)

    if not task.path_exists(full_path):
        abort(404)

    file_stat = task.stat(full_path, ('name', 'size'))
    stream = task.stream_file(full_path)

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
    task = GreenTask()

    if request.method == 'POST':

        if 'task_id' in request.form:
            task.id = request.form['task_id']

        if 'file' in request.files:
            data_file = request.files['file']
            if data_file.filename > '':
                filename = secure_filename(data_file.filename)
                full_file_name = os.path.join(UPLOAD_FOLDER, filename)

                session[task.id] = {'full_file_name': full_file_name,
                                    'progress': 0,
                                    'parse_status': None}

                task.save_file_by_chunks(data_file, session)

    return render_template('upload_file.html', task_id=task.id)


def status(task_id):
    if request.method == 'GET':
        if task_id in session:
            result = ''

            task = GreenTask()
            task.id = task_id

            # we need to run file parsing only once for each file
            if session[task.id]['parse_status'] is None:
                result = task.parse_file(session).value

            return render_template('status.html', task_id=task_id, result=result)

    # if request has incorrect data:
    return redirect('/')


def parsing_file_progress(task_id):
    progress = session.get(task_id, {}).get('progress', 0)
    return jsonify({'status': progress})


def create_app():
    app = Flask(__name__)
    app.secret_key = "F12Zr47j\3yX R~X@H!jmM]Lwf/,?KT"
    app.add_url_rule('/', 'files', files)
    app.add_url_rule('/download/<filename>', 'get_file', get_file)
    app.add_url_rule('/upload', 'upload_file', upload_file, methods=['GET', 'POST'])
    app.add_url_rule('/status/<task_id>', 'status', status)
    app.add_url_rule('/progress/<task_id>', 'parsing_file_progress', parsing_file_progress)
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


if __name__ == "__main__":
    run()
