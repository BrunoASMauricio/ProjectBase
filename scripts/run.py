#!/bin/python3

import sys
import logging

from data.common import Abort, GetNow
from data.settings import Settings
from processes.project import Project, UserChooseProject
from data.common import ValueNotEmpty

if __name__ != "__main__":
    Abort("This script is not meant to be imported, please run directly")

# Configure logging
logging.basicConfig(filename="/tmp/project_base.log",
                    filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S', level = logging.DEBUG)

logging.info("\n\n\n=============== PROJECTBASE start ===============")
logging.info("=============== at " + GetNow() + " ===============")

Settings.init()
if False == ValueNotEmpty(Settings, "url"):
    Settings["url"] = UserChooseProject()

Settings.start()
Project.init()

# Include here so paths are already ready in settings
from menus.main import MainMenu

Settings.load_persistent_settings()

MainMenu.handle_input()

sys.exit(0)