import os
import shutil
import threading
import time
from random import randint

import requests
from flask import request, jsonify

import cognitests
import cognitests.modules.import_export as import_export
from cognitests import app, socketio, db, APP_ROOT
from cognitests.models import Task, Subject, Instructions
from cognitests.modules import influxdbAPI as influx, exportAnlaysis as exportAnlaysis, CEFPython
from cognitests.modules.CortexService import startCortex, stopCortex
from cognitests.modules.cortex_client import Streams
from cognitests.modules.cortex_client import set_send, subscribe, get_last_headset
from cognitests.modules.tasks import EyesTask, start_task, IAPSTask, NBackTask


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
    if cognitests.STOP_DEV:
        cognitests.STOP_DEV.set()
    if cognitests.STOP_POW:
        cognitests.STOP_POW.set()
    if cognitests.STOP_FAC:
        cognitests.STOP_FAC.set()
    Task.query.get(cognitests.TASK_ID).end_time = time.time()
    db.session.commit()


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


def importTasksData(file_info):
    file = file_info['file']
    name = file_info['name']
    if not os.path.exists("Exports/tmp"):
        os.makedirs("Exports/tmp")
    with open('Exports/tmp/' + name, 'wb') as f:
        f.write(file)
    log = import_export.import_tasks_data('Exports/tmp/' + name)
    try:
        shutil.rmtree('Exports/tmp')
    except Exception as e:
        print("importTaskData Error:", e)
    socketio.emit('importTaskDataDone', {'log': log})


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
    try:
        print("on_task_start")
        task_data = Task(subject_id=cognitests.SUBJECT_ID, start_time=time.time(), type=type)
        db.session.add(task_data)
        db.session.flush()
        db.session.refresh(task_data)
        cognitests.TASK_ID = task_data.id
        on_dev = lambda x: influx.insert_dev("task" + str(cognitests.TASK_ID), x)
        if type == "nback":
            set_send(Streams.POW.value,
                     lambda x: [insertPowForNBack(cognitests.TASK_ID, cognitests.TASK.getStatus(),
                                                  cognitests.TASK.getDifficulty(), cognitests.TASK.getRound(), x),
                                sendBandPower(x)])
            set_send(Streams.DEV.value, lambda x: [sendContactQuality(x), on_dev(x)])
            cognitests.TASK.set_sendClick(lambda x: influx.insert_click("task" + str(cognitests.TASK_ID), x))
        if type == "eyes":
            set_send(Streams.POW.value,
                     lambda x: [insertPowForEyes(cognitests.TASK_ID, cognitests.TASK.getEyesState(),
                                                 cognitests.TASK.getRound(), x), sendBandPower(x)])
            set_send(Streams.DEV.value, lambda x: [sendContactQuality(x), on_dev(x)])
            set_send(Streams.FAC.value, lambda x: influx.insert_fac("task" + str(cognitests.TASK_ID), x))
            cognitests.STOP_FAC = subscribe(Streams.FAC.value, get_last_headset())
        if type == "iaps":
            set_send(Streams.POW.value,
                     lambda x: [insertPowForIAPS(cognitests.TASK_ID, x), sendBandPower(x)])
            set_send(Streams.DEV.value, lambda x: [sendContactQuality(x), on_dev(x)])
            cognitests.TASK.set_sendClick(lambda x: influx.insert_image_click("task" + str(cognitests.TASK_ID), x))
        db.session.commit()
    except Exception as e:
        print("Tell me why", e)


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


def generateEyesTask(selected_task):
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
    cognitests.TASK = EyesTask(config, funcs)

    cognitests.TASK.set_onStart(lambda: on_task_start("eyes"))
    start_task(cognitests.TASK, taskDone)


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
    rounds_str = selected_task.rounds.split()
    rounds = []
    for round in rounds_str:
        rounds.append(float(round))
    images = getImages(os.path.join(APP_ROOT + '/../DBS/images/' + selected_task.images_path))
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
    cognitests.TASK = IAPSTask(config, funcs)
    cognitests.TASK.set_onStart(lambda: on_task_start("iaps"))
    start_task(cognitests.TASK, taskDone)


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


def instructionToDict(ins_id):
    print("id:", ins_id)
    ins = Instructions.query.get(ins_id)
    return {"title": ins.title, "paragraphs": ins.paragraphs.split("***END***")[:-1]}


def generateNBackTask(selected_task):
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
    cognitests.TASK = NBackTask(config, funcs)
    cognitests.TASK.set_onStart(lambda: on_task_start("nback"))
    start_task(cognitests.TASK, taskDone)


def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def checkDatabaseFiles():
    path = os.path.dirname(os.path.realpath(__file__))
    for dir in ["/DBS/operative/", "/DBS/recordings/", "/DBS/tasks/", "/DBS/sounds/", "/DBS/images/",
                "/DBS/images/masks"]:
        if not os.path.exists(path + "/../" + dir):
            print(os.path.abspath(path + "/../" + dir))
            os.makedirs(path + "/../" + dir)
    for file in ["/DBS/operative/operative.db", "/DBS/tasks/settings.db"]:
        if not os.path.exists(path + "/../" + file):
            print(os.path.abspath(path + "/../" + file))
            f = open(path + "/../" + file, "w+")
            f.close()


def waitToLocalServer(port):
    import socket
    from socket import AF_INET, SOCK_DGRAM
    s = socket.socket(AF_INET, SOCK_DGRAM)
    s.settimeout(10)
    server_host = 'localhost'
    server_port = port
    while True:
        try:
            s.connect((server_host, server_port))
            break
        except:
            pass
    s.close()


def main():
    import pygame
    from cognitests.modules.splashScreen import splash
    checkDatabaseFiles()
    pygame.mixer.init()
    splash("cognitests/static/img/brainBlue.png")
    open_port = get_open_port()

    t1 = threading.Thread(target=socketio.run, args=(app,), kwargs={'port': open_port})
    t2 = threading.Thread(target=CEFPython.startWindow,
                          args=(
                              'http://127.0.0.1:' + str(open_port), "Cognitests",
                              "cognitests\static\img/brainBlue.ico"))

    t1.start()
    startCortex()
    influx.start_influx()
    db.create_all()
    waitToLocalServer(open_port)
    t2.start()
    pygame.display.quit()
    t1.join()
    t2.join()

    influx.close_influx()
    stopCortex()
