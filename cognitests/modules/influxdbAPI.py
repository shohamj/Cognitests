import os
import subprocess

from influxdb import InfluxDBClient

host = 'localhost'
open_port = 8086
user = 'root'
password = 'root'
dbname = 'Tasks'
myclient = None
influx_server = None
dir = os.path.dirname(__file__)
path = os.path.dirname(os.path.realpath(__file__))
print("path", path)
def start_influx(open_port=None):
    global influx_server, myclient
    influxdEXE = os.path.abspath(path + "/../../influxdb/influxd.exe")
    influxdCONF = os.path.abspath(path + "/../../influxdb/influxdb.conf")
    print(influxdEXE, "-config", influxdCONF)
    influx_server = subprocess.Popen(
        [influxdEXE, "-config", influxdCONF],
        shell=False)
    # = InfluxDBClient(host, open_port, user, password, dbname)
    myclient = InfluxDBClient(database=dbname)
    # Create database if it doesn't exist
    try:
        dbs = myclient.get_list_database()
        print("Databases:", dbs)
        if not any(db['name'] == dbname for db in dbs):
            myclient.create_database(dbname)
    except:
        print("INFLUX_API_ERROR: Databases list is not available")


def close_influx():
    global influx_server
    if influx_server is not None:
        influx_server.kill()


def deletTask(task):
    global myclient
    myclient.delete_series(measurement=task)


def insert(type, table, data, log=False):
    global myclient
    jsondata = [{"measurement": table}]
    newData = {}
    for key in data:
        newData[key.replace("/", "_")] = data[key]
        # newData['type'] = type
    jsondata[0]["fields"] = newData
    jsondata[0]["tags"] = {'type': type}
    try:
        myclient.write_points(jsondata)
        if log:
            with open('real_log.txt', 'a') as the_file:
                the_file.write("insert - " + str(jsondata) + '\n')
    except Exception as e:
        print("Error while insert: ", e)


def insertjson(data):
    try:
        myclient.write_points(data)
    except Exception as e:
        print("Error while insert: ", e)


def insert_pow(table, data):
    insert("pow", table, data)


def insert_dev(table, data):
    insert("dev", table, data)


def insert_fac(table, data):
    insert("fac", table, data)


def insert_click(table, data):
    with open('real_log.txt', 'a') as the_file:
        the_file.write("insert_click - " + str(data) + '\n')
    data["target"] = data["target"].encode('utf-8')
    insert("click", table, data, log=True)


def insert_image_click(table, data):
    insert("click", table, data)


# def queryWave(task, wave, sensor_index):
# #    global data
# #    times = []
# #    values = []
# #    result = myclient.query('SHOW FIELD KEYS from ' + task)
# #    for x in result.get_points():
# #        for col in data.keys():
# #            if col in x["fieldKey"]:
# #                data[col].append(x["fieldKey"])
# #                break
# #    rs = myclient.query('select {} from {} '.format(data[wave][sensor_index], task)).get_points()
# #    for x in rs:
# #        times.append(x['time'].replace("'", " "))
# #        values.append(x[data[wave][sensor_index]])
# #    return times, values

def getTaskData(task, group_by_interval=False, interval=1):
    import time
    t = time.time()
    waves = {"alpha", "betaH", "betaL", "gamma", "theta"}
    data = []
    keys = myclient.query('SHOW FIELD KEYS from ' + task).get_points()
    for x in keys:
        for wave in waves:
            if wave in x["fieldKey"]:
                values = []
                times = []
                if group_by_interval:
                    minTime = myclient.query(
                        'select first({}),time from {}'.format(x["fieldKey"], task)).get_points()
                    minTime = list(minTime)[0]['time']
                    maxTime = myclient.query(
                        'select last({}),time from {}'.format(x["fieldKey"], task)).get_points()
                    maxTime = list(maxTime)[0]['time']
                    res = myclient.query("SELECT mean({}) FROM {} WHERE time >='{}' AND time <='{}' GROUP BY time({}s)"
                                         .format(x["fieldKey"], task, minTime, maxTime, interval)).get_points()
                else:
                    res = myclient.query("SELECT {} FROM {}".format(x["fieldKey"], task)).get_points()
                for row in res:
                    if group_by_interval:
                        values.append(row["mean"])
                    else:
                        values.append(row[x["fieldKey"]])
                    times.append(row["time"])
                data.append({'col': x["fieldKey"], 'data': {"times": times, "values": values}})
                break
    print("GetTaskData -", task, "group_by_interval", group_by_interval, "interval", interval, "Time took:", time.time()-t)
    return data


def getNbackTaskClicks(task):
    clicks = []
    res = myclient.query('select clicked, delay, target, is_correct from ' + task).get_points()
    for x in res:
        clicks.append(x)
    return clicks


def getIAPSTaskClicks(task):
    clicks = []
    res = myclient.query('select display_time, image, reaction_time, response, category from ' + task).get_points()
    for x in res:
        clicks.append(x)
    return clicks


def getEyesStatesTimes(task):
    times = []
    res = list(myclient.query('select eyesState from ' + task).get_points())
    if res:
        lastState = res[0]["eyesState"]
        currentTime = {"start": res[0]["time"], "end": None, "state": res[0]["eyesState"]}
        for x in res[1:-1]:
            if x["eyesState"] != lastState:
                currentTime["end"] = x["time"]
                times.append(currentTime)
                currentTime = {"start": x["time"], "end": None, "state": x["eyesState"]}
            lastState = x["eyesState"]
        currentTime["end"] = res[-1]["time"]
        times.append(currentTime)
    return times


def getTaskSensors(task):
    waves = ["alpha", "betaH", "betaL", "gamma", "theta"]
    fields = list(myclient.query('SHOW FIELD KEYS from ' + task).get_points())
    sensors = []
    for field in fields:
        if '_' in field['fieldKey'] and field['fieldType'] == 'float':
            if field['fieldKey'].split('_')[1] in waves:
                sensors.append(field['fieldKey'].split('_')[0])  # for example 'AF3_alpha'
    sensors = list(dict.fromkeys(sensors))
    return sensors


def getTaskMeansByStatus(task, status, round=None):
    roundQuery = " AND round!='Waiting' AND round!='Trial Round' AND round!='' "
    if round:
        roundQuery = " AND round='" + round + "'"
    means = myclient.query(
        'select MEAN(*) from ' + task + " where status=" + "'" + status + "'" + roundQuery).get_points()
    means = list(means)
    if len(means) > 0:
        return means[0]
    else:
        return []


def getTaskMeansByEyesState(task, state, round=None):
    roundQuery = " AND round!='Waiting' AND round!='Trial Round' AND round!='' "
    if round:
        roundQuery = " AND round='" + round + "'"
    means = myclient.query(
        'select MEAN(*) from ' + task + " where eyesState=" + "'" + state + "'" + roundQuery).get_points()
    means = list(means)
    if len(means) > 0:
        return means[0]
    else:
        return []


def getTaskMaxByEyesState(task, state, round=None):
    roundQuery = " AND round!='Waiting' AND round!='Trial Round' AND round!='' "
    if round:
        roundQuery = " AND round='" + round + "'"
    means = myclient.query(
        'select MAX(*) from ' + task + " where eyesState=" + "'" + state + "'" + roundQuery).get_points()
    means = list(means)
    if len(means) > 0:
        return means[0]
    else:
        return []


def getClicksAnalysis(task, diff=None, round=None):
    diffString = ""
    if diff:
        diffString = " AND difficulty=" + str(diff)
    roundQuery = " AND round!='Waiting' AND round!='Trial Round' AND round!='' "
    if round:
        roundQuery = " AND round='" + round + "'"
    print(
        'SELECT * FROM ' + task + " WHERE type='click' AND (is_correct=true OR is_correct=1)" + diffString + roundQuery)
    correct = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (is_correct=true OR is_correct=1)" + diffString + roundQuery).get_points()
    incorrect = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (is_correct=false OR is_correct=0)" + diffString + roundQuery).get_points()
    cc = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (clicked=true OR clicked=1) AND (is_correct=true OR is_correct=1)" + diffString + roundQuery).get_points()
    ci = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (clicked=true OR clicked=1) AND (is_correct=false OR is_correct=0)" + diffString + roundQuery).get_points()
    ac = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (clicked=false OR clicked=0) AND (is_correct=true OR is_correct=1)" + diffString + roundQuery).get_points()
    ai = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (clicked=false OR clicked=0) AND (is_correct=false OR is_correct=0)" + diffString + roundQuery).get_points()
    correct_delay = myclient.query(
        'SELECT MEAN(delay) FROM ' + task + " WHERE type='click' AND (is_correct=true OR is_correct=1) AND delay > 0" + diffString + roundQuery).get_points()
    correct_delay = list(correct_delay)
    incorrect_delay = myclient.query(
        'SELECT MEAN(delay) FROM ' + task + " WHERE type='click' AND (is_correct=false OR is_correct=0) AND delay > 0" + diffString + roundQuery).get_points()
    incorrect_delay = list(incorrect_delay)
    cc_delay = myclient.query(
        'SELECT MEAN(delay) FROM ' + task + " WHERE type='click' AND (clicked=true OR clicked=1) AND (is_correct=true OR is_correct=1) AND delay > 0" + diffString + roundQuery).get_points()
    cc_delay = list(cc_delay)
    ci_delay = myclient.query(
        'SELECT MEAN(delay) FROM ' + task + " WHERE type='click' AND (clicked=true OR clicked=1) AND (is_correct=false OR is_correct=0) AND delay > 0" + diffString + roundQuery).get_points()
    ci_delay = list(ci_delay)
    print("cc_delay", cc_delay, "ci_delay", ci_delay)
    analysis = {"correct": {}, "incorrect": {}, "cc": {}, "ci": {}, "ac": {}, "ai": {}}
    analysis["correct"]["amount"] = len(list(correct))
    analysis["incorrect"]["amount"] = len(list(incorrect))
    analysis["cc"]["amount"] = len(list(cc))
    analysis["ci"]["amount"] = len(list(ci))
    analysis["ac"]["amount"] = len(list(ac))
    analysis["ai"]["amount"] = len(list(ai))
    sum_clicks = analysis["correct"]["amount"] + analysis["incorrect"]["amount"]
    if sum_clicks:
        analysis["correct"]["percentage"] = (100 * analysis["correct"]["amount"]) / sum_clicks
        analysis["incorrect"]["percentage"] = 100 - analysis["correct"]["percentage"]
        analysis["cc"]["percentage"] = (100 * analysis["cc"]["amount"]) / sum_clicks
        analysis["ci"]["percentage"] = (100 * analysis["ci"]["amount"]) / sum_clicks
        analysis["ac"]["percentage"] = (100 * analysis["ac"]["amount"]) / sum_clicks
        analysis["ai"]["percentage"] = (100 * analysis["ai"]["amount"]) / sum_clicks
    else:
        analysis["correct"]["percentage"] = 0
        analysis["incorrect"]["percentage"] = 0
        analysis["cc"]["percentage"] = 0
        analysis["ci"]["percentage"] = 0
        analysis["ac"]["percentage"] = 0
        analysis["ai"]["percentage"] = 0
    analysis["correct"]["delay"] = correct_delay[0]['mean'] if len(correct_delay) > 0 else "None"
    analysis["incorrect"]["delay"] = incorrect_delay[0]['mean'] if len(incorrect_delay) > 0 else "None"
    analysis["cc"]["delay"] = cc_delay[0]['mean'] if len(cc_delay) > 0 else "None"
    analysis["ci"]["delay"] = ci_delay[0]['mean'] if len(ci_delay) > 0 else "None"
    analysis["ac"]["delay"] = "None"
    analysis["ai"]["delay"] = "None"
    return analysis


def getMeanForClicks(clicks, task):
    waves = {"alpha", "betaH", "betaL", "gamma", "theta"}
    res = {}
    counter = 0
    for click in clicks:
        correct_time_slices = "(time <= '" + click["time"] + "' AND time >= '" + subMS(click["time"], 2500) + "')"
        query = 'SELECT * FROM ' + task + " WHERE type='pow' AND" + correct_time_slices
        t = myclient.query(query).get_points()
        for row in t:
            counter += 1
            for key in row:
                if any(wave in key for wave in waves):
                    if key not in res:
                        res[key] = 0
                    res[key] += row[key]
    for key in res:
        res[key] /= counter
    return res


def getClicksWavesMeansV2(task, round=None):
    roundQuery = " AND round!='Waiting' AND round!='Trial Round' AND round!='' "
    if round:
        roundQuery = " AND round='" + round + "'"
    correct = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (is_correct=true OR is_correct=1)" + roundQuery).get_points()
    incorrect = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (is_correct=false OR is_correct=0)" + roundQuery).get_points()
    res = {}
    correct_data = getMeanForClicksV2(correct, task)
    incorrect_data = getMeanForClicksV2(incorrect, task)
    res["correct"] = correct_data if correct_data else []
    res["incorrect"] = incorrect_data if incorrect_data else []
    return res

def getClicksWavesMeans(task, round=None):
    roundQuery = " AND round!='Waiting' AND round!='Trial Round' AND round!='' "
    if round:
        roundQuery = " AND round='" + round + "'"
    correct = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (is_correct=true OR is_correct=1)" + roundQuery).get_points()
    incorrect = myclient.query(
        'SELECT * FROM ' + task + " WHERE type='click' AND (is_correct=false OR is_correct=0)" + roundQuery).get_points()
    res = {}
    correct_data = getMeanForClicks(correct, task)
    incorrect_data = getMeanForClicks(incorrect, task)
    res["correct"] = correct_data if correct_data else []
    res["incorrect"] = incorrect_data if incorrect_data else []
    return res


def subMS(date, ms):
    from dateutil.parser import parse
    from datetime import timedelta
    sub = parse(date)
    sub -= timedelta(milliseconds=ms)
    utc_str = sub.isoformat("T")
    return utc_str.split("+")[0] + "Z"


def getMeanForWaves(task, round=None):
    roundQuery = " where round!='Waiting' AND round!='Trial Round'"
    if round:
        roundQuery = " where round='" + round + "'"
    waves = {"alpha", "betaH", "betaL", "gamma", "theta"}
    res = {}
    for wave in waves:
        wave_means = list(myclient.query('select mean(/' + wave + '/) from ' + task + roundQuery).get_points())
        sum = 0
        if wave_means:
            wave_means[0].pop("time")
            print(wave_means)
            for mean in wave_means[0]:
                sum += wave_means[0][mean]
            print(sum, len(wave_means[0]))
            sum /= len(wave_means[0])
        else:
            sum = "None"
        res[wave] = sum
    print(res)


def getAllWaves(tasks, round=None):
    roundQuery = " where round!='Waiting' AND round!='Trial Round'"
    if round:
        roundQuery = " where round='" + round + "'"
    print(roundQuery)
    waves = {"alpha", "betaH", "betaL", "gamma", "theta"}
    res = dict(alpha=[], betaH=[], betaL=[], gamma=[], theta=[])
    for task in tasks:
        for wave in waves:
            t = list(myclient.query('select /' + wave + '/ from ' + task + roundQuery).get_points())
            print(t)
            if t:
                for line in t:
                    line.pop("time")
                    for sensor in line:
                        res[wave].append(line[sensor])

    return res


def getClicksAnalysisByDifficulty(task, round=None):
    res = {}
    levels = list(myclient.query('select distinct(difficulty) from ' + task).get_points())
    print(levels)

    for level in levels:
        nback = level["distinct"]
        if nback > 0:
            res[str(nback)] = getClicksAnalysis(task, nback, round)
    return res


def getTaskRounds(task):
    res = []
    rounds = list(myclient.query('select distinct(round) from ' + task).get_points())
    for round in rounds:
        res.append(round['distinct'])
    return res


def getTaskIAPSRounds(task):
    res = []
    rounds = list(myclient.query('select distinct(display_time) from ' + task).get_points())
    for round in rounds:
        res.append(round['distinct'])
    res.sort()
    return res


def getRTByDT(tasks):
    if not isinstance(tasks, (list,)):
        tasks = [tasks]
    res = {}
    for task in tasks:
        dts = getTaskIAPSRounds(task)
        for dt in dts:
            rt = list(
                myclient.query('select reaction_time from ' + task + ' where display_time=' + str(dt)).get_points())
            dt_rt = []
            for t in rt:
                if 'reaction_time' in t:
                    dt_rt.append(t['reaction_time'])
            if str(dt) not in res:
                res[str(dt)] = dt_rt
            else:
                res[str(dt)] += dt_rt

    return res


def getPrecentByDT(tasks):
    if not isinstance(tasks, (list,)):
        tasks = [tasks]
    res = {}
    for task in tasks:
        dts = getTaskIAPSRounds(task)
        for dt in dts:
            responses = list(
                myclient.query('select response from ' + task + ' where display_time=' + str(dt)).get_points())
            dt_res = []
            for response in responses:
                if 'response' in response:
                    dt_res.append(response['response'])
            if str(dt) not in res:
                res[str(dt)] = dt_res
            else:
                res[str(dt)] += dt_res
    for dt in res:
        len_res = len(res[dt])
        res[dt] = {"Pleasant": res[dt].count("Pleasant") * 100 / len_res,
                   "Unpleasant": res[dt].count("Unpleasant") * 100 / len_res,
                   "Neutral": res[dt].count("Neutral") * 100 / len_res}
    return res


def getClicksByCategory(tasks):
    if not isinstance(tasks, (list,)):
        tasks = [tasks]
    res = {}
    print(tasks)
    for task in tasks:
        categories = list(myclient.query('select DISTINCT(category) from ' + task).get_points())
        print("categories:::", categories)
        for category in categories:
            cat_name = category["distinct"]
            if cat_name not in res:
                res[cat_name] = {'amount': 0, 'rt': 0, 'unpleasant': 0, 'pleasant': 0, 'neutral': 0}
            count = list(
                myclient.query(
                    "select count(category) from " + task + " where category='" + cat_name + "'").get_points())
            if count:
                last_count = res[cat_name]["amount"]
                res[cat_name]["amount"] += count[0]["count"]
            print("Count:", count)
            mean = list(myclient.query(
                "select MEAN(reaction_time) from " + task + " where category='" + cat_name + "'").get_points())
            print("MEan:", mean)
            if mean:
                res[cat_name]["rt"] = (count[0]["count"] * mean[0]["mean"] + last_count * res[cat_name]["rt"]) / \
                                      res[cat_name]["amount"]
            for response in ("Unpleasant", "Pleasant", "Neutral"):
                res_amount = list(
                    myclient.query(
                        "select COUNT(response) from " + task + " where response='" + response + "' and category='" + cat_name + "'").get_points())
                print(res_amount)
                if res_amount:
                    last_precent = res[cat_name][response.lower()]
                    t = last_precent * last_count
                    res[cat_name][response.lower()] = (t + res_amount[0]["count"]) / res[cat_name]["amount"]
    for cat in res:
        res[cat]["unpleasant"] = str(round(res[cat]["unpleasant"] * 100, 1)) + "%"
        res[cat]["pleasant"] = str(round(res[cat]["pleasant"] * 100, 1)) + "%"
        res[cat]["neutral"] = str(round(res[cat]["neutral"] * 100, 1)) + "%"
    return res


def getAllPictures(task):
    return list(myclient.query(
        'select image, category, display_time, reaction_time, response from ' + task + " where type='click'").get_points())


def getPicturesTimes(task, by_query):
    points = list(myclient.query(
        'select display_time from ' + task + " where type='click' and " + by_query).get_points())
    times = []
    for point in points:
        times.append({"start": subMS(point["time"], point["display_time"] * 1000), "end": point["time"]})
    # ***********************************************************************************************
    queries = "SELECT mean(*) FROM "
    for time in times:
        time_slices = "(time <= '" + time["end"] + "' AND time >= '" + time["start"] + "')"
        queries += '(SELECT mean(*) FROM ' + task + " WHERE type='pow' AND " + time_slices + "),"
    queries = queries[:-1]
    try:
        t = list(myclient.query(queries).get_points())[0]
    except:
        t = {}
    return t


def getTaskMeansByStatusV2(task, status, round=None):
    import numpy as np
    round_query = "round!='Waiting' AND round!='Trial Round' AND round!='' "
    if round:
        round_query = "round='" + round + "'"
    waves = {"alpha", "betaH", "betaL", "gamma", "theta"}
    sensors = getTaskSensors(task)
    query = "SELECT * FROM (SELECT * FROM {} where (type='pow' and round!='') OR type='dev' fill(previous)) WHERE type='pow' AND status='{}' AND {}".format(task, status, round_query)
    rows = myclient.query(query).get_points()
    res = {}
    for wave in waves:
        for sensor in sensors:
            res[sensor + '_' + wave] = []
    for row in rows:
        for sensor in sensors:
            if isinstance(row[sensor], int) and row[sensor] > 2:
                for wave in waves:
                    res[sensor + '_' + wave].append(row[sensor + '_' + wave])
    for key in res:
        if len(res[key]) > 1:
            arr = np.array(res[key])
            mean = np.mean(arr)
            std = np.std(arr)
            norm_arr = arr[((arr >= mean -2*std) & (arr <= mean + 2*std))]
            print("****************************************{}***********************************************".format(key))
            print(norm_arr)
            res[key] = np.mean(norm_arr)
        else:
            res[key] = None

        # res[key] = list(norm_arr)
    return res

def getMeanForClicksV2(clicks, task):
    import numpy as np
    waves = {"alpha", "betaH", "betaL", "gamma", "theta"}
    sensors = getTaskSensors(task)
    res = {}
    for wave in waves:
        for sensor in sensors:
            res[sensor + '_' + wave] = []
    for click in clicks:
        correct_time_slices = "(time <= '" + click["time"] + "' AND time >= '" + subMS(click["time"], 2500) + "')"
        # query = 'SELECT * FROM ' + task + " WHERE type='pow' AND" + correct_time_slices
        query = "SELECT * FROM (SELECT * FROM {} where (type='pow' and round!='') OR type='dev' fill(previous)) WHERE type='pow' AND {}".format(
            task, correct_time_slices)
        rows = myclient.query(query).get_points()
        for row in rows:
            for sensor in sensors:
                if isinstance(row[sensor], int) and row[sensor] > 2:
                    for wave in waves:
                        res[sensor + '_' + wave].append(row[sensor + '_' + wave])
    for key in res:
        if len(res[key]) > 1:
            arr = np.array(res[key])
            mean = np.mean(arr)
            std = np.std(arr)
            norm_arr = arr[((arr >= mean -2*std) & (arr <= mean + 2*std))]
            res[key] = np.mean(norm_arr)
        else:
            res[key] = None
    return res

def getTaskDataV2(task, group_by_interval=False, interval=1):
    import time
    t = time.time()
    waves = ["alpha", "betaH", "betaL", "gamma", "theta"]
    sensors = getTaskSensors(task)
    res = []
    if group_by_interval:
        first = sensors[0] + '_' + waves[0]
        minTime = myclient.query(
            'select first({}),time from {}'.format(first,task)).get_points()
        minTime = list(minTime)[0]['time']

        maxTime = myclient.query(
            'select last({}),time from {}'.format(first,task)).get_points()
        maxTime = list(maxTime)[0]['time']
        rows = myclient.query("SELECT mean(*) FROM {} WHERE time >='{}' AND time <='{}' GROUP BY time({}s)".format(task, minTime, maxTime, interval)).get_points()
        rows = list(rows)
    else:
        rows = list(myclient.query("SELECT * FROM {} WHERE type='pow' ".format(task)).get_points())

    for wave in waves:
        for sensor in sensors:
            col = sensor + '_' + wave
            data = {'times': [], 'values': []}
            for row in rows:
                data['times'].append(row['time'])
                if group_by_interval:
                    data['values'].append(row['mean_' + col])
                else:
                    data['values'].append(row[col])
            res.append({'col': col, 'data': data})
    print("getTaskDataV2:", time.time() - t)
    return res
if __name__ == '__main__':
    # start_influx()
    myclient = InfluxDBClient(database=dbname)

    import cProfile
    # data = getClicksWavesMeans("task6")["correct"]
    # dataV2 = getClicksWavesMeansV2("task6")["correct"]
    # for key in dataV2:
    #     print(key+":", "V1:", data[key], "V2:", dataV2[key])
    # data = getTaskMeansByStatus("task1", "rest")
    # dataV2 = getTaskMeansByStatusV2("task1", "rest")
    # for key in dataV2:
    #     print(key+":", "V1:", data['mean_'+key], "V2:", dataV2[key])
    # cProfile.run('getTaskDataV2("task3", group_by_interval=True, interval=10)')
    data = getTaskMeansByStatusV2("task8", 'rest', 'Round 3')
    print(data["F3_alpha"])
    # dv2 = getTaskDataV2("task3")
    # dv1 = getTaskData("task3")
    # print(dv2)
    # data = getTaskData("task40", group_by_interval=False, interval=10)
    # print(list(data)[0])
    # getTaskData("task4", group_by_interval=True, interval=1)
    # getTaskData("task4", group_by_interval=True, interval=5)
    # getTaskData("task4", group_by_interval=True, interval=10)
    # close_influx()
