from menus.menu import Menu
from run_linter import runLinter

AnalysisMenu = Menu("Analysis Menu")

# TODO: make runLinter work
AnalysisMenu.add_callback_entry("Run linter", runLinter)
