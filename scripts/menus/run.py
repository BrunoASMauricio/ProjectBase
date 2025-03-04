from menus.menu import Menu
from processes.run_exec import run_single_test, run_single_executable, run_all_tests, run_all_tests_on_valgrind

RunMenu = Menu("Run Menu")

RunMenu.AddCallbackEntry("Run project executable", run_single_executable)
RunMenu.AddCallbackEntry("Run single test", run_single_test)
RunMenu.AddCallbackEntry("Run all tests", run_all_tests)
RunMenu.AddCallbackEntry("Run all tests (with valgrind)", run_all_tests_on_valgrind)
