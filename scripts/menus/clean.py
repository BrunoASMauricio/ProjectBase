from menus.menu import Menu
from processes.project import CleanRunnables, CleanCompiled, CleanAll, CleanCMake
from processes.run_linter import CleanLinterFiles

CleanMenu = Menu("Clean Menu")

CleanMenu.AddCallbackEntry("Reset build", CleanCMake, "All below plus cleans build system. REQUIRES ANOTHER LOAD")
CleanMenu.AddCallbackEntry("Clean all", CleanAll, "All below plus cleans build artifacts")
CleanMenu.AddCallbackEntry("Clean objects", CleanCompiled, "Clean objects like libraries, executables and tests")
CleanMenu.AddCallbackEntry("Clean executables and tests", CleanRunnables, "Clean just the executables and tests")
CleanMenu.AddCallbackEntry("Clean linter files", CleanLinterFiles, "Clear linter files")
