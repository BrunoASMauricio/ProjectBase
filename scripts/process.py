import os
import sys
import fcntl
import re
import pty
import logging
import subprocess
import unicodedata
from colorama import Fore, Style
from common import ColorFormat, Colors

#                           PIPE OPERATIONS
def setPipeNonBlocking(pipe):
    fd = pipe.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

def setPipeBlocking(pipe):
    fd = pipe.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl & (~ os.O_NONBLOCK))

def getNextOutput(pipe, to_print=False):
    # Same logic as for stdout above
    returnal = ""
    char_buffer = ""
    # Used to look for \n's without \r's
    prev_char = ""
    new_char = "new_char"
    # Read until there are no more chars
    while new_char != "":
        new_char = pipe.read(1)
        # New char not empty
        if new_char != "":
            # Even on linux, sometimes \n does not perfrom carriager eturn
            # So always force \r\n
            if prev_char != "\r" and new_char == "\n":
                new_char = "\r"+new_char

            # User print()?
            if to_print == True:
                sys.stdout.write(new_char)

            # Add to buffer
            char_buffer += new_char
            if (new_char == "\n" or new_char == "\r" or new_char == "\r\n") and char_buffer.strip() != "":
                # Logging must be performed only on new lines (since it adds a tag to each output)
                logging.debug("stderr: "+char_buffer)
                char_buffer = ""

            returnal += new_char
        prev_char = new_char

    return returnal

#                           PROCESS OPERATIONS

def remove_control_characters(s):
    """
    Removes control characters. Keeps \\n except if trailing
    """
    allowd_CC = ['\n', '\t']
    new_s = "".join(ch for ch in s if (unicodedata.category(ch)[0] != "C" or ch in allowd_CC))
    return new_s.rstrip()

def remove_ansi_escape_characters(s):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub("", s)

def launchProcess(command, to_print=False):
    """
    Launch new process

    to_print: whether to print

    Returns:
        _type_: {"output":"<stdout>", "code": return code}
    """
    returned = {"output": "", "code": ""}

    if command == "":
        return returned

    if to_print == True:
        print(command)

    output_bytes = []
    def read(fd):
        data = os.read(fd, 1024)
        output_bytes.append(data)
        if to_print == True:
            return data
        return None

    # Remove all types of whitespace repetitions `echo  \t  a` -> `echo a`
    command = " ".join(command.split())
    command = command.replace('"', '\\"')

    returned["code"] = pty.spawn(['bash', '-c', command], read)

    if len(output_bytes) != 0:
        output_bytes = b''.join(output_bytes)
        output_utf8 = output_bytes.decode('utf-8')
        no_escape_utf8 = remove_ansi_escape_characters(output_utf8)
        clean_utf8 = remove_control_characters(no_escape_utf8)

        returned["output"] = clean_utf8
    else:
        returned["output"] = ""

    return returned

def parseProcessResponse(response):
    return remove_control_characters(response["output"].rstrip())

def getProcessResponse(response):
    responses = []
    if response["output"] != "":
        stdout_str = response["output"].lstrip().rstrip()
        responses.append("output: [" + stdout_str + "]")

    if len(responses) == 0:
        responses.append(ColorFormat(Colors.Yellow, "NO OUTPUT"))

    if response["code"]:
        responses.append(ColorFormat(Colors.Magenta, "Code: ")+str(response["code"]))

    return '\n'.join(responses)

def openBashOnDirectoryAndWait(working_directory):
    # Open a new Bash shell in the specified working directory
    process = subprocess.Popen(['bash'], cwd=working_directory)

    print("Close terminal when done (hit Ctrl+D or type exit)")

    # Wait for the Bash shell to be closed by the user
    process.wait()

#                           PROCESS OUTPUT

def launchSilentProcesses(commands):
    output = []
    for command in commands.split("\n"):
        output.append(launchProcess(command))
    return output

def launchSilentProcess(command):
    return launchProcess(command)

def launchVerboseProcess(command):
    ret =  launchProcess(command, True)
    return ret

"""
Changes to the given directory, launches the command in a forked process and
returns the { "stdout": "..." , "code": "..."  } dictionary
"""
def cdLaunchReturn(command, path=""):
    if path != "":
        cwd = os.getcwd()
        os.chdir(path)
        return_value = launchProcess(command)
        os.chdir(cwd)
    else:
        return_value = launchProcess(command)

    return return_value

"""
Changes to the given directory, launches the command in a forked process and
returns the parsed stdout.
While the "output" returned is empty, tries again
"""
def multipleCDLaunch(command, path, attempts=3):
    i = 0
    output = None
    thrown_ex = None
    while (output == None or output == "") and i < attempts:
        try:
            output = parseProcessResponse(cdLaunchReturn(command, path))
        except Exception as ex:
            output = None
            thrown_ex = ex
        i += 1

    if output == None:
        if thrown_ex != None:
            logging.error(str(thrown_ex))

    return output
