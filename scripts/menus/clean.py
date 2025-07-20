from menus.menu import Menu
from processes.project import CleanRunnables, CleanCompiled, CleanAll
from processes.run_linter import CleanLinterFiles

CleanMenu = Menu("Clean Menu")

CleanMenu.AddCallbackEntry("Clean all (all bellow + CMake cache)", CleanAll)
CleanMenu.AddCallbackEntry("Clean objects (libraries), executables and tests", CleanCompiled)
CleanMenu.AddCallbackEntry("Clean executables and tests", CleanRunnables)
CleanMenu.AddCallbackEntry("Clean linter files", CleanLinterFiles)
