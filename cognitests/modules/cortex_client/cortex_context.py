import json
import threading

from cognitests.modules.cortex_client.config import *
from cognitests.modules.cortex_client.constants import Methods
from cognitests.modules.cortex_client.cortex_connect import connect
from cognitests.modules.cortex_client.dto import Request, Response, SubscriptionData
from cognitests.modules.cortex_client.helpers import list_flattenner

# GLOBALS
SEND_FUNCTIONS = {}
LAST_HEADSET = None


def queryHeadsets(headset_id: str = None):
    import time
    t = time.time()
    try:
        ws = connect()
        print("Connection time:", time.time() - t)

        method = Methods.QUERY_HEADSETS.value
        params = {}
        if headset_id:
            params["headsetId"] = headset_id
        req = Request(method=method, params=params)
        t = time.time()
        ws.send(req.to_string())
        res = Response.of_json(ws.recv())
        print("Query time:", time.time() - t)
        ws.close()
        return res.result
    except Exception as e:
        print("Error - queryHeadsets:", e)
        print(time.time() - t)
        return json.loads("[]")

def authorize(ws):
    try:
        method = Methods.AUTHORIZE.value
        params = {}
        if CLIENT_ID:
            params["client_id"] = CLIENT_ID
        if CLIENT_SECRET:
            params["client_secret"] = CLIENT_SECRET
        if LICENSE:
            params["license"] = LICENSE
        req = Request(method=method, params=params)
        ws.send(req.to_string())
        res = Response.of_json(ws.recv())
        if res.result and "_auth" in res.result:
            return res.result["_auth"]
        return res.error
    except Exception as e:
        print("Error - authorize:", e)
        return "Error - authorize:" + str(e)


def create_session(ws, auth, headset_id=None):
    try:
        method = Methods.CREATE_SESSION.value
        params = {
            "status": "open",
            "_auth": auth
        }
        if headset_id:
            params["headset"] = headset_id
        if CLIENT_ID:
            params["client_id"] = CLIENT_ID
        if CLIENT_SECRET:
            params["client_secret"] = CLIENT_SECRET
        if LICENSE:
            params["license"] = LICENSE
        req = Request(method=method, params=params)
        ws.send(req.to_string())
        res = Response.of_json(ws.recv())
        if res.result and "id" in res.result:
            return res.result["id"]
        return res.error
    except Exception as e:
        print("Error - create_session:", e)
        return "Error - create_session:" + str(e)


def subscribe(stream: str, headset_id: str = None):
    global LAST_HEADSET
    if headset_id:
        LAST_HEADSET = headset_id
    else:
        LAST_HEADSET = queryHeadsets()[0]["id"]
    ws = connect()
    auth = authorize(ws)
    session = create_session(ws, auth, headset_id)
    try:
        method = Methods.SUBSCRIBE.value
        params = {
            "status": "open",
            "_auth": auth,
            "session": session,
            "streams": [stream]
        }
        req = Request(method=method, params=params)
        ws.send(req.to_string())
        res = Response.of_json(ws.recv())
        cols = list(res.result[0].values())[0]["cols"]
        cols = list_flattenner(cols)
        return list_to_stream(ws, cols)
    except Exception as e:
        print("Error - subscribe:", e)


def list_to_stream(ws, cols):
    stop_event = threading.Event()
    t = threading.Thread(target=subscribe_listener, args=(ws, cols, stop_event))
    t.setDaemon(True)
    t.start()
    return stop_event


def subscribe_listener(ws, cols, stop_event):
    while not stop_event.is_set():
        res = SubscriptionData.of_json(ws.recv())
        data = dict(zip(cols, list_flattenner(res.data)))
        if res.event in SEND_FUNCTIONS:
            SEND_FUNCTIONS[res.event](data)
    ws.close()


def set_send(stream, func):
    global SEND_FUNCTIONS
    SEND_FUNCTIONS[stream] = func


def get_last_headset():
    return LAST_HEADSET


if __name__ == '__main__':
    print("Start test")
    import time

    ws = connect()
    t1 = time.time()
    auth = authorize(ws)
    print(auth)
    print("authorize time", time.time() - t1)
    while True:
        print("************************************")
        queryHeadsets()
