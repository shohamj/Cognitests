import numpy as np
import xlsxwriter

import Scripts.influxdbAPI as influx


def createTable(name, wb, ws, start_index, waves, sensors, data):
    table_data = []
    print("createTable", data)
    for sensor in sensors:
        arr = [sensor]
        for wave in waves:
            found = False
            for key in data:
                if sensor + '_' + wave in key:
                    arr.append(data[key])
                    found = True
            if not found:
                arr.append("None")
        table_data.append(arr)
    cols = [{'header': 'Sensor'}]
    for wave in waves:
        cols.append({'header': wave})
    merge_format = wb.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter'})
    end_index = (start_index[0] + len(sensors), start_index[1] + len(waves))
    print(end_index)
    ws.merge_range(start_index[0], start_index[1], start_index[0], end_index[1], name, merge_format)
    ws.add_table(start_index[0] + 1, start_index[1], end_index[0] + 1, end_index[1],
                 {"data": table_data, 'columns': cols, 'style': 'Table Style Light 9'})
    return end_index


def createClicksTable(name, wb, ws, analysis, start_index):
    cols = ["Info", "Correct", "Incorrect", "Clicked Correctly", "Clicked Incorrectly", "Avoided Correctly",
            "Avoided Incorrectly"]
    columns = []
    for col in cols:
        columns.append({'header': col})
    data = [["Amount"], ["Percentage"], ["Delay"]]
    for type in analysis:
        value = analysis[type]
        data[0].append(value["amount"])
        data[1].append(str(round(value["percentage"], 2)) + "%")
        data[2].append(value["delay"])
    print(data)
    end_index = (start_index[0] + 3, start_index[1] + 6)
    merge_format = wb.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter'})
    ws.merge_range(start_index[0], start_index[1], start_index[0], end_index[1], name, merge_format)
    ws.add_table(start_index[0] + 1, start_index[1], end_index[0] + 1, end_index[1],
                 {"data": data, 'columns': columns, 'style': 'Table Style Light 9'})


def exportNBackTaskAnalysis(wb, sheet_name, task_id, round=None):
    ws = wb.add_worksheet(sheet_name)
    cells_format = wb.add_format({'align': 'left'})
    ws.set_column(0, 100, 10, cells_format)
    start_index = (2, 1)
    waves = ["alpha", "betaH", "betaL", "gamma", "theta"]
    sensors = influx.getTaskSensors("task" + str(task_id))
    data_rest = influx.getTaskMeansByStatus("task" + str(task_id), "rest", round=round)
    createTable("Rest", wb, ws, start_index, waves, sensors, data_rest)
    data_between = influx.getTaskMeansByStatus("task" + str(task_id), "between", round=round)
    createTable("Between", wb, ws, (start_index[0] + len(sensors) + 3, start_index[1]), waves, sensors, data_between)
    data_targets = influx.getTaskMeansByStatus("task" + str(task_id), "target", round=round)
    createTable("Targets", wb, ws, (start_index[0], start_index[1] + len(waves) + 3), waves, sensors, data_targets)
    data_non_targets = influx.getTaskMeansByStatus("task" + str(task_id), "no-target", round=round)
    createTable("Non-Targets", wb, ws, (start_index[0] + len(sensors) + 3, start_index[1] + len(waves) + 3), waves,
                sensors, data_non_targets)
    clicks_analysis = influx.getClicksAnalysis("task" + str(task_id), round=round)
    clicks_index = (start_index[0] + 2 * len(sensors) + 6, start_index[1])
    createClicksTable("Clicks Analysis - Overall", wb, ws, clicks_analysis,
                      (clicks_index[0] + len(sensors) + 3, clicks_index[1] + 3))
    clicks_waves_analysis = influx.getClicksWavesMeans("task" + str(task_id), round=round)
    createTable("1500ms Before Correct Targets", wb, ws, (clicks_index[0], clicks_index[1]), waves, sensors,
                clicks_waves_analysis["correct"])
    createTable("1500ms Before Incorrect Targets", wb, ws, (clicks_index[0], clicks_index[1] + 3 + len(waves)), waves,
                sensors, clicks_waves_analysis["incorrect"])
    clicks_analysis_by_diff = influx.getClicksAnalysisByDifficulty("task" + str(task_id), round=round)
    clicks_analysis_by_diff_index = (clicks_index[0] + len(sensors) + 3 + 6, clicks_index[1] + 3)
    import collections
    levels = collections.OrderedDict(sorted(clicks_analysis_by_diff.items()))
    for level in levels:
        createClicksTable("Clicks Analysis - Difficulty: " + level, wb, ws, levels[level],
                          clicks_analysis_by_diff_index)
        clicks_analysis_by_diff_index = (clicks_analysis_by_diff_index[0] + 6, clicks_analysis_by_diff_index[1])


def exportMultipleTasksAnalysis(tasks, dir_path, type, log):
    for i, task in enumerate(tasks):
        log("           Starting to export task " + str(i + 1) + " out of " + str(len(tasks)) + "...")
        exportTask(task, dir_path, type, log)
        log("           Done!")


def exportGeneralAnalysis(wb, tasks, sheet_name, round=None):
    allwaves = influx.getAllWaves(tasks, round=round)
    print(allwaves)
    ws = wb.add_worksheet(sheet_name)
    cells_format = wb.add_format({'align': 'left'})
    ws.set_column(0, 100, 10, cells_format)
    waves = ["alpha", "betaH", "betaL", "gamma", "theta"]
    cols = ["Wave", "Mean", "Median", "Range", "25th", "75th"]
    columns = []
    start_index = (3, 5)
    end_index = (len(waves) + 3, 4 + len(cols))
    for col in cols:
        columns.append({'header': col})
    table_data = []
    for wave in waves:
        arr = []
        a = np.array(allwaves[wave])
        print(a)
        arr.append(wave)
        arr.append(np.mean(a))
        arr.append(np.median(a))
        arr.append(np.max(a) - np.min(a))
        arr.append(np.percentile(a, 25))
        arr.append(np.percentile(a, 75))
        table_data.append(arr)
    print(table_data)
    merge_format = wb.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter'})
    ws.merge_range(start_index[0], start_index[1], start_index[0], end_index[1],
                   "General Analysis of All The Tasks Combined", merge_format)
    ws.add_table(start_index[0] + 1, start_index[1], end_index[0] + 1, end_index[1],
                 {"data": table_data, 'columns': columns, 'style': 'Table Style Light 9'})


def export(tasks, dir_path, type, log=lambda x: print(x)):
    try:
        log("Starting to export...")
        import os
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        workbook = xlsxwriter.Workbook(dir_path + "/" + "General" + ".xlsx")
        ts = []
        for t in tasks:
            ts.append("task" + str(t["id"]))
        rounds = influx.getTaskRounds(ts[0])
        log("   Starting general analysis...")
        log("       Starting general analysis - Overall")
        exportGeneralAnalysis(workbook, ts, "Overall")
        log("       Done!")
        for round in rounds:
            log("       Starting general analysis - " + round)
            exportGeneralAnalysis(workbook, ts, round, round=round)
            log("       Done!")
        log("   Done!")
        workbook.close()
        log("   Starting to export single task analysis!")
        exportMultipleTasksAnalysis(tasks, dir_path, type, log)
        log("   Done!")
    except Exception as e:
        log("ERROR! - " + str(e))


def exportEyesTaskAnalysis(wb, sheet_name, task_id, round=None):
    ws = wb.add_worksheet(sheet_name)
    cells_format = wb.add_format({'align': 'left'})
    ws.set_column(0, 100, 10, cells_format)
    start_index = (2, 1)
    waves = ["alpha", "betaH", "betaL", "gamma", "theta"]
    sensors = influx.getTaskSensors("task" + str(task_id))
    print("Sensors:", sensors)
    data_open = influx.getTaskMeansByEyesState("task" + str(task_id), "Open", round=round)
    createTable("Eyes Open - Mean", wb, ws, start_index, waves, sensors, data_open)
    data_closed = influx.getTaskMeansByEyesState("task" + str(task_id), "Open", round=round)
    createTable("Eyes Closed - Mean", wb, ws, (start_index[0], start_index[1] + len(waves) + 3), waves, sensors,
                data_closed)
    data_open = influx.getTaskMaxByEyesState("task" + str(task_id), "Open", round=round)
    createTable("Eyes Open - Max", wb, ws, (start_index[0] + len(sensors) + 3, start_index[1]), waves, sensors,
                data_open)
    data_closed = influx.getTaskMaxByEyesState("task" + str(task_id), "Open", round=round)
    createTable("Eyes Closed - Max", wb, ws, (start_index[0] + len(sensors) + 3, start_index[1] + len(waves) + 3),
                waves,
                sensors, data_closed)


def exportTask(task, dir_path, type, log):
    workbook = xlsxwriter.Workbook(dir_path + "/" + task["name"] + ".xlsx")
    rounds = influx.getTaskRounds("task" + str(task["id"]))
    log("               Analysing all the rounds combined...")
    if type == 'nback':
        exportNBackTaskAnalysis(workbook, "Overall", task["id"])
    elif type == 'eyes':
        exportEyesTaskAnalysis(workbook, "Overall", task["id"])

    log("               Done!")
    for round in rounds:
        if round != "Waiting":
            log("           Analysing " + round + "...")
            if type == 'nback':
                exportNBackTaskAnalysis(workbook, round, task["id"], round=round)
            elif type == 'eyes':
                exportEyesTaskAnalysis(workbook, round, task["id"], round=round)
            log("           Done!")
    workbook.close()


def IAPSMeanRT(tasks, wb, ws, start_index, log=lambda x: print(x)):
    men = []
    women = []
    all_ids = []
    for task in tasks:
        if task["gender"] == "male":
            men.append(task["id"])
        else:
            women.append(task["id"])
        all_ids.append(task["id"])
    men_rt = influx.getRTByDT(men)
    women_rt = influx.getRTByDT(women)
    overall_rt = influx.getRTByDT(all_ids)
    print(men_rt)
    men_rt_mean = {}
    women_rt_mean = {}
    overall_rt_mean = {}
    for rt in men_rt:
        men_rt_mean[rt] = np.mean(np.array(men_rt[rt]))
    for rt in women_rt:
        women_rt_mean[rt] = np.mean(np.array(women_rt[rt]))
    for rt in overall_rt:
        overall_rt_mean[rt] = np.mean(np.array(overall_rt[rt]))
    # Creating the table
    print("overall_rt_mean", overall_rt_mean)
    all_rts = overall_rt_mean.keys()
    men_row = ["Men"]
    women_row = ["Women"]
    mean_row = ["Mean"]
    for rt in all_rts:
        if rt in men_rt_mean:
            men_row.append(int(men_rt_mean[rt] * 1000))
        else:
            men_row.append("None")
    for rt in all_rts:
        if rt in women_rt_mean:
            women_row.append(int(women_rt_mean[rt] * 1000))
        else:
            women_row.append("None")
    mean_row += (map(lambda x: int(x * 1000), list(overall_rt_mean.values())))
    table_data = [men_row, women_row, mean_row]
    cols = [{'header': "Participants"}]

    for rt in all_rts:
        if float(rt) <= 0:
            cols.append({'header': "Free Time"})
        else:
            cols.append({'header': str(int(float(rt) * 1000)) + " msec"})
    merge_format = wb.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter'})
    end_index = (start_index[0] + 3, start_index[1] + len(all_rts))
    print("cols", cols)
    print("table data", table_data)
    print(end_index)
    ws.merge_range(start_index[0], start_index[1], start_index[0], end_index[1], "Mean Reaction Time (Milliseconds)",
                   merge_format)
    ws.merge_range(start_index[0] + 1, start_index[1], start_index[0] + 1, end_index[1],
                   "As a Function of Display Time and Gender", merge_format)
    ws.add_table(start_index[0] + 2, start_index[1], end_index[0] + 2, end_index[1],
                 {"data": table_data, 'columns': cols, 'style': 'Table Style Light 9'})
    return (end_index[0] + 2, start_index[1])


def createPrecentTable(data, wb, ws, start_index, name, log=lambda x: print(x)):
    pleasant = ["Pleasant"]
    unpleasant = ["Unpleasant"]
    neutral = ["Neutral"]
    cols = [{'header': "Valence"}]
    for rt in data:
        if float(rt) <= 0:
            cols.append({'header': "Free Time"})
        else:
            cols.append({'header': str(int(float(rt) * 1000)) + " msec"})
        pleasant.append(data[rt]["Pleasant"])
        unpleasant.append(data[rt]["Unpleasant"])
        neutral.append(data[rt]["Neutral"])
    table_data = [unpleasant, pleasant, neutral]
    merge_format = wb.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter'})
    end_index = (start_index[0] + 3, start_index[1] + len(data))
    print("end", end_index)
    print("cols", cols)
    print("table data", table_data)
    print(end_index)
    ws.merge_range(start_index[0], start_index[1], start_index[0], end_index[1], name,
                   merge_format)
    ws.add_table(start_index[0] + 1, start_index[1], end_index[0] + 1, end_index[1],
                 {"data": table_data, 'columns': cols, 'style': 'Table Style Light 9'})
    return (end_index[0] + 1, start_index[1])


def IAPSPrecent(tasks, wb, ws, start_index, log=lambda x: print(x)):
    men = []
    women = []
    all_ids = []
    for task in tasks:
        if task["gender"] == "male":
            men.append(task["id"])
        else:
            women.append(task["id"])
        all_ids.append(task["id"])
    men_precent = influx.getPrecentByDT(men)
    women_precent = influx.getPrecentByDT(women)
    overall_precent = influx.getPrecentByDT(all_ids)
    # Creating the table
    if men_precent:
        name = "Percentage of Responses: Men"
        last_index = createPrecentTable(men_precent, wb, ws, start_index, name, log=lambda x: print(x))
        start_index = (start_index[0] + 6, start_index[1])
    if women_precent:
        name = "Percentage of Responses: Women"
        last_index = createPrecentTable(women_precent, wb, ws, start_index, name, log=lambda x: print(x))
        start_index = (start_index[0] + 6, start_index[1])
    if overall_precent:
        name = "Percentage of Responses: Men + Women"
        last_index = createPrecentTable(overall_precent, wb, ws, start_index, name, log=lambda x: print(x))
    return last_index


def IAPSCategories(tasks, wb, ws, start_index, log=lambda x: print(x)):
    tasks_id = []
    for t in tasks:
        tasks_id.append(t["id"])
    categories = influx.getClicksByCategory(tasks_id)
    print(categories)
    if categories:
        keys = next(iter(categories.values())).keys()
    else:
        return
    cols = [{'header': "Category"}, {'header': "No. of Pictures"}, {'header': "RT"}, {'header': "Unpleasant"},
            {'header': "Pleasant"}, {'header': "Neutral"}]

    table_data = []
    for cat in categories:
        table_data.append([cat] + list(categories[cat].values()))
    merge_format = wb.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter'})
    end_index = (start_index[0] + len(categories), start_index[1] + len(keys))
    print(end_index)
    print(cols)
    print(table_data)
    ws.merge_range(start_index[0], start_index[1], start_index[0], end_index[1], "Categories",
                   merge_format)
    ws.add_table(start_index[0] + 1, start_index[1], end_index[0] + 1, end_index[1],
                 {"data": table_data, 'columns': cols, 'style': 'Table Style Light 9'})
    return (end_index[0] + 1, start_index[1])


def exportGeneralIAPSAnalysis(tasks, dir_path, log=lambda x: print(x)):
    wb = xlsxwriter.Workbook(dir_path + "/" + "General" + ".xlsx")
    ws = wb.add_worksheet("Test")
    next_index = IAPSMeanRT(tasks, wb, ws, (1, 1))
    next_index = IAPSPrecent(tasks, wb, ws, (next_index[0] + 2, next_index[1]))
    IAPSCategories(tasks, wb, ws, (next_index[0] + 2, next_index[1]))
    wb.close()


def exportIAPSTaskAnalysis(task, dir_path, log):
    start_index = (1, 1)
    wb = xlsxwriter.Workbook(dir_path + "/" + task["name"] + ".xlsx")
    ws = wb.add_worksheet("All Pictures")
    pics = influx.getAllPictures(task["id"])
    table_data = []
    for pic in pics:
        if pic["display_time"] == 0:
            pic["display_time"] = "Free Time"
        table_data.append(list(pic.values()))
    cols = [{'header': "Time"}, {'header': "Image"}, {'header': "Category"}, {'header': "Display Time"},
            {'header': "Reaction Time"},
            {'header': "Response"}]
    merge_format = wb.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter'})
    end_index = (start_index[0] + len(pics), start_index[1] + len(cols) - 1)
    ws.merge_range(start_index[0], start_index[1], start_index[0], end_index[1], "Pictures and Responses",
                   merge_format)
    ws.add_table(start_index[0] + 1, start_index[1], end_index[0] + 1, end_index[1],
                 {"data": table_data, 'columns': cols, 'style': 'Table Style Light 9'})

    waves = ["alpha", "betaH", "betaL", "gamma", "theta"]
    sensors = influx.getTaskSensors(str(task["id"]))
    print("sensors", sensors)
    start_index = (end_index[0] + 2, start_index[1])
    data_pleasant = influx.getPicturesTimes(str(task["id"]), "response='Pleasant'")
    end_index = createTable("Pleasant", wb, ws, start_index, waves, sensors, data_pleasant)
    start_index = (end_index[0] + 2, start_index[1])
    data_neutral = influx.getPicturesTimes(str(task["id"]), "response='Neutral'")
    end_index = createTable("Neutral", wb, ws, start_index, waves, sensors, data_neutral)
    start_index = (end_index[0] + 2, start_index[1])
    data_unpleasant = influx.getPicturesTimes(str(task["id"]), "response='Unpleasant'")
    createTable("Unpleasant", wb, ws, start_index, waves, sensors, data_unpleasant)
    wb.close()


def exportIAPS(tasks, dir_path, log=lambda x: print(x)):
    try:
        log("Starting to export...")
        import os
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        for task in tasks:
            task["id"] = "task" + task["id"]
        log("   Starting general analysis...")
        exportGeneralIAPSAnalysis(tasks, dir_path, log)
        log("   Done!")
        log("   Starting single task analysis...")
        for idx, task in enumerate(tasks):
            log("       Analysing task  " + str(idx + 1) + "/" + str(len(tasks)) + "...")
            exportIAPSTaskAnalysis(task, dir_path, log)
            log("       Done!")
        log("Export done successfully!")
    except Exception as e:
        log("ERROR! - " + str(e))


if __name__ == '__main__':
    influx.start_influx()
    tasks = [
        {"name": "t53", "id": "task53", "gender": "male"}, {"name": "t54", "id": "task53", "gender": "female"}
    ]
    exportGeneralIAPSAnalysis(tasks, ".")
    influx.close_influx()
