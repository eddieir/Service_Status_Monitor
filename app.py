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
