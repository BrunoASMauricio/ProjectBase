import os
import sys
import time
import logging
from enum import Enum

from data.common import Formatter
from data.colors import ColorFormat, Colors
from data.common import ErrorCheckLogs, SlimError
from data.common import Assert, GetText, GetHost, GetTime
from processes.auto_completer import CustomCompleter
from data.settings import Settings
from data.common import RemoveNonAlfanumeric, ResetTerminal
from data.paths import JoinPaths

class EntryType(Enum):
    CALLBACK = 1
    MENU     = 2
    DYNAMIC  = 3

def GetNextOption(prompt = "[<] ", single_string = False):
    global ProjectArgs

    if len(Settings["action"]) != 0:
        # Next automated action
        next_input = Settings["action"][0]
        del Settings["action"][0]
        print("[< Auto " + prompt + " <] {" + next_input + "}")
    else:
        # Called with --exit and no command, just exit
        if Settings["exit"] == True:
            raise EOFError
        next_input = input(prompt)

        # No request to keep input as single string (non split)
        if not single_string:
            # Check if we received multiple commands
            SplitInput = next_input.split(" ")
            if len(SplitInput) > 1:
                Settings["action"] += SplitInput[1:]
                next_input = SplitInput[0]

    return next_input

def MenuExit(input):
    # If "exit" is entered, ProjectBase exits ()
    # if Settings["exit"] == True or input == "out":??
    if input == "out":
        return True
    if input == "exit":
        Settings["action"].append(input)
        return True
    return False

all_menu_names = []
class Menu():
    """
    If name is None, history completer isn't setup (previous menus' completer is used)
    If stay_in_menu is True, entry completion will reprint the menu, and
     not return to previous menu
    """
    def __init__(self, name=None, stay_in_menu=False):
        self.entries      = []
        self.prologue     = None
        self.epilogue     = None
        self.stay_in_menu = stay_in_menu
        self.history_file = None
        self.completer = None
        # Make sure menus don't have colliding names
        if name != None:
            name = RemoveNonAlfanumeric(name)
            Assert(name not in all_menu_names, "Repeated name " + name)
            self.history_file = JoinPaths(Settings["paths"]["history"], name)
            self.completer = CustomCompleter(self.history_file, [])
            all_menu_names.append(name)

    def AddCallbackEntry(self, entry, Callback):
        self.entries.append([entry, EntryType.CALLBACK, Callback])
    
    def AddSubmenuEntry(self, entry, menu):
        self.entries.append([entry, EntryType.MENU, menu])

    """
    A function will run during menu selection and return the entries to show
    These entries come in a list of lists like so:
    [["entry 0 name", entry_0_callback, args_for_callback], ...]
    The callback will be called first with args_for_callback as named arguments
    """
    def AddDynamicEntries(self, entry_generator, fallback=None):
        self.entries.append([entry_generator, EntryType.DYNAMIC, fallback])

    """
    Return string with menu data
    """
    def GetMenu(self, depth):
        index = 1
        menu = GetText(self.prologue)
        menu += ColorFormat(Colors.Yellow, f"({GetTime()})({GetHost()})\n")

        for entry in self.entries:
            if entry[1] == EntryType.DYNAMIC:
                # Remove previously generated entries
                if len(entry) == 4:
                    del entry[3]
                entries = entry[0]()
                if len(entries) == 0:
                    entry.append(GetText(entry[2]))
                else:
                    for new_entry in entries:
                        menu  += ("| " * depth) + str(index)+" ) " + new_entry[0] + "\n"
                        index += 1
                    # Store generated entries in dynamic entry
                entry.append(entries)
            else:
                if entry[1] == EntryType.MENU:
                    menu  += ("| " * depth) + str(index)+">) " + GetText(entry[0]) + "\n"
                elif entry[1] == EntryType.CALLBACK:
                    menu  += ("| " * depth) + str(index)+" ) " + GetText(entry[0]) + "\n"
                index += 1

        menu += GetText(self.epilogue)

        return menu
    """
    Activate the entry selected via its' index
    """
    def SelectEntry(self, index, depth):
        picked_index = index - 1
        picked_entry = None
        current_index = 0

        for saved_entry in self.entries:
            if saved_entry[1] == EntryType.DYNAMIC:
                # If the adjusted index belongs to the dynamic entry being evaluated
                if picked_index - current_index < len(saved_entry[3]):
                    picked_index = picked_index - current_index
                    picked_entry = saved_entry
                    break
                current_index += len(saved_entry[3])
            else:
                if current_index == picked_index:
                    picked_entry = saved_entry
                    break
                current_index += 1

        if picked_entry == None:
            print("Menu has " + str(current_index) + " entries, input " + str(index) + " is not valid")
            return

        if picked_entry[1] == EntryType.CALLBACK:
            picked_entry[2]()
        elif picked_entry[1] == EntryType.MENU:
            picked_entry[2].HandleInput(depth + 1)
            self.completer.setup()
        else:
            dynamic_entry = picked_entry[3][picked_index]
            dynamic_entry[1](**dynamic_entry[2])
    """
    Print menu and handle input from user
    """
    def HandleInput(self, depth = 0):
        if depth == 0:
            Formatter.setup()
        current_dir = os.getcwd()
        previous_command = None
        previous_invalid = False
        previous_time = None
        current_tries = 5

        def __ResetException():
            nonlocal previous_time
            nonlocal current_tries
            current_tries = 5
            previous_time = None

        def __CheckException():
            nonlocal previous_time
            nonlocal current_tries

            current_time = time.time()

            # First try
            if previous_time == None:
                previous_time = current_time
                current_tries -= 1
                return

            # Check if failure was too quick
            if current_time - previous_time <= 1:
                current_tries -= 1
                if current_tries == 0:
                    message = "Too many consecutive exceptions (maximum allowed is 5 with less than 1 second in between)"
                    logging.critical(message)
                    print(message)
                    sys.exit(1)
            else:
                __ResetException()


        while True:
            try:
                ResetTerminal()

                # Newline is useful in general here
                print()
                # Show menu
                print(self.GetMenu(depth))
                if previous_command != None:
                    print("Previous command: " +str(previous_command))

                # Setup completer
                self.completer.setup()
                # Get next input and save to history
                try:
                    next_input_str = GetNextOption()
                    if (MenuExit(next_input_str) == True):
                        return
                    next_input = int(next_input_str)
                    previous_invalid = False
                except ValueError:
                    # Empty enter goes to previous menu
                    if len(next_input_str) == 0:
                        return
                    if previous_invalid == False:
                        print("Invalid input")
                        previous_invalid = True
                    continue
                previous_command = next_input
                self.completer.update(next_input)

                # Activate selected entry
                self.SelectEntry(next_input, depth)

                # Reset allowed exceptions
                __ResetException()

            except KeyboardInterrupt:
                print("\nCtrl+C interrupts running operations and enter goes to the previous menu. Press Ctrl+D to back out of ProjectBase")
                continue
            except SlimError:
                # An error has already been printed, stop here
                logging.error("A thread errored out, canceling operation")
                print("\nThere was an error, operation canceled")
            except EOFError:
                # Ctrl+D
                print("\nBye :)")
                sys.exit(0)
            except SystemExit as sys_ex:
                raise sys_ex
            except Exception as exception:
                ErrorCheckLogs(exception)
                __CheckException()

            # Always reset directory after running an operation
            os.chdir(current_dir)
            if self.stay_in_menu == False:
                break
