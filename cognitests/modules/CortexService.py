import os
import platform
import subprocess

system32 = os.path.join(os.environ['SystemRoot'], 'SysNative' if
platform.architecture()[0] == '32bit' else 'System32')
sc = os.path.join(system32, 'sc.exe')
net = os.path.join(system32, 'net.exe')
path = os.path.dirname(os.path.realpath(__file__))


# def startCortex():
#     try:
#         cortex = os.path.abspath(path + "/../../EmotivCortexService/CortexService.exe")
#         print('binPath="{}"'.format(cortex).replace("\\", "\\\\"))
#         subprocess.call([sc, 'CREATE', 'CortexService2', 'binPath="{}"'.format(cortex).replace("\\", "\\\\")],
#                         shell=False)
#         subprocess.call([sc, 'START', 'CortexService2'], shell=False)
#     except Exception as e:
#         print("[startCortex] " + e)


# def stopCortex():
#     try:
#         # subprocess.call(["EmotivCortexService\\cortex_remove_script.bat"], shell=False)
#         subprocess.call([sc, 'STOP', 'CortexService2'], shell=False)
#         subprocess.call([sc, 'DELETE', 'CortexService2'], shell=False)
#     except Exception as e:
#         print(e)

def startCortex():
    subprocess.call([sc, 'START', 'EmotivCortexServiceV2'], shell=False)


def stopCortex():
    subprocess.call([sc, 'STOP', 'EmotivCortexServiceV2'], shell=False)
