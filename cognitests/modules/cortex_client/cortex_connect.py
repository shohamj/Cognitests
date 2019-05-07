import ssl
import threading

import websocket

from cognitests.modules.cortex_client.config import URL


def connect():
    ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
    ws.connect(URL)
    return ws


def connect_long(on_message=None, on_error=None, on_close=None, on_open=None):
    ws = websocket.WebSocketApp(URL,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close,
                                on_open=on_open)
    # ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    t = threading.Thread(target=ws.run_forever, kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE}})
    t.setDaemon(True)
    t.start()
    return ws


if __name__ == '__main__':
    ws = connect_long(on_open=print, on_message=print)
    threading.Event().wait(1)
    ws.send("gggg")
    threading.Event().wait()
