from menus.menu import Menu
from processes.run_exec import RunSingleTest, RunSingleExecutable, RunAllTests, RunAllTestsWithValgrind, RunModuleTests
from processes.run_exec import GetTestCompletions, GetExecutableCompletions

RunMenu = Menu("Run Menu")

RunMenu.AddCallbackEntry("Run project executable", RunSingleExecutable, "Run single executable", completions=GetExecutableCompletions)
RunMenu.AddCallbackEntry("Run single test", RunSingleTest, "Run single test", completions=GetTestCompletions)
RunMenu.AddCallbackEntry("Run module tests", RunModuleTests, "Select a module and run all of its tests")
RunMenu.AddCallbackEntry("Run all tests", RunAllTests, "Run all tests")
RunMenu.AddCallbackEntry("Run all tests (with valgrind)", RunAllTestsWithValgrind, "Run all tests with valgrind")
