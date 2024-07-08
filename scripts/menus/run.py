from menus.menu import Menu
from processes.run_exec import run_single_test, run_single_executable, run_all_tests

RunMenu = Menu("Run Menu")

RunMenu.add_callback_entry("Run project executable", run_single_executable)
RunMenu.add_callback_entry("Run all tests", run_all_tests)
RunMenu.add_callback_entry("Run single test", run_single_test)
