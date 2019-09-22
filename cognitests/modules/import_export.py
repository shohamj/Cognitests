import copy
import json
import os
import time
import zipfile
from subprocess import call, check_output

from cognitests.models import Task, NbackSettings, EyesSettings, IAPSSettings, Subject, db, PartOfGroup
from cognitests.modules.influxdbAPI import insertjson

dir = os.path.dirname(__file__)


def export_tasks_data(tasks_ids=[], filename="default", export_zip=False, export_csv=False, log=print):
    path = []
    if not os.path.exists("Exports/data/"):
        os.makedirs("Exports/data/")
    if export_zip:
        data_list = []
        for index, id in enumerate(tasks_ids):
            log("Exporting task {} of {} into the ZIP file".format(index+1, len(tasks_ids)))
            task_data = check_output(
                ["influxdb\influx.exe", "-database", "Tasks", "-execute", "select * from task" + str(id), "-format",
                 "json"])

            task_data = json.loads(task_data)

            t = Task.query.get(id).as_dict()
            s = Subject.query.get(t['subject_id']).as_dict()
            g = db.session.query(PartOfGroup.group_id).filter_by(subject_id=t['subject_id']).all()
            data = task_data

            data["task"] = t
            data["subject"] = s
            data["groups"] = g
            data_list.append(data)
            f = open("data3.json", "w")
            f.write(str(data_list))
            f.close()
        log("Saving the ZIP file...")
        with open("Exports/data/" + filename + '.json', "w") as jsonFile:
            json.dump(data_list, jsonFile)
        zip = zipfile.ZipFile("Exports/data/" + filename + '.zip', 'w')
        zip.write("Exports/data/" + filename + '.json', filename + '.json', compress_type=zipfile.ZIP_DEFLATED)
        if os.path.exists(os.path.join(dir, "../../Exports/data/" + filename + '.json')):
            os.remove(os.path.join(dir, "../../Exports/data/" + filename + '.json'))
        else:
            print("ERROR")
        log("ZIP file was saved!")
        path.append(os.path.abspath(os.path.join(dir, "../../Exports/data/" + filename + '.zip')))
    if export_csv:
        if not os.path.exists("Exports/data/" + filename):
            os.makedirs("Exports/data/" + filename)
        for index, id in enumerate(tasks_ids):
            log("Exporting CSV {} of {}".format(index+1, len(tasks_ids)))
            s = Subject.query.get(Task.query.get(id).subject_id)
            t = Task.query.get(id).start_time
            csv_path = os.path.join(dir, "../../Exports/data/" + filename + "/" + s.serial + "--" + time.strftime(
                '%Y-%m-%d--%H-%M-%S', time.localtime(t)) + '.csv')
            f = open(csv_path, "w")
            call(
                ["influxdb\influx.exe", "-database", "Tasks", "-execute", "select * from task" + str(id), "-format",
                 "csv", "-precision", "rfc3339"], stdout=f)
            f.close()
            from cognitests.modules.fixExcel import utf_to_windows
            utf_to_windows(csv_path)
        log("Done!")
        path.append(os.path.abspath(os.path.join(dir, "../../Exports/data/" + filename)))

    return path


def import_tasks_data(path, log=print):
    try:
        log("Starting the import process...")
        if zipfile.is_zipfile(path):
            archive = zipfile.ZipFile(path, 'r')
            for file in archive.namelist():
                data = archive.read(file)
                unzippedjson = json.loads(data.decode("utf-8"))
                return insert_tasks(unzippedjson, log)
        else:
            with open(path, "r") as jsonFile:
                data = json.load(jsonFile)
                return insert_tasks(data, log)
    except Exception as e:
        print(e)
        log("Couldn't import: Reason: " + str(e))
        return ["Couldn't import: Reason: " + str(e)]


def insert_tasks(tasks, console=print):
    log = []
    for index, data in enumerate(tasks):
        try:
            console("Importing task {} of {}...".format(index+1, len(tasks)))
            s = data['subject']
            t = data['task']
            g = []
            if "groups" in data:
                g = data["groups"]
            s.pop('id', None)
            t.pop('id', None)
            s_id = insertSubject(s)
            task = Task(**t)
            task.subject_id = s_id
            db.session.add(task)
            db.session.flush()
            db.session.refresh(task)
            t_id = task.id
            for group in g:
                exists = db.session.query(
                    db.exists().where(PartOfGroup.group_id == group[0] and PartOfGroup.subject_id == s_id)).scalar()
                if not exists:
                    db.session.add(PartOfGroup(group_id=group[0], subject_id=s_id))
            db.session.commit()
            insert_data(data["results"], t_id)
            log.append("Imported: Subject: " + s['name'] + " Started: " + time.strftime('%Y-%m-%d %H:%M:%S',
                                                                                        time.localtime(
                                                                                            t['start_time'])))
            console("Imported: Subject: " + s['name'] + " Started: " + time.strftime('%Y-%m-%d %H:%M:%S',
                                                                                        time.localtime(
                                                                                            t['start_time'])))
        except Exception as e:
            log.append("Couldn't import: " + str(e))
            console("Couldn't import: " + str(e))
    return log


def to_float(i):
    if isinstance(i, int):
        return float(i)
    else:
        return i


def insert_data(data, task_id):
    print(data)
    allData = []
    points = {}
    for result in data:
        series = result['series'][0]
        print(series)
        points["measurement"] = "task" + str(task_id)
        cols = series["columns"]
        count = 0
        for vals in series["values"]:
            count += 1
            points["time"] = vals[0]
            points["fields"] = dict(zip(cols[1:], [to_float(i) for i in vals[1:]]))
            allData.append(copy.deepcopy(points))
        insertjson(allData)


# *********************************Subjects*******************************************************


def exportSubjects(subjects_ids=[], filename="default", log=print):
    if not os.path.exists("Exports/subjects/"):
        os.makedirs("Exports/subjects/")
    data = {"subjects": []}
    for index, id in enumerate(subjects_ids):
        log("Exporting subject {} of {}...".format(index + 1, len(subjects_ids)))
        s = Subject.query.get(id)
        s_dict = s.as_dict()
        s_dict["groups"] = db.session.query(PartOfGroup.group_id).filter_by(subject_id=id).all()
        if s:
            data["subjects"].append(s_dict)
    log("Saving the ZIP file...")
    with open(os.path.join(dir, "../../Exports/subjects/" + filename + '.json'), "w") as jsonFile:
        json.dump(data, jsonFile)
    f = zipfile.ZipFile(os.path.join(dir, "../../Exports/subjects/" + filename + '.zip'), 'w')
    f.write(os.path.join(dir, "../../Exports/subjects/" + filename + '.json'), filename + '.json',
            compress_type=zipfile.ZIP_DEFLATED)
    if os.path.exists(os.path.join(dir, "../../Exports/subjects/" + filename + '.json')):
        os.remove(os.path.join(dir, "../../Exports/subjects/" + filename + '.json'))
    else:
        print("ERROR")
    log("ZIP file was saved!")
    return os.path.abspath(os.path.join(dir, "../../Exports/subjects/" + filename + '.zip'))


def importSubjects(path, console):
    try:
        if zipfile.is_zipfile(path):
            archive = zipfile.ZipFile(path, 'r')
            for file in archive.namelist():
                data = archive.read(file)
                unzippedjson = json.loads(data.decode("utf-8"))
                try:
                    return insert_subjects(unzippedjson['subjects'], console)
                except:
                    return ["File is corrupted"]
        else:
            with open(path, "r") as jsonFile:
                data = json.load(jsonFile)
                try:
                    return insert_subjects(data['subjects'], console)
                except:
                    return ["File is corrupted"]
    except Exception as e:
        return ["Couldn't import: Reason: " + str(e)]


def insert_subjects(data,console):
    log = []
    for index, subject in enumerate(data):
        try:
            console("Importing subject {} of {}".format(index+1, len(data)))
            subject.pop('id', None)
            subject.pop('group_id', None)
            groups = subject.pop('groups', None)
            new_id = insertSubject(subject, True)
            for group in groups:
                db.session.add(PartOfGroup(group_id=group[0], subject_id=new_id))
            log.append("Imported: Name: " + subject['name'] + " ,Serial: " + subject['serial'])
            console("Imported: Name: " + subject['name'] + " ,Serial: " + subject['serial'])
        except Exception as e:
            log.append("Couldn't import: " + str(subject) + " Reason: " + str(e))
            console("Couldn't import: " + str(e))
    db.session.commit()
    return log


def insertSubject(subject, throw=False):
    existingSubject = Subject.query.filter_by(serial=subject['serial']).first()
    print(existingSubject)
    if (existingSubject is None):
        subject = Subject(**subject)
        db.session.add(subject)
        db.session.flush()
        db.session.refresh(subject)
        return subject.id
    else:
        if throw:
            raise Exception("There's already a subject with this serial number.")
        return existingSubject.id


# *******************************Task Settings**********************************************************
def exportSettings(settings=[], filename="default", log=print):
    if not os.path.exists("Exports/settings/"):
        os.makedirs("Exports/settings/")
    data = {"settings": []}
    f = zipfile.ZipFile(os.path.join(dir, "../../Exports/settings/" + filename + '.zip'), 'w')
    for index, task in enumerate(settings):
        log("Exporting task settings {} of {}...".format(index+1, len(settings)))
        s = None
        if task["type"] == "nback":
            s = NbackSettings.query.get(task["id"])
        elif task["type"] == "eyes":
            s = EyesSettings.query.get(task["id"])
            if s.open_sound:
                f.write(os.path.join(dir, "../../DBS/sounds/" + s.open_sound), "sounds/" + s.open_sound,
                        compress_type=zipfile.ZIP_DEFLATED)
            if s.close_sound:
                f.write(os.path.join(dir, "../../DBS/sounds/" + s.close_sound), "sounds/" + s.close_sound,
                        compress_type=zipfile.ZIP_DEFLATED)
        elif task["type"] == "iaps":
            s = IAPSSettings.query.get(task["id"])
            for dirpath, dirs, files in os.walk(os.path.join(dir, "../../DBS/images/" + s.images_path)):
                for file in files:
                    fn = os.path.join(dirpath, file)
                    dest_name = os.path.relpath((os.path.join(dirpath, file)), os.path.join(dir, "../../DBS/images/"))
                    f.write(fn, "images/" + dest_name, compress_type=zipfile.ZIP_DEFLATED)
            f.write(os.path.join(dir, "../../DBS/images/masks/" + s.mask), "images/masks/" + s.mask,
                    compress_type=zipfile.ZIP_DEFLATED)
        if s:
            s = s.as_dict()
            s["type"] = task["type"]

            data["settings"].append(s)
    log("Saving the ZIP file...")
    with open(os.path.join(dir, "../../Exports/settings/" + filename + '.json'), "w") as jsonFile:
        json.dump(data, jsonFile)
    f.write(os.path.join(dir, "../../Exports/settings/" + filename + '.json'), filename + '.json',
            compress_type=zipfile.ZIP_DEFLATED)
    if os.path.exists(os.path.join(dir, "../../Exports/settings/" + filename + '.json')):
        os.remove(os.path.join(dir, "../../Exports/settings/" + filename + '.json'))
    else:
        print("ERROR")
    log("ZIP file was saved!")
    return os.path.abspath(os.path.join(dir, "../../Exports/settings/" + filename + '.zip'))


def importSettings(path, log):
    try:
        if zipfile.is_zipfile(path):
            archive = zipfile.ZipFile(path, 'r')
            for file in archive.namelist():
                if file.endswith(".json"):
                    data = archive.read(file)
                    unzippedjson = json.loads(data.decode("utf-8"))
                elif file.startswith('sounds/') or file.startswith('images/'):
                    archive.extract(file, os.path.join(dir, '../../DBS/'))
            return insertSettings(unzippedjson['settings'], log)
        else:
            with open(path, "r") as jsonFile:
                data = json.load(jsonFile)
                return insertSettings(data['settings'], log)
    except Exception as e:
        return ["Couldn't import: Reason: " + str(e)]


def insertSettings(data, console):
    log = []
    for index, settings in enumerate(data):
        console("Importing task settings {} of {}...".format(index+1, len(data)))
        task_type = settings["type"]
        settings.pop('type', None)
        existingSettings = None
        if task_type == "nback":
            existingSettings = NbackSettings.query.filter_by(name=settings['name']).first()
        elif task_type == "eyes":
            existingSettings = EyesSettings.query.filter_by(name=settings['name']).first()
        elif task_type == "iaps":
            existingSettings = IAPSSettings.query.filter_by(name=settings['name']).first()
        if existingSettings is None:
            settings.pop('id', None)
            if task_type == "nback":
                task = NbackSettings(**settings)
            elif task_type == "eyes":
                task = EyesSettings(**settings)
            elif task_type == "iaps":
                task = IAPSSettings(**settings)
            db.session.add(task)
            log.append("Imported: Name: " + settings['name'])
            console("Imported: Name: " + settings['name'])
        else:
            log.append(
                "Couldn't import: Name: " + settings['name'] + ", Reason: There's already a task with this name.")
            console(
                "Couldn't import: Name: " + settings['name'] + ", Reason: There's already a task with this name.")
    db.session.commit()
    return log


if __name__ == '__main__':
    # exportSettings([1,2,3], "settings")
    importSettings("E:\Dropbox\Project\Emotiv\Exports\settings.zip")
