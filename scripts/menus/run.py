from menus.menu import Menu
from processes.run_exec import RunSingleTest, RunSingleExecutable, RunAllTests, RunAllTestsWithValgrind

RunMenu = Menu("Run Menu")

RunMenu.AddCallbackEntry("Run project executable", RunSingleExecutable)
RunMenu.AddCallbackEntry("Run single test", RunSingleTest)
RunMenu.AddCallbackEntry("Run all tests", RunAllTests)
RunMenu.AddCallbackEntry("Run all tests (with valgrind)", RunAllTestsWithValgrind)
