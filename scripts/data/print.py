import threading
import logging

from data.colors import ColorFormat, Colors

thread_log = ""
thread_log_lock = threading.Lock()
is_threading = False

def GetThreadId():
    return threading.get_ident()


"""
Check if the system is currently multi threading
"""
def IsSystemMultiThreading():
    global is_threading
    return is_threading

"""
Toggle if threading is on or off
"""
def ToggleThreading(on):
    global is_threading
    is_threading = on

"""
Add message to buffered log
"""
def AddTothreadLog(message):
    global thread_log
    global thread_log_lock

    with thread_log_lock:
        thread_log += f"({GetThreadId()}) {message}\n"

"""
Clear buffered logs
"""
def ClearThreadLog():
    global thread_log
    global thread_log_lock
    with thread_log_lock:
        thread_log = ""

"""
Print buffered logs (clearing them afterwards)
"""
def Flushthread_log():
    global thread_log
    global thread_log_lock
    with thread_log_lock:
        if len(thread_log) > 0:
            print(thread_log,end="")
        thread_log = ""

"""
Base print which decides if direct print is ok, or it buffered is necessary
"""
def __Print(message, end):
    if IsSystemMultiThreading():
        AddTothreadLog(message + end)
    else:
        print(message, end=end)

def PrintError(message, end="\n"):
    message = ColorFormat(Colors.Red, f"[ERROR] {message}")
    __Print(message, end)
    logging.error(message + end)

def PrintWarning(message, end="\n"):
    message = ColorFormat(Colors.Magenta, f"[WARN] {message}")
    __Print(message, end)
    logging.warning(message + end)


def PrintNotice(message, end="\n"):
    message = ColorFormat(Colors.Blue, f"[NOTICE] {message}")
    __Print(message, end)
    logging.info(message + end)

def PrintInfo(message, end="\n"):
    message = ColorFormat(Colors.Green, f"{message}")
    __Print(message, end)
    logging.info(message + end)

def Print(message, end="\n"):
    PrintInfo(message, end)

def PrintDebug(message, end="\n"):
    message = f"[DEBUG] {message}"
    __Print(message, end)
    logging.debug(message + end)