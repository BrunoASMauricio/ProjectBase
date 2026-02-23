import threading
import logging

from data.colors import ColorFormat, Colors
from enum import IntEnum

class LogLevels(IntEnum):
    DEBUG   = 1
    INFO    = 2
    NOTICE  = 3
    WARN    = 4
    ERR     = 5

log_dict = {
    LogLevels.DEBUG:  logging.DEBUG,
    LogLevels.INFO:   logging.INFO,
    LogLevels.NOTICE: logging.INFO,
    LogLevels.WARN:   logging.WARN,
    LogLevels.ERR:    logging.ERROR,
}

cur_log_level = LogLevels.WARN
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
def FlushthreadLog():
    global thread_log
    global thread_log_lock
    with thread_log_lock:
        if len(thread_log) > 0:
            print(thread_log,end="")
        thread_log = ""

def SetLogLevel(level):
    global cur_log_level
    cur_log_level = level

"""
Base print which decides if direct print is ok, or it buffered is necessary
"""
def __Print(message, end, log_level):
    global cur_log_level
    if IsSystemMultiThreading():
        AddTothreadLog(message + end)
    else:
        # INFO is always printed, it is the de facto comms with the user
        # DEBUG isnt shown to the user in the terminal so as to not polutte it
        if log_level >= cur_log_level or log_level == LogLevels.INFO and log_level != LogLevels.DEBUG:
            print(message, end=end)

def PrintError(message, end="\n"):
    message = ColorFormat(Colors.Red, f"[ERROR] {message}")
    __Print(message, end, LogLevels.ERR)
    logging.error(message + end)

def PrintWarning(message, end="\n"):
    message = ColorFormat(Colors.Magenta, f"[WARN] {message}")
    __Print(message, end, LogLevels.WARN)
    logging.warning(message + end)

def PrintNotice(message, end="\n"):
    message = ColorFormat(Colors.Blue, f"[NOTICE] {message}")
    __Print(message, end, LogLevels.NOTICE)
    logging.info(message + end)

def PrintInfo(message, end="\n"):
    message = ColorFormat(Colors.Green, f"{message}")
    __Print(message, end, LogLevels.INFO)
    logging.info(message + end)

def Print(message, end="\n"):
    PrintInfo(message, end)

def PrintDebug(message, end="\n"):
    message = f"[DEBUG] {message}"
    __Print(message, end, LogLevels.DEBUG)
    logging.debug(message + end)