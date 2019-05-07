from enum import Enum


class Methods(Enum):
    """
    Represent possible method types described : https://emotiv.github.io/cortex-docs/#methods
    """
    LOGIN = "login"
    GET_USER_LOGIN = "getUserLogin"
    LOGOUT = "logout"
    AUTHORIZE = "authorize"
    ACCEPT_LICENSE = "acceptLicense"
    GET_LICENSE_INFO = "getLicenseInfo"
    QUERY_HEADSETS = "queryHeadsets"
    CONTROL_BLUETOOTH_HEADSET = "controlBluetoothHeadset"
    CREATE_SESSION = "createSession"
    UPDATE_SESSION = "updateSession"
    QUERY_SESSIONS = "querySessions"
    UPDATE_NOTE = "updateNote"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    INJECT_MARKER = "injectMarker"
    GET_DETECTION_INFO = "getDetectionInfo"
    TRAINING = "training"
    GET_TRAINING_TIME = "getTrainingTime"
    GET_TRAINED_SIGNATURE_ACTIONS = "getTrainedSignatureActions"
    MENTAL_COMMAND_GET_SKILL_RATING = "mentalCommandGetSkillRating"
    MENTAL_COMMAND_ACTION_SENSITIVITY = "mentalCommandActionSensitivity"
    MENTAL_COMMAND_ACTION_LEVEL = "mentalCommandActionLevel"
    MENTAL_COMMAND_ACTIVE_ACTION = "mentalCommandActiveAction"
    FACIAL_EXPRESSION_SIGNATURE_TYPE = "facialExpressionSignatureType"
    FACIAL_EXPRESSION_THRESHOLD = "facialExpressionThreshold"
    MENTAL_COMMAND_TRAINING_THRESHOLD = "mentalCommandTrainingThreshold"
    MENTAL_COMMAND_BRAIN_MAP = "mentalCommandBrainMap"
    QUERY_PROFILE = "queryProfile"
    SETUP_PROFILE = "setupProfile"
    GET_CURRENT_PROFILE = "getCurrentProfile"
    DECRYPT_DATA = "decryptData"
    CONFIG_MAPPING = "configMapping"

    def __str__(self):
        return str(self.value)


class Streams(Enum):
    """
    Represent possible stream types described : https://emotiv.github.io/cortex-docs/#subscriptions
    """
    MOD = "mod"
    EEG = "eeg"
    COM = "com"
    FAC = "fac"
    MET = "met"
    DEV = "dev"
    POW = "pow"
    SYS = "sys"
# lines = text.split('\n')
# for line in lines:
#     l = ""
#     for letter in line:
#         if letter.islower():
#             l += letter.upper()
#         else:
#             l += "_" + letter
#     print(l + ' = "' + line + '"' )
