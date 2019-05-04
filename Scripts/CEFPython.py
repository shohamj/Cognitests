"""
Set initial window size to 900/640px without use of
any third party GUI framework. On Linux/Mac you can set
window size by calling WindowInfo.SetAsChild. On Windows
you can accomplish this by calling Windows native functions
using the ctypes module.
"""

import ctypes
import os
import threading
import urllib.request
import win32api
import win32gui

import win32con
from cefpython3 import cefpython as cef

BROWSER = None


def startWindow(url, title, icon="resources/chromium.ico"):
    global BROWSER
    try:
        cef.Initialize()
        window_info = cef.WindowInfo()
        BROWSER = cef.CreateBrowserSync(url=url,
                                        window_info=window_info,
                                        window_title=title,
                                        settings={"file_access_from_file_urls_allowed": True})
        window_handle = BROWSER.GetOuterWindowHandle()
        print(BROWSER.IsWindowRenderingDisabled())
        setWindowIcon(window_handle, icon)
        ctypes.windll.user32.ShowWindow(window_handle, 3)

        cef.MessageLoop()
        del BROWSER
        cef.Shutdown()
        onExit(url)
    except Exception as e:
        print("CEF startWindow exception:", e)


def toggleFullscreen(state):
    global BROWSER
    try:
        if BROWSER:
            if BROWSER.IsFullscreen() != state:
                BROWSER.ToggleFullscreen()
    except Exception as e:
        print("CEF toggleFullscreen exception:", e)


def setWindowIcon(window_handle, icon):
    global BROWSER
    # Window icon
    icon = os.path.abspath(icon)
    if not os.path.isfile(icon):
        icon = None
    if icon:
        # Load small and big icon.
        # WNDCLASSEX (along with hIconSm) is not supported by pywin32,
        # we need to use WM_SETICON message after window creation.
        # Ref:
        # 1. http://stackoverflow.com/questions/2234988
        # 2. http://blog.barthe.ph/2009/07/17/wmseticon/
        bigx = win32api.GetSystemMetrics(win32con.SM_CXICON)
        bigy = win32api.GetSystemMetrics(win32con.SM_CYICON)
        big_icon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON,
                                      bigx, bigy,
                                      win32con.LR_LOADFROMFILE)
        smallx = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        smally = win32api.GetSystemMetrics(win32con.SM_CYSMICON)
        small_icon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON,
                                        smallx, smally,
                                        win32con.LR_LOADFROMFILE)
        win32api.SendMessage(window_handle, win32con.WM_SETICON,
                             win32con.ICON_BIG, big_icon)
        win32api.SendMessage(window_handle, win32con.WM_SETICON,
                             win32con.ICON_SMALL, small_icon)
        cef.WindowUtils.SetIcon(BROWSER, icon="inherit")


def onExit(url):
    try:
        urllib.request.urlopen(url + '/_shutdown')
    except:
        print("Can't call '/_shutdown'")


def keept(bool):
    while True:
        toggleFullscreen(bool)
        bool = not bool
        threading.Event().wait(timeout=0.5)


if __name__ == '__main__':
    t1 = threading.Thread(target=keept, args=(True,))
    t1.setDaemon(True)
    # t1.start()
    a = "https://www.google.com/"
    b = "https://www.babylonjs-playground.com/"
    c = "https://css-tricks.com/examples/DragAndDropFileUploading/"
    d = "https://www.jqueryscript.net/demo/Drag-And-Drop-File-Uploader-With-Preview-Imageuploadify/"
    startWindow(c, "Babylon")
