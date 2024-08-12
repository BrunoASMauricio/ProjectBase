import os
import pty
import logging
import traceback
import subprocess

from time import sleep
from threading import Thread, Lock
from data.settings import Settings
from data.colors import ColorFormat, Colors
from processes.progress_bar import PrintProgressBar
from data.common import Abort, AppendToEnvVariable, RemoveControlCharacters, RemoveAnsiEscapeCharacters

#                           PROCESS OPERATIONS

def PrintProgressWhileWaitOnThreads(threads, print_function, print_arguments={}):
    # Wait for all threads
    if Settings["single_thread"] == False:
        a_thread_is_alive = True
        while a_thread_is_alive == True:
            a_thread_is_alive = False
            for thread in threads:
                if thread.is_alive():
                    a_thread_is_alive = True
                    continue
            print_function(**print_arguments)
            sleep(0.05)

operation_status = {}
operation_lock = Lock()

def __PrintRunOnFoldersProgress(paths):
    current_progress = len(operation_status)
    total_repos      = len(paths)
    if total_repos == current_progress:
        PrintProgressBar(current_progress, total_repos, prefix = 'Running:', suffix = 'Ran on ('+str(current_progress)+') folders')
    else:
        PrintProgressBar(current_progress, total_repos, prefix = 'Running:', suffix = "Done on " + str(current_progress) + "/" + str(total_repos) + " folders")

def __RunOnFoldersThreadWrapper(callback, path, arguments={}):
    global operation_lock
    global operation_status
    os.chdir(path)
    Result = callback(**arguments)

    operation_lock.acquire()
    operation_status[path] = Result
    operation_lock.release()

"""
For each path, change directory to it, execute the provided function with the
provided arguments, concatenate result into list and return said list
"""
def RunOnFolders(paths, callback, arguments={}):
    global operation_status

    if len(paths) == 0:
        return {}

    operation_status.clear()
    threads = []
    current_dir = os.getcwd()

    for path in paths:
        if not os.path.isdir(path):
            raise Exception(path+" is not a valid directory, cannot perform "+str(callback)+"("+str(arguments)+")")
        if Settings["single_thread"]:
            os.chdir(path)
            operation_status[path] = callback(**arguments)
            __PrintRunOnFoldersProgress(paths)
        else:
            thread = Thread(target=__RunOnFoldersThreadWrapper, args=(callback, path, arguments,))
            threads.append(thread)
            thread.start()

    PrintProgressWhileWaitOnThreads(threads, __PrintRunOnFoldersProgress, {"paths":paths})
    os.chdir(current_dir)

    return operation_status

def RunExecutable(CommandString):
    return subprocess.run(CommandString, shell=True)

def LaunchProcess(Command, ToPrint=False):
    """
    Launch new process

    ToPrint: whether to print the output (process thinks it is in a TY)

    Returns:
        _type_: {"stdout":"<stdout>", "code": return code}
    """

    Returned = {"stdout": "", "stderr": "", "code": ""}

    if Command == "":
        return {"stdout": "", "stderr": "", "code": ""}

    if ToPrint == True:
        print(ColorFormat(Colors.Blue, Command))
        OutputBytes = []
        def read(fd):
            Data = os.read(fd, 1024)
            OutputBytes.append(Data)
            return Data

        # Remove all types of whitespace repetitions `echo  \t  a` -> `echo a`
        Command = " ".join(Command.split())

        Returned["code"] = int(pty.spawn(['bash', '-c', Command], read))

        if ToPrint == True:
            print(ColorFormat(Colors.Blue, "Returned " + str(Returned["code"])))

        if len(OutputBytes) != 0:
            OutputBytes = b''.join(OutputBytes)
            OutputUTF8 = OutputBytes.decode('utf-8')
            NoEscapeUTF8 = RemoveAnsiEscapeCharacters(OutputUTF8)
            CleanUTF8 = RemoveControlCharacters(NoEscapeUTF8)

            Returned["stdout"] = CleanUTF8
        else:
            Returned["stdout"] = ""
    else:
        Result = subprocess.run(['bash', '-c', Command],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        Returned["stdout"] = Result.stdout.decode('utf-8')
        Returned["stderr"] = Result.stderr.decode('utf-8')
        Returned["code"] = int(Result.returncode)

    if Returned["code"] != 0:
        message  = "\n\t========================= Process failed (start) =========================\n"
        message += "\t\tProcess returned failure (" + ColorFormat(Colors.Yellow, str(Returned["code"])) + "):\n"
        message += ColorFormat(Colors.Cyan, Command+"\n")
        message += ColorFormat(Colors.Blue, "stdout: " + Returned["stdout"]+"\n")
        message += ColorFormat(Colors.Red,  "stderr: " + Returned["stderr"]+"\n")
        message += "Stack Trace:\n"
        for line in traceback.format_stack():
            pieces = line.strip().split("\n")
            if len(pieces) == 2:
                file, callback = pieces
                function  = file.split(" in ")[-1]
                # line NUMBER, .. # Get NUMBER, .. # Remove .. # Remove ,
                file_line = file.split(" line ")[-1].split(" ")[0][:-1]
                message += function + "() line " + str(file_line) + "\n" +ColorFormat(Colors.Green, callback) + "\n"
            else:
                message += line
        message += "\n\t========================= Process failed (end) =========================\n"
        logging.error(message)

    return Returned

def ParseProcessResponse(Response):
    return RemoveControlCharacters(Response["stdout"].rstrip())

def OpenBashOnDirectoryAndWait(working_directory):
    print("Opening new slave terminal")
    print("Close when finished (hit Ctrl+D or type exit)")
    # Open a new Bash shell in the specified working directory
    Process = subprocess.Popen(['bash'], cwd=working_directory)

    # Wait for the Bash shell to be closed by the user
    Process.wait()

#                           PROCESS OUTPUT

def LaunchSilentProcess(Command):
    return LaunchProcess(Command, False)

def LaunchVerboseProcess(Command):
    return LaunchProcess(Command, True)


def AssertProcessRun(Process, ExpectedCode, ExpectedOutput):
    Result = LaunchSilentProcess(Process)
    if Result["code"] != ExpectedCode:
        Message  = "Wrong code for process"
        Message += "\n\tExpected " + str(ExpectedCode)
        Message += "\n\tGot " + str(Result["code"])
        Abort(Message)

    if Result["stdout"] != ExpectedOutput:
        TextDiff = GetTextDiff(ExpectedOutput, Result["stdout"])
        Message  = "Wrong output for process"
        Message += ''.join(TextDiff)
        Message += "\t\nExpected (" + str(len(Result["stdout"])) + " characters)"
        Message += "="*30 + "\n>"+Result["stdout"]+"<"
        Message += "\t\nGot (" + str(len(ExpectedOutput)) + " characters)"
        Message += "="*30 + "\n>"+ExpectedOutput+"<"
        Abort(Message)

"""
Changes to the given directory, launches the Command in a forked process and
returns the { "stdout": "..." , "code": "..."  } dictionary
"""
def LaunchProcessAt(Command, Path="", ToPrint=False):
    if Path != "":
        # CurrentDirectory = os.getcwd()
        # os.chdir(Path)
        ReturnValue = LaunchProcess("set -e; cd " + Path + "; " +Command, ToPrint)
        # os.chdir(CurrentDirectory)
    else:
        ReturnValue = LaunchProcess(Command, ToPrint)

    return ReturnValue

"""
Changes to the given directory, launches the Command in a forked process and
returns the parsed stdout.
While the "stdout" Returned is empty, tries again
"""
def MultipleCDLaunch(Command, Path, ToPrint, Attempts=3):
    i = 0
    Output = None
    ThrownException = None
    while (Output == None or Output == "") and i < Attempts:
        try:
            Output = ParseProcessResponse(LaunchProcessAt(Command, Path, ToPrint))
        except Exception as ex:
            Output = None
            ThrownException = ex
        i += 1

    if Output == None:
        if ThrownException != None:
            logging.error("MultipleCDLaunch(" + Command + ") exception with: " + str(ThrownException))
            logging.error(traceback.format_exc())
            raise ThrownException

    return Output

def PrepareExecEnvironment():
    AppendToEnvVariable("PYTHONPATH",       Settings["paths"]["scripts"])
    AppendToEnvVariable("PB_ROOT_NAME",     Settings["name"])
    AppendToEnvVariable("PB_ROOT_URL",      Settings["url"])
