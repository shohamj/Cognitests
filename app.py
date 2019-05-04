import os
import shutil
import threading
import time
from random import randint

import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

import Scripts.CEFPython as CEFPython
import Scripts.exportAnlaysis as exportAnlaysis
import Scripts.import_export as import_export
import Scripts.influxdbAPI as influx
from Scripts.CortexService import startCortex, terminateCortex
from Scripts.cortex_client.constants import Streams
from Scripts.cortex_client.cortex_context_fake import queryHeadsets, subscribe, set_send, get_last_headset
from Scripts.tasks import NBackTask, EyesTask, IAPSTask, start_task

app = Flask(__name__)

for dir in ["DBS/operative/", "DBS/recordings/", "DBS/tasks/", "DBS/sounds/", "DBS/images/", "DBS/images/masks"]:
    if not os.path.exists(dir):
        os.makedirs(dir)
for file in ["DBS/operative/operative.db", "DBS/tasks/settings.db"]:
    if not os.path.exists(file):
        f = open(file, "w+")
        f.close()

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DBS/operative/operative.db'
app.config['SQLALCHEMY_BINDS'] = {'tasks': 'sqlite:///DBS/tasks/settings.db'}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # will be removed next major patch
db = SQLAlchemy(app)
# database.set_db(db)
# database.db.init_app(app)
socketio = SocketIO(app, async_mode="threading")
dataListener = 0
d = {}
task = None
isShutdown = False
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

subject_id = None
task_id = None

STOP_POW = None
STOP_DEV = None
STOP_FAC = None


class Subject(db.Model):
    __tablename__ = 'Subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    serial = db.Column(db.Text, unique=True, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('Groups.id'))
    age = db.Column(db.Integer)
    gender = db.Column(db.Text)
    dom_hand = db.Column(db.Text)
    education = db.Column(db.Integer)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Group(db.Model):
    __tablename__ = 'Groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PartOfGroup(db.Model):
    __tablename__ = 'PartOfGroup'
    subject_id = db.Column(db.Integer, db.ForeignKey('Subjects.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('Groups.id'), primary_key=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Task(db.Model):
    __tablename__ = 'Tasks'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('Subjects.id'))
    start_time = db.Column(db.REAL)
    end_time = db.Column(db.REAL)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class NbackSettings(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'NbackSettings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.TEXT, unique=True, nullable=False)
    nback = db.Column(db.Integer)
    trials = db.Column(db.Integer)
    timeout = db.Column(db.REAL)
    rest = db.Column(db.REAL)
    words = db.Column(db.TEXT)
    instructions = db.Column(db.Integer, db.ForeignKey('Instructions.id'))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class EyesSettings(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'EyesSettings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.TEXT, unique=True, nullable=False)
    open_time = db.Column(db.REAL)
    close_time = db.Column(db.REAL)
    rounds = db.Column(db.Integer)
    open_sound = db.Column(db.TEXT)
    close_sound = db.Column(db.TEXT)
    instructions = db.Column(db.Integer, db.ForeignKey('Instructions.id'))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class IAPSSettings(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'IAPSSettings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.TEXT, unique=True, nullable=False)
    images_path = db.Column(db.TEXT, nullable=False)
    rounds = db.Column(db.TEXT, nullable=False)
    rest = db.Column(db.REAL, nullable=False)
    mask = db.Column(db.TEXT, nullable=False)
    mask_duration = db.Column(db.REAL, nullable=False)
    fixation = db.Column(db.REAL, nullable=False)
    instructions = db.Column(db.Integer, db.ForeignKey('Instructions.id'))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class IAPSImages(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'IAPSImages'
    id = db.Column(db.Integer, primary_key=True)
    settings_id = db.Column(db.Integer, db.ForeignKey('IAPSSettings.id'))
    path = db.Column(db.TEXT, nullable=False)
    display_time = db.Column(db.REAL)
    category_id = db.Column(db.Integer, db.ForeignKey('IAPSCategories.id'))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class IAPSCategories(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'IAPSCategories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Instructions(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'Instructions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text, nullable=False)
    paragraphs = db.Column(db.Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def writeProgressToConsole(text):
    with app.app_context():
        socketio.emit('exportTaskAnalysisConsole', text)


def boolToHTMLDisplay(bool):
    if bool is True:
        return ""
    else:
        return "none"


def sendContactQuality(data):
    with app.app_context():
        socketio.emit('contactQuality', data)


def sendBandPower(data):
    with app.app_context():
        socketio.emit('bandPower', data)


def setGridContent(top, mid, bot):
    with app.app_context():
        socketio.emit('setContent', {'top': top, 'mid': mid, 'bot': bot})


def setCrossVisibility(bool):
    with app.app_context():
        socketio.emit('setContentVisibility', boolToHTMLDisplay(bool))
        if bool:
            socketio.emit('setContent', {'top': "", 'mid': '+', 'bot': ""})


def setMidContent(content):
    with app.app_context():
        socketio.emit('setContent', {'top': "", 'mid': content, 'bot': ""})


def setIAPSContent(content):
    with app.app_context():
        socketio.emit('setIAPSContent', {"src": content})


def setInsVisibility(bool):
    with app.app_context():
        socketio.emit('setInsVisibility', boolToHTMLDisplay(bool))


def setContentVisibility(bool):
    with app.app_context():
        socketio.emit('setContentVisibility', boolToHTMLDisplay(bool))


def setWaitVisibility(bool):
    with app.app_context():
        socketio.emit('setWaitVisibility', boolToHTMLDisplay(bool))


def setIAPSWaitVisibility(bool):
    with app.app_context():
        print("setIAPSWaitVisibility", bool, boolToHTMLDisplay(bool))
        socketio.emit('setIAPSWaitVisibility', boolToHTMLDisplay(bool))


def setIAPSEmotionVisibility(bool):
    with app.app_context():
        socketio.emit('setIAPSEmotionVisibility', boolToHTMLDisplay(bool))


def setEndVisibility(bool):
    with app.app_context():
        socketio.emit('setEndVisibility', boolToHTMLDisplay(bool))


def setIAPSContentVisibility(bool):
    with app.app_context():
        socketio.emit('setIAPSContentVisibility', boolToHTMLDisplay(bool))


def setIAPSKeyChoosingVisibility(bool):
    with app.app_context():
        socketio.emit('setIAPSKeyChoosingVisibility', boolToHTMLDisplay(bool))


def setInstructionsData(data):
    with app.app_context():
        print("setInstructionsData", data)
        socketio.emit('setInstructionsData', data)


def taskDone():
    global STOP_DEV, STOP_POW, STOP_FAC
    STOP_DEV.set()
    STOP_POW.set()
    STOP_FAC.set()
    Task.query.get(task_id).end_time = time.time()
    db.session.commit()


@app.route('/fullScreenOn')
def fullScreenOn():
    try:
        CEFPython.toggleFullscreen(True)
    except:
        pass
    return "fullScreenOn"


@socketio.on('evAddIAPSCategory')
def evAddIAPSCategory(name=None):
    if name:
        print("evAddIAPSCategory, Name:", name)
        new_category = IAPSCategories(name=name)
        db.session.add(new_category)
        db.session.commit()
    categories = IAPSCategories.query.all()
    categories_data = []
    for c in categories:
        categories_data.append({"name": c.name, "id": c.id})
    print(categories_data)
    socketio.emit('evIAPSCategoriesChanged', {"categories": categories_data})


@socketio.on('evTaskWindowLoaded')
def evTaskWindowLoaded():
    global task
    task.taskWindowLoaded()


@socketio.on('evCloseTask')
def evCloseTask():
    global STOP_DEV, STOP_POW, STOP_FAC
    global task
    task.isAlive = False
    STOP_DEV.set()
    STOP_POW.set()
    STOP_FAC.set()
    db.session.delete(Task.query.get(task_id))
    db.session.commit()
    influx.deletTask("task" + str(task_id))


@socketio.on('openPath')
def openPath(path):
    print(path)
    print(r'explorer /select, "' + path + '"')
    import subprocess
    subprocess.Popen(r'explorer /select, "' + path + '"')


@socketio.on('openDir')
def openDir(path):
    path = os.path.realpath(path)
    os.startfile(path)


@app.route('/fullScreenOff')
def fullScreenOff():
    CEFPython.toggleFullscreen(False)
    return "fullScreenOff"

    # size = wxCEF.GetSize()
    # wxCEF.SetSize(0, 0)
    # wxCEF.SetSize(size)


@socketio.on('evSpaceKeyPressed')
def handle_spacepressed():
    global task
    if task is not None:
        task.spaceKeyPressed()


@socketio.on('evEmotionChosen')
def evEmotionChosen(emotion):
    global task
    if task is not None:
        task.emotionChosen(emotion)


@socketio.on('exportTaskData')
def exportTaskData(tasks, file_name, zip, csv):
    if not os.path.exists("Exports"):
        os.makedirs("Exports")
    path = import_export.export_tasks_data(tasks, file_name, zip, csv)
    socketio.emit('exportTaskDataDone', {"path": path})


def exportTaskAnalysis(tasks, dir_name, task_type):
    if not os.path.exists("Exports/analysis"):
        os.makedirs("Exports/analysis")
    path = os.path.abspath("Exports/analysis/" + dir_name)
    print(tasks)
    if task_type == "iaps":
        for task in tasks:
            sub_id = Task.query.get(int(task["id"])).subject_id
            task["gender"] = Subject.query.get(sub_id).gender
        exportAnlaysis.exportIAPS(tasks, path, writeProgressToConsole)
    else:
        exportAnlaysis.export(tasks, path, task_type, writeProgressToConsole)
    with app.app_context():
        socketio.emit('exportTaskAnalysisDone', {"path": [path]})


@socketio.on('exportTaskAnalysis')
def exportTaskDataEvent(tasks, dir_name, task_type):
    threading.Thread(target=exportTaskAnalysis, args=(tasks, dir_name, task_type)).start()


@socketio.on('exportSubjects')
def exportSubjects(subjects, file_name):
    if not os.path.exists("Exports"):
        os.makedirs("Exports")
    path = import_export.exportSubjects(subjects, file_name)
    socketio.emit('exportSubjectsDone', {"path": path})


@socketio.on('exportSettings')
def exportSettings(settings, file_name):
    if not os.path.exists("Exports"):
        os.makedirs("Exports")
    path = import_export.exportSettings(settings, file_name)
    print(path)
    socketio.emit('exportSettingsDone', {"path": path})


@socketio.on('importTaskData')
def importTaskData(file_info):
    file = file_info['file']
    name = file_info['name']
    if not os.path.exists("Exports/tmp"):
        os.makedirs("Exports/tmp")
    with open('Exports/tmp/' + name, 'wb') as f:
        f.write(file)
    log = import_export.import_tasks_data('Exports/tmp/' + name)
    shutil.rmtree('Exports/tmp')
    socketio.emit('importTaskDataDone', {'log': log})


@socketio.on('importSubjects')
def importSubjects(file_info):
    file = file_info['file']
    name = file_info['name']
    if not os.path.exists("Exports/tmp"):
        os.makedirs("Exports/tmp")
    with open('Exports/tmp/' + name, 'wb') as f:
        f.write(file)
    log = import_export.importSubjects('Exports/tmp/' + name)
    print(log)
    shutil.rmtree('Exports/tmp', ignore_errors=True)
    socketio.emit('importSubjectsDone', {'log': log})


@socketio.on('importSettings')
def importSettings(file_info):
    file = file_info['file']
    name = file_info['name']
    if not os.path.exists("Exports/tmp"):
        os.makedirs("Exports/tmp")
    with open('Exports/tmp/' + name, 'wb') as f:
        f.write(file)
    log = import_export.importSettings('Exports/tmp/' + name)
    shutil.rmtree('Exports/tmp', ignore_errors=True)
    socketio.emit('importSettingsDone', {'log': log})


@socketio.on('selectedTaskChanged')
def selectedTaskChanged(id, type):
    task_settings = None
    print("selectedTaskChanged", id, type)
    if type == "nback":
        selected_task = NbackSettings.query.get(id)
        task_settings = selected_task.as_dict()

    if type == "eyes":
        selected_task = EyesSettings.query.get(id)
        task_settings = selected_task.as_dict()
        if task_settings["open_sound"]:
            task_settings["open_sound"] = "/sounds/" + task_settings["open_sound"]
        if task_settings["close_sound"]:
            task_settings["close_sound"] = "/sounds/" + task_settings["close_sound"]
        print(task_settings)

    if type == "iaps":
        selected_task = IAPSSettings.query.get(id)
        task_settings = selected_task.as_dict()

    if task_settings:
        task_settings["type"] = type
        socketio.emit('changeSelectedTask', task_settings)


@socketio.on('selectedGroupChanged')
def selectedGroupChanged(id):
    selected_group = Group.query.get(id)
    socketio.emit('changeSelectedGroup', {"name": selected_group.name, "desc": selected_group.description})


@socketio.on('selectedSubjectChanged')
def selectedSubjectChanged(id):
    selected_subject = Subject.query.get(id)
    socketio.emit('changeSelectedSubjectData', selected_subject.as_dict())


@socketio.on('analysisSubjectsChanged')
def analysisSubjectsChanged(subjects, select, type):
    task_ids = []
    for id in subjects:
        tasks = Task.query.filter_by(subject_id=id)
        print(tasks)
        for t in tasks:
            print(t)
            task_ids.append(t.id)
    socketio.emit('changeTasksAnalysisSelect', {"tasks": task_ids, "bool": select, "type": type})


@socketio.on('analysisGroupsChanged')
def analysisGroupsChanged(groups, select):
    task_ids = []
    for g in groups:
        subjects = []
        q = Subject.query.filter_by(group_id=g)
        for s in q:
            subjects.append(s.serial)
        for id in subjects:
            tasks = Task.query.filter_by(subject_id=id)
            print(tasks)
            for t in tasks:
                print(t)
                task_ids.append(t.id)
    socketio.emit('changeTasksAnalysisSelect', {"tasks": task_ids, "bool": select})


@socketio.on('selectedAnalysisChanged')
def selectedTaskChanged(taskid, type):
    taskData = influx.getTaskData("task" + str(taskid))
    if type == "nback":
        taskClicks = influx.getNbackTaskClicks("task" + str(taskid))
        socketio.emit('changeAnalysisData', {"data": taskData, "clicks": taskClicks, "type": type})
    if type == "iaps":
        taskClicks = influx.getIAPSTaskClicks("task" + str(taskid))
        print(taskClicks)
        socketio.emit('changeAnalysisData', {"data": taskData, "clicks": taskClicks, "type": type})
    if type == "eyes":
        states = influx.getEyesStatesTimes("task" + str(taskid))
        print(states)
        socketio.emit('changeAnalysisData', {"data": taskData, "states": states, "type": type})


def insertPowForNBack(task_id, task_status, task_difficulty, task_round, data):
    data["status"] = task_status
    data["difficulty"] = task_difficulty
    data["round"] = task_round
    influx.insert_pow("task" + str(task_id), data)


def insertPowForIAPS(task_id, data):
    influx.insert_pow("task" + str(task_id), data)


def insertPowForEyes(task_id, eyesState, round, data):
    data["eyesState"] = eyesState
    data["round"] = round
    influx.insert_pow("task" + str(task_id), data)


def on_task_start(type):
    global subject_id, task_id, task, STOP_POW, STOP_DEV, STOP_FAC
    try:
        task_data = Task(subject_id=subject_id, start_time=time.time(), type=type)
        db.session.add(task_data)
        db.session.flush()
        db.session.refresh(task_data)
        task_id = task_data.id
        on_dev = lambda x: influx.insert_dev("task" + str(task_id), x)

        if type == "nback":
            set_send(Streams.POW.value,
                     lambda x: [insertPowForNBack(task_id, task.getStatus(), task.getDifficulty(), task.getRound(), x),
                                sendBandPower(x)])
            set_send(Streams.DEV.value, lambda x: [sendContactQuality(x), on_dev(x)])
            task.set_sendClick(lambda x: influx.insert_click("task" + str(task_id), x))
        if type == "eyes":
            set_send(Streams.POW.value,
                     lambda x: [insertPowForEyes(task_id, task.getEyesState(), task.getRound(), x), sendBandPower(x)])
            set_send(Streams.DEV.value, lambda x: [sendContactQuality(x), on_dev(x)])
            set_send(Streams.FAC.value, lambda x: influx.insert_fac("task" + str(task_id), x))
            STOP_FAC = subscribe(Streams.FAC.value, get_last_headset())
        if type == "iaps":
            set_send(Streams.POW.value,
                     lambda x: [insertPowForIAPS(task_id, x), sendBandPower(x)])
            set_send(Streams.DEV.value, lambda x: [sendContactQuality(x), on_dev(x)])
            task.set_sendClick(lambda x: influx.insert_image_click("task" + str(task_id), x))
        db.session.commit()
    except Exception as e:
        print("Tell me why", e)


@app.route('/')
def main():
    # return redirect("/addInstructions")
    return render_template("homev2.html")


@app.route('/_headsetcard')
def _headsetcard():
    return render_template("includes/_headsetcard.html")


@app.route('/_groups')
def _groups():
    groups = list(map(lambda x: x.as_dict(), Group.query.all()))
    return jsonify(groups)


@app.route('/insight.babylon')
def _insightBabylon():
    return send_from_directory('../project3DHead', "Head3DProject.babylon")


@app.route('/taskVisualization')
def tasksAnalysis():
    nbackTasks = Task.query.filter_by(type="nback")
    eyesTasks = Task.query.filter_by(type="eyes")
    iapsTasks = Task.query.filter_by(type="iaps")
    Task.subject_name = property(lambda self: Subject.query.get(self.subject_id).name)
    Task.start_time_str = property(lambda self: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)))
    return render_template("taskVisualization.html", nbackTasks=nbackTasks, eyesTasks=eyesTasks, iapsTasks=iapsTasks,
                           taskover=False)


@app.route('/importTasksData')
def importTasksData():
    return render_template("importTasksData.html")


@app.route('/importSubjects')
def importSubjects():
    return render_template("importSubjects.html")


@app.route('/importSettings')
def importSettings():
    return render_template("importSettings.html")


@app.route('/exportTasksData')
def exportTasksData():
    tasks = Task.query.all()
    Task.subject_name = property(lambda self: Subject.query.get(self.subject_id).name)
    Task.start_time_str = property(lambda self: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)))
    return render_template("exportTasksData.html", tasks=tasks)


def arrayToString(arr):
    res = ""
    if arr:
        for elem in arr[:-1]:
            if isinstance(elem, tuple):
                elem = elem[0]
            res += str(elem) + ","
        if isinstance(arr[-1], tuple):
            arr[-1] = arr[-1][0]
        res += str(arr[-1])
    return res


@app.route('/exportTasksAnalysis')
def exportTasksAnalysis():
    nbackTasks = Task.query.filter_by(type="nback")
    eyesTasks = Task.query.filter_by(type="eyes")
    iapsTasks = Task.query.filter_by(type="iaps")
    Task.subject_name = property(lambda self: Subject.query.get(self.subject_id).name)
    Task.start_time_str = property(lambda self: time.strftime('%Y-%m-%d--%H-%M-%S', time.localtime(self.start_time)))
    Task.start_time_str = property(lambda self: time.strftime('%Y-%m-%d--%H-%M-%S', time.localtime(self.start_time)))
    groups = Group.query.all()
    subjects = Subject.query.all()
    Subject.group_id = property(lambda self: arrayToString(
        PartOfGroup.query.with_entities(PartOfGroup.group_id).filter_by(subject_id=str(self.id)).all()))
    for subject in subjects:
        print(subject.group_id)
    return render_template("exportTasksAnalysis.html", nbackTasks=nbackTasks, eyesTasks=eyesTasks, iapsTasks=iapsTasks,
                           groups=groups, subjects=subjects)


@app.route('/exportSubjects')
def exportSubjects():
    subjects = Subject.query.all()
    return render_template("exportSubjects.html", subjects=subjects)


@app.route('/exportSettings')
def exportSettings():
    nback_settings = NbackSettings.query.all()
    eyes_settings = EyesSettings.query.all()
    iaps_settings = IAPSSettings.query.all()

    return render_template("exportSettings.html", nback_settings=nback_settings, eyes_settings=eyes_settings,
                           iaps_settings=iaps_settings)


@app.route('/taskVisualization/taskover/<type>')
def tasksAnalysisTaskOver(type="nback"):
    nbackTasks = Task.query.filter_by(type="nback")
    eyesTasks = Task.query.filter_by(type="eyes")
    iapsTasks = Task.query.filter_by(type="iaps")
    Task.subject_name = property(lambda self: Subject.query.get(self.subject_id).name)
    Task.start_time_str = property(lambda self: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)))
    return render_template("taskVisualization.html", nbackTasks=nbackTasks, eyesTasks=eyesTasks, iapsTasks=iapsTasks,
                           taskover=True, type=type)


def generateEyesTask(selected_task):
    global task
    config = {
        "open_time": selected_task.open_time,
        "close_time": selected_task.close_time,
        "open_sound": selected_task.open_sound,
        "close_sound": selected_task.close_sound,
        "rounds": selected_task.rounds,
        "instructions": instructionToDict(selected_task.instructions)

    }
    funcs = {
        "setContent": setMidContent,
        "setInsVisibility": setInsVisibility,
        "setContentVisibility": setContentVisibility,
        "setWaitVisibility": setWaitVisibility,
        "setEndVisibility": setEndVisibility,
        "setInstructionsData": setInstructionsData

    }
    task = EyesTask(config, funcs)
    task.set_onStart(lambda: on_task_start("eyes"))
    start_task(task, taskDone)


def getImages(path):
    res = []
    dir = os.path.basename(os.path.normpath(path))
    for root, directories, filenames in os.walk(path):
        for filename in filenames:
            if root == path:
                res.append({"path": dir + "/" + filename, "category": None})
            else:
                category = os.path.basename(os.path.normpath(root))
                res.append({"path": dir + "/" + category + "/" + filename, "category": category})
    return res


def generateIAPSTask(selected_task):
    global task
    rounds_str = selected_task.rounds.split()
    rounds = []
    for round in rounds_str:
        rounds.append(float(round))
    images = getImages(os.path.join(APP_ROOT + '/DBS/images/' + selected_task.images_path))
    config = {
        "fixation": selected_task.fixation,
        "rest": selected_task.rest,
        "rounds": rounds,
        "images": images,
        "mask": "masks/" + selected_task.mask,
        "mask_duration": selected_task.mask_duration,
        "instructions": instructionToDict(selected_task.instructions)

    }
    funcs = {
        "setContent": setIAPSContent,
        "setInsVisibility": setInsVisibility,
        "setContentVisibility": setIAPSContentVisibility,
        "setWaitVisibility": setIAPSWaitVisibility,
        "setEndVisibility": setEndVisibility,
        "setEmotionVisibility": setIAPSEmotionVisibility,
        "setCrossVisibility": setCrossVisibility,
        "setKeyChoosingVisibility": setIAPSKeyChoosingVisibility,
        "setInstructionsData": setInstructionsData

    }
    task = IAPSTask(config, funcs)
    task.set_onStart(lambda: on_task_start("iaps"))
    start_task(task, taskDone)


@app.route('/chooseTask/', methods=['GET'])
@app.route('/chooseTask/send/<type>', methods=['POST'])
def chooseTask(type=None):
    if request.method == 'POST':
        id = request.form['task']
        if type == "nback":
            selected_task = NbackSettings.query.get(id)
            generateNBackTask(selected_task)
        if type == "eyes":
            selected_task = EyesSettings.query.get(id)
            generateEyesTask(selected_task)
        if type == "iaps":
            selected_task = IAPSSettings.query.get(id)
            generateIAPSTask(selected_task)
        return redirect('/chooseSubject')
    if request.method == 'GET':
        nback_tasks = NbackSettings.query.all()
        eyes_tasks = EyesSettings.query.all()
        iaps_tasks = IAPSSettings.query.all()
        return render_template("chooseTask.html", nback_tasks=nback_tasks, eyes_tasks=eyes_tasks, iaps_tasks=iaps_tasks)


@app.route('/editTask/', methods=['GET'])
@app.route('/editTask/send/<type>', methods=['POST'])
def editTask(type=None):
    if request.method == 'POST':
        print(request.form)
        if type == "nback":
            id = request.form['task']
            task_to_update = NbackSettings.query.get(id)
            task_to_update.name = request.form['name']
            task_to_update.words = request.form['words']
            task_to_update.nback = request.form['nback']
            task_to_update.trials = request.form['trials']
            task_to_update.timeout = request.form['timeout']
            task_to_update.rest = request.form['rest']
            task_to_update.instructions = request.form['instructions']
        elif type == 'eyes':
            id = request.form['task']
            task_to_update = EyesSettings.query.get(id)
            task_to_update.name = request.form['name']
            task_to_update.rounds = request.form['rounds']
            task_to_update.open_time = request.form['open_time']
            task_to_update.close_time = request.form['close_time']
            open_s = saveFile('open_sound', request.files, "sounds")
            close_s = saveFile('close_sound', request.files, "sounds")
            task_to_update.instructions = request.form['instructions']
            if open_s:
                task_to_update.open_sound = open_s
            if close_s:
                task_to_update.close_sound = close_s
        elif type == "iaps":
            rounds = request.form.getlist('rounds[]')
            rounds = " ".join(str(x) for x in rounds)
            id = request.form['task']
            task_to_update = IAPSSettings.query.get(id)
            task_to_update.name = request.form['name']
            task_to_update.rest = request.form['rest']
            task_to_update.mask_duration = request.form['mask_duration']
            task_to_update.mask = request.form['mask']
            task_to_update.fixation = request.form['fixation']
            task_to_update.images_path = request.form['dir']
            task_to_update.rounds = rounds
            task_to_update.instructions = request.form['instructions']
        db.session.commit()
        return "edited"
    if request.method == 'GET':
        nbackTasks = NbackSettings.query.all()
        eyesTasks = EyesSettings.query.all()
        iapsTasks = IAPSSettings.query.all()
        ins = Instructions.query.all()
        return render_template("editTaskV2.html", nbackTasks=nbackTasks, eyesTasks=eyesTasks, iapsTasks=iapsTasks,
                               instructions=ins)


@app.route('/editGroup/', methods=['GET'])
@app.route('/editGroup/send/', methods=['POST'])
def editGroup():
    if request.method == 'POST':
        print(request.form)
        old_name = request.form['group']
        new_name = request.form['groupName']
        desc = request.form['desc']
        group_to_update = Group.query.filter_by(name=old_name).first()
        print(group_to_update)
        group_to_update.name = new_name
        group_to_update.description = desc
        db.session.commit()
        return redirect('/editGroup')
    if request.method == 'GET':
        groups = Group.query.all()
        return render_template("editGroup.html", groups=groups)


@app.route('/deleteGroup', methods=['POST'])
def deleteGroup():
    print(request.form['group'])
    group = Group.query.get(request.form['group'])
    db.session.delete(group)
    db.session.commit()
    return "deleted"


@app.route('/deleteSubject', methods=['POST'])
def deleteSubject():
    subject = Subject.query.get(request.form['subject'])
    subject_tasks = db.session.query(Task.id).filter_by(subject_id=request.form['subject'])
    for id in subject_tasks.all():
        id = id[0]
        print("subject_tasks id", id)
        influx.deletTask("task" + str(id))
    subject_tasks.delete()
    PartOfGroup.query.filter_by(subject_id=request.form['subject']).delete()
    db.session.delete(subject)
    db.session.commit()

    return "deleted"


@app.route('/deleteTask/<type>', methods=['POST'])
def deleteTask(type):
    if type == "nback":
        task = NbackSettings.query.get(request.form['task'])
    if type == "eyes":
        task = EyesSettings.query.get(request.form['task'])
    if type == "iaps":
        task = IAPSSettings.query.get(request.form['task'])
    db.session.delete(task)
    db.session.commit()
    return "deleted"


@app.route('/editSubject/', methods=['GET'])
@app.route('/editSubject/send/', methods=['POST'])
def editSubject():
    if request.method == 'POST':
        subject = Subject.query.get(request.form['subject'])
        subject.name = request.form['name']
        subject.serial = request.form['serial']
        subject.age = request.form['age']
        subject.gender = request.form['gender']
        subject.dom_hand = request.form['dom_hand']
        subject.education = request.form['education']
        groups = request.form.getlist('group_id')
        PartOfGroup.query.filter_by(subject_id=request.form['subject']).delete()
        for group in groups:
            db.session.add(PartOfGroup(group_id=group, subject_id=subject.id))
        db.session.commit()
        return redirect('/editSubject')
    if request.method == 'GET':
        subjects = Subject.query.all()
        groups = Group.query.all()
        Subject.group_id = property(lambda self:
                                    PartOfGroup.query.with_entities(PartOfGroup.group_id).filter_by(
                                        subject_id=str(self.id)).all())
        return render_template("editSubject.html", subjects=subjects, groups=groups)


@app.route('/addInstructions/', methods=['GET'])
@app.route('/addInstructions/send/', methods=['POST'])
def addInstructions():
    if request.method == 'GET':
        return render_template("addInstructions.html")
    if request.method == 'POST':
        pars = ""
        for par in request.form.getlist('pars[]'):
            print(par)
            pars += par + "***END***"
        new_ins = Instructions(name=request.form['name'], title=request.form['title'], paragraphs=pars)
        db.session.add(new_ins)
        db.session.commit()
        return jsonify({"name": new_ins.name, "id": new_ins.id})


@app.route('/headsets')
def headsets():
    global STOP_DEV, STOP_POW, STOP_FAC
    try:
        STOP_DEV.set()
        STOP_POW.set()
        STOP_FAC.set()
    except:
        pass
    return render_template("headsets.html")


@app.route('/task')
def task():
    global task
    task_class = task.__class__.__name__
    type = ""
    if task_class == "NBackTask":
        type = "nback"
    if task_class == "EyesTask":
        type = "eyes"
    if task_class == "IAPSTask":
        type = "iaps"
    return render_template("task.html", type=type)


def saveFile(input, files, dir):
    print("all files:", files)
    res = None
    if input in files:
        filesList = request.files.getlist(input)
        for file in filesList:
            print("input file:", file)
            if file.filename != '':
                if not res:
                    res = ''
                file_name = str(time.time()) + "_" + file.filename.replace(' ', '_') + ' '
                res += file_name
                try:
                    file.save(os.path.join(APP_ROOT + '/DBS/' + dir, file_name))
                except Exception as e:
                    print("saveFile", e)
    return res


def addIAPSImages(request, settings_id):
    display_times = request.form.getlist('display_time[]')
    categories = request.form.getlist('category[]')
    images = request.files.getlist('image[]')
    for image, category, display_time in zip(images, categories, display_times):
        print(image, category, display_time)
        file_name = str(time.time()) + "_" + image.filename.replace(' ', '_') + ' '
        image.save(os.path.join(APP_ROOT + '/DBS/images', file_name))
        new_image = IAPSImages(settings_id=settings_id, path=file_name, category_id=category, display_time=display_time)
        db.session.add(new_image)
        db.session.commit()
    # print("display_times", display_times)
    # print("categories", categories)
    # print("images", images)


@app.route('/createTask/', methods=['GET'])
@app.route('/createTask/send/<type>', methods=['POST'])
def createTask(type=None):
    if request.method == 'POST':
        new_task = None
        if type == "nback":
            try:
                new_task = NbackSettings(
                    name=request.form['name'],
                    nback=request.form['nback'],
                    trials=request.form['trials'],
                    timeout=request.form['timeout'],
                    rest=request.form['rest'],
                    words=request.form['words'],
                    instructions=request.form['instructions']
                )
                db.session.add(new_task)
                db.session.commit()
            except Exception as e:
                print("My error:", e)
        elif type == 'eyes':
            try:
                new_task = EyesSettings(
                    name=request.form['name'],
                    rounds=request.form['rounds'],
                    open_time=request.form['open_time'],
                    close_time=request.form['close_time'],
                    open_sound=saveFile("open_sound", request.files, "sounds"),
                    close_sound=saveFile("close_sound", request.files, "sounds"),
                    instructions=request.form['instructions']
                )
                db.session.add(new_task)
                db.session.commit()
            except Exception as e:
                print("My error:", e)
        elif type == 'iaps':
            try:
                print(request.form)
                rounds = request.form.getlist('rounds[]')
                rounds = " ".join(str(x) for x in rounds)
                print(rounds)
                new_task = IAPSSettings(
                    name=request.form['name'],
                    rounds=rounds,
                    fixation=request.form['fixation'],
                    rest=request.form['rest'],
                    mask=request.form['mask'],
                    mask_duration=request.form['mask_duration'],
                    images_path=request.form['dir'],
                    instructions=request.form['instructions']
                )
                db.session.add(new_task)
                db.session.commit()
            except Exception as e:
                print("My error:", e)
        return "created"
    if request.method == 'GET':
        ins = Instructions.query.all()
        return render_template("createTaskV2.html", instructions=ins)


@app.route('/loadTask', methods=['POST'])
def loadTask():
    '''
    tasksFolder = os.path.join(APP_ROOT, 'tasks\\')
    print(tasksFolder)
    filePath = tasksFolder + request.form['file']
    print(filePath)
    with open(filePath, 'r') as fp:
        words = []
        data = json.load(fp)
        for word in data["words"]:
            words.append(word["word"])
        generateTask(words)
        '''
    return redirect("/chooseSubject")


@app.route('/data')
@app.route('/data/<headsetID>')
def data(headsetID=None):
    global dataListener, STOP_DEV, STOP_POW
    print("data")
    if headsetID:
        set_send(Streams.DEV.value, sendContactQuality)
        set_send(Streams.POW.value, sendBandPower)
        STOP_DEV = subscribe(Streams.DEV.value, headsetID)
        STOP_POW = subscribe(Streams.POW.value, headsetID)
        headset = headsetID.split('-')[0]
        print(headset.lower())
        return render_template("dataV2_d.html", headset=headset.lower(), devcols=queryHeadsets(headsetID)[0]["sensors"],
                               showbtns=True)
    else:
        headset = get_last_headset().split('-')[0]
        return render_template("dataV2_d.html", headset=headset.lower(),
                               devcols=queryHeadsets(get_last_headset())[0]["sensors"],
                               showbtns=False)
    return "Nope!"


@app.route('/_queryHeadsets')
def _queryheadsets():
    return jsonify(queryHeadsets())
    # return fakehs()


@app.route('/_taskInfo')
def _taskInfo():
    global task
    if task is not None:
        return jsonify(task.next)
    else:
        return jsonify({})


@app.route('/_taskNewRound', methods=['POST'])
def _taskNewRound():
    global task
    if task is not None:
        task.startRound()
        return "New round started"
    else:
        return "There is no task loaded"


@app.route('/_getDev', methods=['GET', 'POST'])
def quality():
    global d
    if request.method == 'GET':
        return jsonify(d)

    elif request.method == 'POST':
        d = request.form
        return jsonify(d)


def fakehs():
    return jsonify([{'id': "insight-fake"}, {'id': "epoc-fake"}])


def changeq():
    while True:
        time.sleep(0.2)
        connected = False
        while not connected:
            try:
                requests.post("http://localhost:5000/_getQuality",
                              data={'c1': randint(0, 4), 'c2': randint(0, 4), 'c3': randint(0, 4), 'c4': randint(0, 4),
                                    'c5': randint(0, 4)})
                connected = True
            except:
                pass


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@app.route('/_shutdown', methods=['GET'])
@app.route('/_shutdown', methods=['GET'])
def shutdown():
    global isShutdown
    if not isShutdown:
        try:
            socketio.stop()
            isShutdown = True;
        except Exception as e:
            print(e)
    return render_template("exit.html")


def instructionToDict(ins_id):
    print("id:", ins_id)
    ins = Instructions.query.get(ins_id)
    return {"title": ins.title, "paragraphs": ins.paragraphs.split("***END***")[:-1]}


def generateNBackTask(selected_task):
    global task
    config = {
        "words": selected_task.words.split(),
        "timeout": selected_task.timeout,
        "rest": selected_task.rest,
        "nback": selected_task.nback,
        "trials_amount": selected_task.trials,
        "instructions": instructionToDict(selected_task.instructions)
    }
    funcs = {
        "setContent": setGridContent,
        "setInsVisibility": setInsVisibility,
        "setContentVisibility": setContentVisibility,
        "setWaitVisibility": setWaitVisibility,
        "setEndVisibility": setEndVisibility,
        "setInstructionsData": setInstructionsData
    }
    task = NBackTask(config, funcs)
    task.set_onStart(lambda: on_task_start("nback"))
    start_task(task, taskDone)


@app.route('/chooseSubject/send', methods=['POST'])
@app.route('/chooseSubject', methods=['GET'])
def chooseSubject():
    global subject_id
    if request.method == 'POST':
        subject = request.form['subject']
        subject_serial = subject.split(", ")[1]
        subject_id = Subject.query.filter_by(serial=subject_serial).one().id
        print(subject)
        return redirect(url_for('task'))
    if request.method == 'GET':
        subjects = Subject.query.all()
        return render_template("chooseSubject.html", subjects=subjects)


@app.route('/createSubject/send', methods=['POST'])
@app.route('/createSubject/send/<under>', methods=['POST'])
@app.route('/createSubject', methods=['GET'])
@app.route('/createSubject/<under>', methods=['GET'])
def createSubject(under=None):
    try:
        global subject_id
        if request.method == 'POST':
            subject = Subject(name=request.form['name'],
                              serial=request.form['serial'],
                              age=request.form['age'],
                              dom_hand=request.form['dom_hand'],
                              gender=request.form['gender'],
                              education=request.form['education']
                              )
            db.session.add(subject)
            db.session.flush()
            db.session.refresh(subject)
            subject_id = subject.id
            groups = request.form.getlist('group_id')
            for group in groups:
                db.session.add(PartOfGroup(group_id=group, subject_id=subject_id))
            db.session.commit()
            if under == '_':
                return redirect(url_for('task'))
            else:
                return redirect('/')

        else:
            groups = Group.query.all()
            return render_template("createSubject.html", inTask=under, groups=groups)
    except Exception as e:
        print("create user error:", e)


@app.route('/createGroup/', methods=['GET'])
@app.route('/createGroup/send/', methods=['POST'])
def createGroup():
    if request.method == 'POST':
        group = Group(name=request.form['groupName'], description=request.form['desc'])
        db.session.add(group)
        db.session.commit()
    return render_template("createGroup.html")


@app.route('/sounds/<file>', methods=['GET'])
def sounds(file):
    return send_from_directory('DBS/sounds', file)


@app.route('/images/<path:file>', methods=['GET'])
def images(file):
    print("images:", file)
    return send_from_directory('DBS/images/', file)


@app.route('/get_instructions_as_dict', methods=['POST'])
def get_instructions_as_dict():
    return jsonify(instructionToDict(request.form['ins_id']))


def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def main():
    open_port = get_open_port()

    t1 = threading.Thread(target=socketio.run, args=(app,), kwargs={'port': open_port})
    t2 = threading.Thread(target=CEFPython.startWindow,
                          args=('http://127.0.0.1:' + str(open_port), "CogniTasks", "static/img/brainBlue.ico"))

    t1.start()
    t2.start()

    startCortex()
    influx.start_influx()
    db.create_all()

    t1.join()
    t2.join()

    influx.close_influx()
    terminateCortex()


if __name__ == '__main__':
    main()
