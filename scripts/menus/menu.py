import os
import traceback
from enum import Enum
from processes.auto_completer import CustomCompleter
from data.settings import *
from data.common import RemoveNonAlfanumeric

class EntryType(Enum):
    CALLBACK = 1
    MENU = 2

def GetNextOption():
    global ProjectArgs
    
    if len(settings["action"]) != 0:
        # Next automated action
        next_input = settings["action"][0]
        del settings["action"][0]
        print("[< Auto <] {" + next_input + "}")
    else:
        # Called with --exit and no command, just exit
        if settings["exit"] == True:
            sys.exit(0)
        next_input = input("[<] ")

        # Check if we received multiple commands
        SplitInput = next_input.split(" ")
        if len(SplitInput) > 1:
            settings["action"] += SplitInput[1:]
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
            self.history_file = settings["paths"]["history"] + "/" + name
            self.completer = CustomCompleter(self.history_file, [])
            all_menu_names.append(name)

    def add_callback_entry(self, entry, Callback):
        self.entries.append([entry, EntryType.CALLBACK, Callback])
    
    def add_submenu_entry(self, entry, menu):
        self.entries.append([entry, EntryType.MENU, menu])
    
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
            if entry[1] == EntryType.MENU:
                menu  += ("| " * depth) + str(index)+">) " + self.get_text(entry[0]) + "\n"
            else:
                menu  += ("| " * depth) + str(index)+" ) " + self.get_text(entry[0]) + "\n"
            index += 1

        menu += self.get_text(self.epilogue)

        return menu
    """
    Activate the entry selected via its' index
    """
    def select_entry(self, index, depth):
        if index > len(self.entries):
            print("Menu has " + str(len(self.entries)) + " entries, input " + str(index) + " is not valid")
            return 

        entry = self.entries[index-1]

        if entry[1] == EntryType.CALLBACK:
            entry[2]()
        else:
            entry[2].handle_input(depth + 1)
    """
    Print menu and handle input from user
    """
    def handle_input(self, depth = 0):
        current_dir = os.getcwd()
        previous_command = None
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
                    next_input = int(GetNextOption())
                except ValueError:
                    print("Invalid input")
                    continue
                previous_command = next_input
                self.completer.update(next_input)

                # Activate selected entry
                self.select_entry(next_input, depth)

                # Always reset directory after running an operation
                os.chdir(current_dir)
                if self.stay_in_menu == False:
                    break
            except KeyboardInterrupt:
                print("\nCtrl+C exits running operations. Press Ctrl+D to back out of ProjectBase")
                continue
            except EOFError:
                break
            # except Exception as Ex:
            #     print("Uncaught exception: "+str(Ex))
            #     traceback.print_exc()