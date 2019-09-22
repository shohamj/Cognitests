import os
import shutil
import threading

import cognitests
from cognitests import socketio, db
from cognitests.helpers import exportTaskAnalysis, importTasksData, exportTaskData, exportSettings,importSettings,exportSubjects,importSubjects
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
def exportTaskDataEvent(tasks, file_name, zip, csv):
    threading.Thread(target=exportTaskData, args=(tasks, file_name, zip, csv)).start()
    # exportTaskData(tasks, file_name, zip, csv)

@socketio.on('exportTaskAnalysis')
def exportTaskAnalysisEvent(tasks, dir_name, task_type):
    threading.Thread(target=exportTaskAnalysis, args=(tasks, dir_name, task_type)).start()


@socketio.on('exportSubjects')
def exportSubjectsEvent(subjects, file_name):
    threading.Thread(target=exportSubjects, args=(subjects, file_name)).start()



@socketio.on('exportSettings')
def exportSettingsEvent(settings, file_name):
    threading.Thread(target=exportSettings, args=(settings, file_name)).start()


@socketio.on('importTaskData')
def importTaskData(file_info):
    threading.Thread(target=importTasksData, args=(file_info,)).start()

@socketio.on('importSubjects')
def importSubjectsEvent(file_info):
    threading.Thread(target=importSubjects, args=(file_info,)).start()


@socketio.on('importSettings')
def importSettingsEvent(file_info):
    threading.Thread(target=importSettings, args=(file_info,)).start()


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
def selectedAnalysisChanged(taskid, type, group_by_interval, interval):
    print(group_by_interval, interval)
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
        socketio.emit('changeAnalysisData', {"data": taskData, "clicks": taskClicks, "type": type})
        print("Data Sent!!!!!!!!!!!!!!!")

    if type == "iaps":
        taskClicks = influx.getIAPSTaskClicks("task" + str(taskid))
        print(taskClicks)
        socketio.emit('changeAnalysisData', {"data": taskData, "clicks": taskClicks, "type": type})
    if type == "eyes":
        states = influx.getEyesStatesTimes("task" + str(taskid))
        print(states)
        socketio.emit('changeAnalysisData', {"data": taskData, "states": states, "type": type})
