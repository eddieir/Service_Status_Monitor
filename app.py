import datetime
import re
import sqlite3
import subprocess
import threading
import time
from contextlib import closing
from functools import wraps
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, g, request, jsonify, session, abort
from gpu.utils import gpu_status

"""
Server status:
-1 UNKNOWN
0  DOWN
1  HEALTHY
Server/App state:
1  On monitor
0  Stop monitor
"""

app = Flask(__name__)
DATABASE = 'monitor.db'
config = app.config
config.from_object(__name__)
app.secret_key = "secret?"
config['SERVER_NAME'] = "127.0.0.1:5006"
config['threaded'] = True
config['HTTPS'] = False
config['SESSION_COOKIE_DOMAIN'] = config['SERVER_NAME']
config['SESSION_COOKIE_PATH'] = '/'
server_base = ['http://',
               'https://'][int(config['HTTPS'])] + config['SERVER_NAME']
cron = BackgroundScheduler()
cron.start()

machines_status = {}


def call_proc(cmd):
    output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    return output


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()


def query_db(query, args=(), one=False, mode='query'):
    cur = g.db.execute(query, args)
    if mod == 'modify':
        g.db.commit()
        return cur.lastrowid

    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]

    return (rv[0] if rv else None) if one else rv


@app.before_request
def before_request():
    g.db = connect_db()


@app.after_request
def after_request(response):
    g.db.close()
    response.headers['Access-Control-Allow-Origin'] = request.headers.get(
        'Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# Front end
@app.route('/')
def index():
    return app.send_static_file("index.html")

# API
@app.route('/login/', methods=['POST'])
def login():
    data = request.get_json()
    if data is None:
        return abort(400)

    username, password = data.get('username'), data.get('password')
    rs = query_db('select * from Users where username = ? and password = ?',
                  [username, password], one=True)
    if rs is not None:
        session['logged_in'] = rs
        return jsonify({'code': 200, 'data': 'success'})
    return abort(403)


@app.route('/is_login/', methods=['GET'])
def is_login():
    if not session.get('logged_in'):
        return jsonify({'code': 200, 'data': False})
    else:
        return jsonify({'code': 200, 'data': session.get('logged_in')})


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') is None:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/logout/', methods=['POST'])
@login_required
def logout():
    session.pop('logged_in', None)
    return jsonify({'code': 200, 'data': 'success'})


@app.route('/users/', methods=['GET'])
@login_required
def get_users():
    rs = query_db('select id,username from Users')
    return jsonify({'code': 200, 'data': rs})


@app.route('/servers/', methods=['GET'])
@app.route('/servers/<server_id>', methods=['GET'])
def get_servers(server_id=None):
    if server_id is None:
        rs = query_db('select * from Servers')
        return jsonify({"code": 200, 'data': rs})
    else:
        rs = query_db('select * from Servers where id = ?',
                      [server_id], one=True)
        return jsonify({"code": 200, 'data': rs})


@app.route('/servers/', methods=['POST'])
@login_required
def create_server():
