import os

from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

import cognitests.modules.CEFPython as CEFPython
import cognitests.modules.influxdbAPI as influx
from cognitests.modules.CortexService import startCortex, terminateCortex

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

for dir in ["/../DBS/operative/", "/../DBS/recordings/", "/../DBS/tasks/", "/../DBS/sounds/", "/../DBS/images/",
            "/../DBS/images/masks"]:
    if not os.path.exists(APP_ROOT + dir):
        print(os.path.abspath(APP_ROOT + dir))
        os.makedirs(dir)
for file in ["/../DBS/operative/operative.db", "/../DBS/tasks/settings.db"]:
    if not os.path.exists(APP_ROOT + file):
        print(os.path.abspath(APP_ROOT + file))
        f = open(file, "w+")
        f.close()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../DBS/operative/operative.db'
app.config['SQLALCHEMY_BINDS'] = {'tasks': 'sqlite:///../DBS/tasks/settings.db'}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # will be removed next major patch

db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode="threading")

# Globals shared by routes.py, events.py, and helpers.py
TASK = None
SUBJECT_ID = None
TASK_ID = None
STOP_POW = None
STOP_DEV = None
STOP_FAC = None

from cognitests import routes, events
