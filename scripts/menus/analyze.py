from menus.menu import Menu
from processes.run_linter import RunLinter, RunFormat

AnalysisMenu = Menu("Analysis Menu")

AnalysisMenu.add_callback_entry("Runs clang-tidy linter in all project files", RunLinter)
AnalysisMenu.add_callback_entry("Runs clang-format in all project files creating tmp files when they exist format unconformities", RunFormat)
