import sys
import logging
import datetime
import traceback
from data.settings import Settings
from processes.project import Project, UserChooseProject
from data.common import ValueNotEmpty

if __name__ != "__main__":
    Abort("This script is not meant to be imported, please run directly")

# Configure logging
# logging.basicConfig(stream = sys.stdout, level = logging.DEBUG)
logging.basicConfig(filename="/tmp/project_base.log",
                    filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S', level = logging.DEBUG)

# logging.basicConfig(stream = sys.stdout, level = logging.INFO)

logging.info("\n\n\n=============== PROJECTBASE start ===============")
logging.info("=============== at " + str(datetime.datetime.now()) + " ===============")
Settings.init()
if False == ValueNotEmpty(Settings, "url"):
    Settings["url"] = UserChooseProject()

Settings.start()
Project.init()

# Include here so paths are already ready in settings (find better way)
from menus.main import MainMenu

Settings.load_persistent_settings()

MainMenu.handle_input()

sys.exit(0)