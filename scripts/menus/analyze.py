from menus.menu import Menu
from processes.run_linter import RunLinter, RunFormat
from processes.versioning import GetDiff, GetFilesDiff
AnalysisMenu = Menu("Analysis Menu")

AnalysisMenu.AddCallbackEntry("Get files diff", GetFilesDiff)
AnalysisMenu.AddCallbackEntry("Get content diff", GetDiff)
AnalysisMenu.AddCallbackEntry("Runs clang-tidy linter in all project files", RunLinter)
AnalysisMenu.AddCallbackEntry("Runs clang-format in all project files creating tmp files when they exist format unconformities", RunFormat)
