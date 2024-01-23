import os
import sys
import fcntl
import select
import termios
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

def launchProcess(command, to_print=False):
    """
    Launch new process

    to_print: whether to print

    Returns:
        _type_: {"stdout":"<stdout>", "stderr": "<stderr>", "code": return code}
    """
    returned = {"stdout": "", "stderr": "", "code": ""}

    if command == "":
        return returned

    if to_print == True:
        print(command)

    logging.debug(command)

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        setPipeNonBlocking(sys.stdin)

        process = subprocess.Popen(command, shell=True,
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                executable='/bin/bash',
                                encoding="UTF-8",
                                bufsize=1
                                    )
        setPipeNonBlocking(process.stdout)
        setPipeNonBlocking(process.stderr)

        logging.debug("Starting process with pid "+str(process.pid)+" for command "+str(command))

        next_stdout = None
        next_stderr = None

        while process.poll() == None or next_stdout != "" or next_stderr != "":
            next_stdout = getNextOutput(process.stdout, to_print)
            if next_stdout != "":
                returned["stdout"] += next_stdout

            next_stderr = getNextOutput(process.stderr, to_print)
            if next_stderr != "":
                returned["stderr"] += next_stderr

        returned["code"] = str(process.poll())
        command = command.replace(";", ";\n")
        logging.debug(ColorFormat(Colors.Magenta, "\n$ "+command)+" \n "+getProcessResponse(returned))

        logging.debug(str(command)+" returned code: "+returned["code"])

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        setPipeBlocking(sys.stdin)

    if to_print == True:
        print()

    return returned

def parseProcessResponse(response):
    if response["stdout"] == "" or response["stdout"] == "\n":
        return remove_control_characters(response["stderr"].rstrip())
    return remove_control_characters(response["stdout"].rstrip())

def getProcessResponse(response):
    responses = []
    if response["stdout"] != "":
        stdout_str = response["stdout"].lstrip().rstrip()
        responses.append(ColorFormat(Colors.Green, "stdout: [")+stdout_str+ColorFormat(Colors.Green,"]"))

    if response["stderr"] != "":
        stderr_str = response["stderr"].lstrip().rstrip()
        responses.append(ColorFormat(Colors.Blue, "stderr: [")+stderr_str+ColorFormat(Colors.Blue, "]"))

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

def launchErrorProcess(command):
    ret =  launchProcess(command)

    if ret["stderr"] != "":
        print(command)
        print("stderr: "+ret["stderr"])

    return ret

"""
Changes to the given directory, launches the command in a forked process and
returns the { "stdout": "..." , "stderr": "..."  } dictionary
"""
def cdLaunchReturn(command, path=""):
    if path != "":
        return_value = launchProcess("cd "+path+"; "+command)
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

    while (output == None or output == "") and i < attempts:
        try:
            output = parseProcessResponse(cdLaunchReturn(command, path))
        except:
            output = None
        i += 1

    return output
