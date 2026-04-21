import re
import os
import sys
import shutil
import curses
import inspect
import logging
import difflib
import traceback
import unicodedata

from datetime import datetime
from data.error import *
import socket # for gethostname
import getpass # for getuser

from data.paths import GetBasePaths
from data.colors import ColorFormat, Colors
from data.print import *

class INDENT_FORMATTER(logging.Formatter):
    def __init__(self, style='%'):
        super().__init__('%(asctime)s,%(msecs)d %(levelname)s %(message)s', '%H:%M:%S', style)
        # , base_depth=None
        self.base_depth = None

    def setup(self):
        self.base_depth = len(inspect.stack())  # Set base depth

    def format(self, record):
        try:
            # Get current stack
            stack = inspect.stack()

            # For DEBUG logs after base_depth has been set, also print a light version of the stack
            if self.base_depth is None or record.levelno == logging.INFO:
                relevant_stack = ""
            else:
                relevant_stack = stack[10:-1*self.base_depth]
                if len(relevant_stack) > 0:
                    frame = relevant_stack[0].frame

                    relevant_stack = [ColorFormat(Colors.Green, f"{level.function}(#{level.lineno})") for level in relevant_stack]
                    relevant_stack = relevant_stack[::-1]
                    relevant_stack = "->".join(relevant_stack)
                    # Print arguments of the last call
                    args, _, _, values = inspect.getargvalues(frame)
                    function_args = ", ".join(f"\n  {ColorFormat(Colors.Yellow, arg)} = {values[arg]!r}" for arg in args) if args else ""
                    relevant_stack = f"{relevant_stack}({function_args})\n"

            # Apply indentation
            record.msg = f"\n{relevant_stack}{record.msg}\n"
        except Exception as ex:
            print(f"Logger error: {ex}")
            traceback.print_exc()
            sys.exit(0)

        return super().format(record)

Formatter = INDENT_FORMATTER()

def RemoveDuplicates(lst):
    return list(set(lst))

def AppendToEnvVariable(env_variable, new_value):
    if new_value is None:
        new_value = ""

    if env_variable not in os.environ.keys():
        os.environ[env_variable] = new_value
    else:
        # Only append if not already present
        BasicList = os.environ[env_variable].split(os.pathsep)
        if new_value not in BasicList:
            os.environ[env_variable] = new_value + os.pathsep + os.environ[env_variable]

def PrintableCharacterLength(string):
    return len(RemoveAnsiEscapeCharacters(RemoveControlCharacters(string)))

"""
Assemble a string based on the table (2D list) provided.
Each column is aligned to its' largest member
"""

def AssembleTable(rows, sep="|", headers=None):
    msg = ""
    if headers is not None:
        hdr_row = []
        for header in headers:
            hdr_row.append(ColorFormat(Colors.Grey, header))
        rows.insert(0, hdr_row)

    # Use `RemoveAllNonPrintable` and  direct padding to avoid color characters and such to be counted in padding
    widths = [max(len(RemoveAllNonPrintable(x)) for x in col) for col in zip(*rows)]
    for row in rows:
        msg += f" {sep} ".join((val + " " * (width - len(RemoveAllNonPrintable(val))) for val, width in zip(row, widths)))+"\n"
    return msg


"""
Print pre-formatted strings in aligned columns, fitting as many columns per
line as the terminal width allows.

Accepted shapes for `items`:
  - a flat list of strings: printed as a single columnar group.
  - a list of (header, items_list) tuples: each group is printed under its
    header (printed verbatim when not None, via `header_fn`). Column widths
    and column count are computed jointly across ALL groups, so column j on
    any line of any group sits at the same x-position — cross-group vertical
    alignment is preserved.

Each column is sized to the widest entry that actually lands in that column,
across all groups, so a single long outlier in one group does not inflate
every column in every other group.

Items within a group are laid out column-major (read down, then across).
Handles ANSI color codes correctly when measuring widths.
"""
def PrintInColumns(items, gap=3, header_fn=print):
    if not items:
        return

    # Normalize to [(header, items_list), ...]
    if isinstance(items[0], str):
        groups = [(None, items)]
    else:
        groups = list(items)

    group_lengths = [
        [PrintableCharacterLength(it) for it in group_items]
        for _, group_items in groups
    ]
    all_lengths = [l for lengths in group_lengths for l in lengths]

    if not all_lengths:
        for header, _ in groups:
            if header is not None:
                header_fn(header)
        return

    cols, _ = shutil.get_terminal_size(fallback=(80, 24))
    min_len = min(all_lengths)
    max_group_size = max(len(g) for _, g in groups)
    # Upper bound: can't exceed largest group, nor terminal packing limit
    max_candidate = min(
        max_group_size,
        max(1, (cols + gap) // (min_len + gap))
    )

    num_cols = 1
    col_widths = [max(all_lengths)]
    for candidate in range(max_candidate, 0, -1):
        widths = [0] * candidate
        for lengths in group_lengths:
            if not lengths:
                continue
            num_rows = (len(lengths) + candidate - 1) // candidate
            for j in range(candidate):
                start = j * num_rows
                end = min(start + num_rows, len(lengths))
                if start >= end:
                    continue
                col_max = max(lengths[start:end])
                if col_max > widths[j]:
                    widths[j] = col_max
        # Last column has no trailing gap
        total = sum(widths) + gap * (candidate - 1)
        if total <= cols:
            num_cols = candidate
            col_widths = widths
            break

    for (header, group_items), lengths in zip(groups, group_lengths):
        if header is not None:
            header_fn(header)
        if not group_items:
            continue
        num_rows = (len(group_items) + num_cols - 1) // num_cols
        for row in range(num_rows):
            line = ""
            for col in range(num_cols):
                idx = col * num_rows + row
                if idx < len(group_items):
                    padding = col_widths[col] - lengths[idx] + gap
                    line += group_items[idx] + " " * padding
            print(line.rstrip())


def CLICenterString(string, pad=" "):
    # Color characters count for length :()
    string_len = PrintableCharacterLength(string)
    cols, _ = shutil.get_terminal_size(fallback=(string_len, 1))
    padding_len = int((cols - string_len) / 2) - 1
    return pad * padding_len + string + pad * padding_len

def GetTextDiff(Text1, Text2):
    diff = difflib.ndiff(Text1.split("\n"), Text2.split("\n"))
    return ''.join(diff)

def RemoveAllNonPrintable(str):
    return RemoveControlCharacters(RemoveTerminalColorCodes(RemoveNonAscii(str)))

def RemoveControlCharacters(str):
    """
    Removes control characters. Keeps \\n except if trailing
    """
    allowed_CCs = ['\n', '\t']
    new_str = "".join(ch for ch in str if (unicodedata.category(ch)[0] != "C" or ch in allowed_CCs))
    return new_str.rstrip()

def RemoveTerminalColorCodes(text):
    # return re.sub(r'\x1b\[[0-9;]*m', '', text)
    return re.sub(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

def RemoveNonAscii(str):
    return ''.join(char for char in str if ord(char) < 128)

def RemoveAnsiEscapeCharacters(str):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub("", str)

def RemoveSequentialDuplicates(str, sub_str):
    List = str.split(sub_str)
    List = [list_el for list_el in List if len(list_el) != 0]

    NewStr = sub_str.join(List)

    # Special cases for starting/ending with sub_str (will lead to empty
    # element on either side, without being sequential duplicate)
    if str[0] == sub_str:
        NewStr = sub_str + NewStr

    if str[-1] == sub_str:
        NewStr = NewStr + sub_str

    return NewStr

def IsEmpty(object):
    if object is None:
        return True

    if type(object) == type({}):
        return len(object.keys()) == 0

    if type(object) == type([]):
        return len(object) == 0

    if type(object) == type(""):
        return object.strip() == ""

    # Other values cannot be empty (no way to detect that)
    return False
    # raise Exception("Unknown type for IsEmpty: " + str(type(object)) + str(object))

def RemoveNonAlfanumeric(string):
    return re.sub(r'[^A-Za-z0-9]+', '', string)

def ValueNotEmpty(list, name):
    if name in list and False == IsEmpty(list[name]):
        return True
    return False

"""
Gets the value from the dict if Name exists, or
Default is returned if it does not exist
"""
def GetValueOrDefault(dict, name, default = None):
    if name in dict.keys():
        # If there is a default value, enforce the type is the same to the
        # existing value
        if default is not None and type(default) != type(dict[name]):
            raise Exception(f"Incorrect type \"{type(dict[name])}\" for value named {name}. Should be {type(default)}")
        return dict[name]
    return default

"""
Remove 'None' elements from a list
"""
def RemoveEmpty(iterable):
    if type(iterable) == type(list()):
        return [list_el for list_el in iterable if IsEmpty(list_el) is False]
    else:
        new_dict = {}
        for key in iterable:
            if IsEmpty(iterable[key]) is False:
                new_dict[key] = iterable[key]
        return new_dict
def StringIsNumber(Str):
    number_regex = '^[0-9]+$'
    if(re.search(number_regex, Str)):
        return True
    return False

def LoadFromFile(file_path, default=None):
    if os.path.isfile(file_path):
        with open(file_path, "r") as file:
            return file.read()
    return default

def DumpToFile(file_path, data, mode='w'):
    with open(file_path, mode) as file:
        file.write(data)

"""
Present Message to user and return True if the response is y or Y, False if n or N
Loop if response is not in nNyY
"""
YES_NO_PROMPT = "[yY/nN]"
def UserYesNoChoice(choice, default_no = False):
    # answer = input("("+ColorFormat(Colors.Green,"Yy")+"/"+ColorFormat(Colors.Red,"Nn")+"): ")
    if choice in ["y", "Y"]:
        return True
    elif choice in ["n", "N"]:
        return False
    return default_no

"""
Copy some script over and replace variables
"""
def SetupScript(script_file, target_file, variable_substitutions={}):
    logging.debug(f"Setting up script {script_file}")

    whole_script = ""
    project_base_paths = GetBasePaths()

    if script_file.endswith(".sh"):
        # Get bash header
        with open(project_base_paths["templates"]+"/scriptHeader.sh", 'r') as f:
            whole_script = f.read()+"\n\n"

    # Get rest of script
    with open(script_file, 'r') as f:
        whole_script += f.read()

    # Perform variable substitutions
    for variable_name in variable_substitutions:
        whole_script = whole_script.replace("$$"+variable_name+"$$", variable_substitutions[variable_name])

    # Write script back
    with open(target_file, 'w') as f:
        f.write(whole_script)


# Sets up a script according to its template and the target variable substitutions
def SetupTemplate(template_name, target_file, variable_substitutions={}):
    project_base_paths = GetBasePaths()

    # Var replace and copy it over to the correct place
    SetupScript(f"{project_base_paths["templates"]}/{template_name}", target_file, variable_substitutions)

"""
If obj is string, returns it
Otherwise assumes it is a function that returns a string, calls that function and returns the result
"""
def GetText(obj):
    if obj is None:
        return ""
    # Only accept strings or functions
    if type(obj) == type(""):
        return obj

    # Non-function is ok to fail here
    return obj()

def GetNow():
    return str(datetime.now())

def GetTime():
    current_datetime = datetime.now()
    return str(current_datetime.strftime("%m/%d/%Y %H:%M:%S"))

def GetHost():
    return f"{getpass.getuser()}@{socket.gethostname()}"

def GetTimeForPath():
    return GetTime().replace(" ", "_").replace("/", "_")

def ResetTerminal():
    # Initialize curses
    stdscr = curses.initscr()

    # Set terminal back to normal mode
    curses.endwin()
    del stdscr