import json


class Request(object):

    def __init__(self, method: str, id: int = 1, jsonrpc: str = "2.0", params: dict = {}):
        self.id = id
        self.jsonrpc = jsonrpc
        self.method = method
        self.params = params

    def to_string(self):
        return json.dumps(vars(self))


class Response(object):

    def __init__(self, id: int, result=None, error=None, jsonrpc: str = "2.0"):
        self.id = id
        self.jsonrpc = jsonrpc
        self.result = result
        self.error = error

    def to_string(self, pretty=False):
        return json.dumps(vars(self)) if not pretty else json.dumps(vars(self), indent=4)

    @classmethod
    def of_json(self, resp: dict):
        return Response(**json.loads(resp))


class SubscriptionData(object):

    def __init__(self, event: str, data: list):
        self.event = event
        self.data = data

    def to_string(self, pretty=False):
        return json.dumps(vars(self)) if not pretty else json.dumps(vars(self), indent=4)

    @classmethod
    def of_json(self, resp: dict):
        resp = json.loads(resp)
        if resp:
            return SubscriptionData(list(resp.keys())[0], list(resp.values())[0])
