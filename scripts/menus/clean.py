from menus.menu import Menu
from processes.project import CleanRunnables, CleanCompiled, CleanAll
from processes.run_linter import CleanLinterFiles

CleanMenu = Menu("Clean Menu")

CleanMenu.add_callback_entry("Clean all (all bellow + CMake cache)", CleanAll)
CleanMenu.add_callback_entry("Clean objects (libraries), executables and tests", CleanCompiled)
CleanMenu.add_callback_entry("Clean executables and tests", CleanRunnables)
CleanMenu.add_callback_entry("Clean linter files", CleanLinterFiles)
