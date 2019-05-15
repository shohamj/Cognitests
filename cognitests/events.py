import os
import shutil
import threading

import cognitests
from cognitests import socketio, db
from cognitests.helpers import exportTaskAnalysis
from cognitests.models import Task, NbackSettings, EyesSettings, IAPSSettings, Group, Subject
from cognitests.modules import influxdbAPI as influx, import_export as import_export


@socketio.on('evTaskWindowLoaded')
def evTaskWindowLoaded():
    cognitests.TASK.taskWindowLoaded()


@socketio.on('evCloseTask')
def evCloseTask():
    if cognitests.TASK:
        cognitests.TASK.isAlive = False
    if cognitests.STOP_DEV:
        cognitests.STOP_DEV.set()
    if cognitests.STOP_POW:
        cognitests.STOP_POW.set()
    if cognitests.STOP_FAC:
        cognitests.STOP_FAC.set()
    if cognitests.TASK_ID:
        db.session.delete(Task.query.get(cognitests.TASK_ID))
        influx.deletTask("task" + str(cognitests.TASK_ID))
    db.session.commit()


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


@socketio.on('evSpaceKeyPressed')
def handle_spacepressed():
    if cognitests.TASK is not None:
        cognitests.TASK.spaceKeyPressed()


@socketio.on('evEmotionChosen')
def evEmotionChosen(emotion):
    if cognitests.TASK is not None:
        cognitests.TASK.emotionChosen(emotion)


@socketio.on('exportTaskData')
def exportTaskData(tasks, file_name, zip, csv):
    if not os.path.exists("Exports"):
        os.makedirs("Exports")
    path = import_export.export_tasks_data(tasks, file_name, zip, csv)
    socketio.emit('exportTaskDataDone', {"path": path})


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
def selectedAnalysisChanged(taskid, type):
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
