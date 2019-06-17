import threading

# GLOBALS
SEND_FUNCTIONS = {}
LAST_HEADSET = None
epoc = ['AF3', 'AF4', 'F7', 'F3', 'F4', 'F8', 'FC5', 'FC6', 'T7', 'T8', 'P7', 'P8', 'O1', 'O2']
insight = ["AF3", "AF4", "T7", "T8", "Pz"]
waves = ["alpha", "betaH", "betaL", "gamma", "theta"]


def queryHeadsets(headset_id: str = None):
    if headset_id == "insight-Test_Mode":
        return [{"id": "insight-Test_Mode", "sensors": insight}]
    if headset_id == "epocplus-Test_Mode":
        return [{"id": "epocplus-Test_Mode", "sensors": epoc}]
    if not headset_id:
        return [{"id": "insight-Test_Mode", "sensors": insight},
                {"id": "epocplus-Test_Mode", "sensors": epoc}]


def subscribe(stream: str, headset_id: str = None):
    global LAST_HEADSET
    if headset_id:
        LAST_HEADSET = headset_id
    else:
        LAST_HEADSET = queryHeadsets()[0]["id"]
    stop_event = threading.Event()
    t = threading.Thread(target=subscribe_listener, args=(stream, headset_id, stop_event))
    t.setDaemon(True)
    t.start()
    return stop_event


def subscribe_listener(stream, headset_id, stop_event):
    import random
    if headset_id == "epocplus-Test_Mode":
        sensors = epoc
    else:
        sensors = insight
    data = {}
    while not stop_event.is_set():
        if stream == "dev":
            data = {"Battery": 4, "Signal": 2}
            for s in sensors:
                data[s] = 4.0
        if stream == "pow":
            for s in sensors:
                for w in waves:
                    sensor_wave = s + "/" + w
                    if sensor_wave in data:
                        if random.random() > 0.5 and data[sensor_wave] <= 3 or data[sensor_wave] <= 0.2:
                            data[sensor_wave] += random.normalvariate(0.1, 0.05)
                        else:
                            data[sensor_wave] -= random.normalvariate(0.1, 0.05)
                    else:
                        data[sensor_wave] = random.normalvariate(1.5, 0.5)

        if stream == "fac":
            data = {"eyeAct": "lookD", "uAct": "surprise", "uPow": 0.0, "lAct": "neutral", "lPow": 0.0446911528706551}
        if stream in SEND_FUNCTIONS:
            SEND_FUNCTIONS[stream](data)
        threading.Event().wait(0.1)


def set_send(stream, func):
    global SEND_FUNCTIONS
    SEND_FUNCTIONS[stream] = func


def get_last_headset():
    return LAST_HEADSET


if __name__ == '__main__':
    e1 = subscribe("pow", "epocplus-Test_Mode")
    set_send("pow", print)
    threading.Event().wait()
    print(e1)
