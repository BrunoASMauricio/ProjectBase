#!/bin/python3

import os
import sys
import logging

from data.common import Abort, GetNow, ValueNotEmpty, Formatter
from data.settings import Settings
from processes.project import Project, UserChooseProject
from data.paths import GetBasePaths
from processes.filesystem import CreateDirs
from data.print import *

if __name__ != "__main__":
    Abort("This script is not meant to be imported, please run directly")

Settings.init()

# Configure output
if len(Settings["out_file"]) == 0:
    out = sys.stdout
else:
    if os.path.isfile(Settings["out_file"]):
        out = open(Settings["out_file"], "a", encoding="utf-8")
    else:
        out = open(Settings["out_file"], "w", encoding="utf-8")

sys.stdout = out
sys.stderr = out

# TODO Set log level from command line
default_log_level = LogLevels.ERR

SetLogLevel(default_log_level)

# Configure logging
logging.basicConfig(filename=Settings["log_file"],
                    filemode='a', level = log_dict[default_log_level])
                    # filemode='a', level = logging.WARNING)

logging.info("\n\n\n=============== PROJECTBASE start ===============")
logging.info("=============== at " + GetNow() + " ===============")
logging.info("=============== at " + os.getcwd() + " ===============")

if Settings["debug"] == True:
    for handler in logging.getLogger().handlers:
        handler.setFormatter(Formatter)

if False == ValueNotEmpty(Settings, "url"):
    Settings["url"] = UserChooseProject()

Settings.start()

# Make sure all base paths exist before we start
CreateDirs(GetBasePaths().values())

Project.init()

# Include here so paths are already ready in settings
from menus.main import MainMenu

Settings.load_persistent_settings()

MainMenu.HandleInput()

# After exit, clean stdout and stderr just in case
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

sys.exit(0)