from menus.menu import Menu
from processes.run_exec import RunSingleTest, RunSingleExecutable, RunAllTests, RunAllTestsWithValgrind

RunMenu = Menu("Run Menu")

RunMenu.AddCallbackEntry("Run project executable", RunSingleExecutable, "Run single executable")
RunMenu.AddCallbackEntry("Run single test", RunSingleTest, "Run single test")
RunMenu.AddCallbackEntry("Run all tests", RunAllTests, "Run all tests")
RunMenu.AddCallbackEntry("Run all tests (with valgrind)", RunAllTestsWithValgrind, "Run all tests with valgrind")
