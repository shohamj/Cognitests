import time

from flask import request, redirect, render_template, send_from_directory, jsonify

import cognitests
from cognitests import app, db, socketio
from cognitests.helpers import sendContactQuality, sendBandPower, arrayToString, generateEyesTask, generateIAPSTask, \
    saveFile, \
    instructionToDict, generateNBackTask
from cognitests.models import Subject, PartOfGroup, Group, NbackSettings, EyesSettings, IAPSSettings, Instructions, Task
from cognitests.modules import influxdbAPI as influx, CEFPython as CEFPython
from cognitests.modules.cortex_client import Streams
from cognitests.modules.cortex_client import set_send, subscribe, queryHeadsets, get_last_headset, set_test_mode, \
    get_test_mode

isShutdown = False


@app.route('/chooseSubject/send', methods=['POST'])
@app.route('/chooseSubject', methods=['GET'])
def chooseSubject():
    if request.method == 'POST':
        subject = request.form['subject']
        subject_serial = subject.split(", ")[1]
        cognitests.SUBJECT_ID = Subject.query.filter_by(serial=subject_serial).one().id
        return redirect('/task')
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
            ret = Subject.query.filter(Subject.serial == request.form['serial']).first()
            if ret:
                return jsonify({"success": False, "error": "A subject with that serial number already exists!"})
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
            return jsonify({"success": True})

        else:
            groups = Group.query.all()
            return render_template("createSubject.html", inTask=under, groups=groups)
    except Exception as e:
        print("create user error:", e)
        return jsonify({"success": False, "error": str(e)})


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
    return send_from_directory('../DBS/sounds', file)


@app.route('/images/<path:file>', methods=['GET'])
def images(file):
    print("images:", file)
    return send_from_directory('../DBS/images/', file)


@app.route('/get_instructions_as_dict', methods=['POST'])
def get_instructions_as_dict():
    return jsonify(instructionToDict(request.form['ins_id']))


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


@app.route('/createTask/', methods=['GET'])
@app.route('/createTask/send/<type>', methods=['POST'])
def createTask(type=None):
    if request.method == 'POST':
        new_task = None
        if type == "nback":
            try:
                ret = NbackSettings.query.filter(NbackSettings.name == request.form['name']).first()
                if ret:
                    return jsonify({"success": False, "error": "NBack task with that name already exists!"})
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
                return jsonify({"success": False, "error": str(e)})

        elif type == 'eyes':
            try:
                ret = EyesSettings.query.filter(EyesSettings.name == request.form['name']).first()
                if ret:
                    return jsonify({"success": False, "error": "Eyes task with that name already exists!"})
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
                return jsonify({"success": False, "error": str(e)})

        elif type == 'iaps':
            try:
                ret = IAPSSettings.query.filter(IAPSSettings.name == request.form['name']).first()
                if ret:
                    return jsonify({"success": False, "error": "IAPS task with that name already exists!"})
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
                return jsonify({"success": False, "error": str(e)})

        return jsonify({"success": True})
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
    print("data")
    if headsetID:
        distime = time.time()
        set_send(Streams.DEV.value, sendContactQuality)
        set_send(Streams.POW.value, sendBandPower)
        cognitests.STOP_DEV = subscribe(Streams.DEV.value, headsetID)
        cognitests.STOP_POW = subscribe(Streams.POW.value, headsetID)
        headset = headsetID.split('-')[0].lower()
        devcols = queryHeadsets(headsetID)[0]["sensors"]
        print(headset.lower())
        print("data:", time.time() - distime)
        return render_template("dataV2_d.html", headset=headset, devcols=devcols, showbtns=True)
    else:
        headset = get_last_headset().split('-')[0]
        return render_template("dataV2_d.html", headset=headset.lower(),
                               devcols=queryHeadsets(get_last_headset())[0]["sensors"],
                               showbtns=False)
    return "Nope!"


@app.route('/_queryHeadsets')
def _queryheadsets():
    return jsonify(queryHeadsets())


@app.route('/_taskInfo')
def _taskInfo():
    if cognitests.TASK is not None:
        return jsonify(cognitests.TASK.next)
    else:
        return jsonify({})


@app.route('/_taskNewRound', methods=['POST'])
def _taskNewRound():
    if cognitests.TASK is not None:
        cognitests.TASK.startRound()
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
            ret = NbackSettings.query.filter(NbackSettings.name == request.form['name']).first()
            if ret and request.form['name'] != task_to_update.name:
                return jsonify({"success": False, "error": "N-Back task with that name already exists!"})
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
            ret = EyesSettings.query.filter(EyesSettings.name == request.form['name']).first()
            if ret and request.form['name'] != task_to_update.name:
                return jsonify({"success": False, "error": "Eyes task with that name already exists!"})
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
            ret = IAPSSettings.query.filter(IAPSSettings.name == request.form['name']).first()
            if ret and request.form['name'] != task_to_update.name:
                return jsonify({"success": False, "error": "IAPS task with that name already exists!"})
            task_to_update.name = request.form['name']
            task_to_update.rest = request.form['rest']
            task_to_update.mask_duration = request.form['mask_duration']
            task_to_update.mask = request.form['mask']
            task_to_update.fixation = request.form['fixation']
            task_to_update.images_path = request.form['dir']
            task_to_update.rounds = rounds
            task_to_update.instructions = request.form['instructions']
        db.session.commit()
        return jsonify({"success": True})
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
        task_to_delete = NbackSettings.query.get(request.form['task'])
    if type == "eyes":
        task_to_delete = EyesSettings.query.get(request.form['task'])
    if type == "iaps":
        task_to_delete = IAPSSettings.query.get(request.form['task'])
    db.session.delete(task_to_delete)
    db.session.commit()
    return "deleted"


@app.route('/editSubject/', methods=['GET'])
@app.route('/editSubject/send/', methods=['POST'])
def editSubject():
    if request.method == 'POST':
        subject = Subject.query.get(request.form['subject'])
        ret = Subject.query.filter(Subject.serial == request.form['serial']).first()
        if ret and request.form['serial'] != subject.serial:
            return jsonify({"success": False, "error": "A subject with that serial number already exists!"})
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
        return jsonify({"success": True})
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
    if cognitests.STOP_DEV:
        cognitests.STOP_DEV.set()
    if cognitests.STOP_POW:
        cognitests.STOP_POW.set()
    if cognitests.STOP_FAC:
        cognitests.STOP_FAC.set()
    return render_template("headsets.html")


@app.route('/task')
def taskroute():
    task_class = cognitests.TASK.__class__.__name__
    type = ""
    if task_class == "NBackTask":
        type = "nback"
    if task_class == "EyesTask":
        type = "eyes"
    if task_class == "IAPSTask":
        type = "iaps"
    return render_template("task.html", type=type)


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


@app.route('/')
def home():
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


@app.route('/fullScreenOn')
def fullScreenOn():
    # return "fullScreenOn"  # Disabling fullscreen toggle for presentation
    try:
        CEFPython.toggleFullscreen(True)
    except:
        pass
    return "fullScreenOn"


@app.route('/fullScreenOff')
def fullScreenOff():
    #return "fullScreenOff"  # Disabling fullscreen toggle for presentation
    CEFPython.toggleFullscreen(False)
    return "fullScreenOff"

    # size = wxCEF.GetSize()
    # wxCEF.SetSize(0, 0)
    # wxCEF.SetSize(size)


@app.route('/set_test_mode', methods=['POST'])
def set_mode():
    if request.form['state'] == 'true':
        set_test_mode(True)
    else:
        set_test_mode(False)
    return "mode is set"


@app.route('/get_test_mode', methods=['GET'])
def get_mode():
    if get_test_mode():
        return "true"
    return "false"

@app.route('/getAnalysisChanged', methods=['GET'])
def selectedAnalysisChanged():
    taskid = request.args.get('taskid')
    type = request.args.get('type')
    group_by_interval = request.args.get('group_by_interval') == 'true'
    interval = request.args.get('interval')
    print(taskid,type, group_by_interval, interval)
    if not taskid:
        return jsonify({"data": [], "clicks": [], "states": [], "type": type})
    if taskid == None:
        socketio.emit('changeAnalysisData', {"data": [], "clicks": [], "type": type})
        return
    if group_by_interval:
        interval_value = int(interval)
    else:
        interval_value = 1
    taskData = influx.getTaskDataV2("task" + str(taskid), group_by_interval, interval_value)
    print("Got Data")
    if type == "nback":
        taskClicks = influx.getNbackTaskClicks("task" + str(taskid))
        print("Got Clicks")
        return jsonify({"data": taskData, "clicks": taskClicks, "type": type})

    if type == "iaps":
        taskClicks = influx.getIAPSTaskClicks("task" + str(taskid))
        print(taskClicks)
        return jsonify({"data": taskData, "clicks": taskClicks, "type": type})

    if type == "eyes":
        states = influx.getEyesStatesTimes("task" + str(taskid))
        print(states)
        return jsonify({"data": taskData, "states": states, "type": type})
