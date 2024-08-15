import os
import sys
import logging
import traceback
from data.common import Assert
from enum import Enum
from processes.auto_completer import CustomCompleter
from data.settings import Settings
from data.common import RemoveNonAlfanumeric
from data.paths import JoinPaths

class EntryType(Enum):
    CALLBACK = 1
    MENU     = 2
    DYNAMIC  = 3

def GetNextOption(prompt="[<] "):
    global ProjectArgs
    
    if len(Settings["action"]) != 0:
        # Next automated action
        next_input = Settings["action"][0]
        del Settings["action"][0]
        print("[< Auto " + prompt + " <] {" + next_input + "}")
    else:
        # Called with --exit and no command, just exit
        if Settings["exit"] == True:
            sys.exit(0)
        next_input = input(prompt)

        # Check if we received multiple commands
        SplitInput = next_input.split(" ")
        if len(SplitInput) > 1:
            Settings["action"] += SplitInput[1:]
            next_input = SplitInput[0]

    return next_input

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

    def add_callback_entry(self, entry, Callback):
        self.entries.append([entry, EntryType.CALLBACK, Callback])
    
    def add_submenu_entry(self, entry, menu):
        self.entries.append([entry, EntryType.MENU, menu])

    """
    A function will run during menu selection and return the entries to show
    These entries come in a list of lists like so:
    [["entry 0 name", entry_0_callback, args_for_callback], ...]
    The callback will be called first with args_for_callback as named arguments
    """
    def add_dynamic_entries(self, entry_generator, fallback=None):
        self.entries.append([entry_generator, EntryType.DYNAMIC, fallback])
    
    """
    If obj is string, returns it
    Otherwise assumes it is a function that returns a string, calls that function and returns the result 
    """
    def get_text(self, obj):
        if obj == None:
            return ""
        # Only accept strings or functions
        if type(obj) == type(""):
            return obj

        # Non-function is ok to fail here
        return obj()
    
    """
    Return string with menu data
    """
    def get_menu(self, depth):
        index = 1
        menu = self.get_text(self.prologue)

        for entry in self.entries:
            if entry[1] == EntryType.DYNAMIC:
                # Remove previously generated entries
                if len(entry) == 4:
                    del entry[3]
                entries = entry[0]()
                if len(entries) == 0:
                    entry.append(self.get_text(entry[2]))
                else:
                    for new_entry in entries:
                        menu  += ("| " * depth) + str(index)+" ) " + new_entry[0] + "\n"
                        index += 1
                    # Store generated entries in dynamic entry
                entry.append(entries)
            else:
                if entry[1] == EntryType.MENU:
                    menu  += ("| " * depth) + str(index)+">) " + self.get_text(entry[0]) + "\n"
                elif entry[1] == EntryType.CALLBACK:
                    menu  += ("| " * depth) + str(index)+" ) " + self.get_text(entry[0]) + "\n"
                index += 1

        menu += self.get_text(self.epilogue)

        return menu
    """
    Activate the entry selected via its' index
    """
    def select_entry(self, index, depth):
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
            picked_entry[2].handle_input(depth + 1)
        else:
            dynamic_entry = picked_entry[3][picked_index]
            dynamic_entry[1](**dynamic_entry[2])
    """
    Print menu and handle input from user
    """
    def handle_input(self, depth = 0):
        current_dir = os.getcwd()
        previous_command = None
        previous_invalid = False
        while True:
            try:
                # Show menu
                print(self.get_menu(depth))
                if previous_command != None:
                    print("Previous command: " +str(previous_command))

                # Setup completer
                self.completer.setup()
                # Get next input and save to history
                try:
                    next_input_str = GetNextOption()
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
                self.select_entry(next_input, depth)

            except KeyboardInterrupt:
                print("\nCtrl+C exits running operations. Press Ctrl+D to back out of ProjectBase")
                continue
            except EOFError:
                break
            except Exception as Ex:
                logging.error("Uncaught exception: "+str(Ex))
                logging.error(traceback.format_stack())
            # Always reset directory after running an operation
            os.chdir(current_dir)
            if self.stay_in_menu == False:
                break
