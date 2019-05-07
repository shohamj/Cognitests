import cognitests.modules.cortex_client.cortex_context as headsets
import cognitests.modules.cortex_client.cortex_context_fake as test

test_mode_on = False


def get_test_mode():
    global test_mode_on
    return test_mode_on


def set_test_mode(state: bool):
    global test_mode_on
    test_mode_on = state


def set_send(stream, func):
    global test_mode_on
    if test_mode_on:
        return test.set_send(stream, func)
    else:
        return headsets.set_send(stream, func)


def subscribe(stream: str, headset_id: str = None):
    global test_mode_on
    if test_mode_on:
        return test.subscribe(stream, headset_id)
    else:
        return headsets.subscribe(stream, headset_id)


def get_last_headset():
    global test_mode_on
    if test_mode_on:
        return test.get_last_headset()
    else:
        return headsets.get_last_headset()


def queryHeadsets(headset_id: str = None):
    global test_mode_on
    if test_mode_on:
        return test.queryHeadsets(headset_id)
    else:
        return headsets.queryHeadsets(headset_id)
