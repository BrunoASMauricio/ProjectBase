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

def PrintProgressWhileWaitOnThreads(Threads, PrintFunction=None, PrintArguments=None):
    if PrintArguments == None:
        PrintArguments = {}

    def PrintProgress():
        if PrintFunction != None:
            PrintFunction(**PrintArguments)
        else:
            Progress = len(Threads) - ThreadsAlive
            PrintProgressBar(Progress, len(Threads), prefix = 'Running:', suffix = 'Threads finished ' + str(Progress) + '/' + str(len(Threads)))

    # Wait for all threads
    ThreadsAlive = len(Threads)
    Progress = 0
    prev_alive = ThreadsAlive
    while ThreadsAlive != Progress:
        ThreadsAlive = len(Threads)
        for thread in Threads:
            if thread.is_alive():
                continue
            ThreadsAlive -= 1
        if prev_alive != ThreadsAlive:
            PrintProgress()
        sleep(0.05)
    PrintProgress()

operation_status = {}
operation_lock = Lock()

def __PrintRunOnFoldersProgress(paths):
    current_progress = len(operation_status)
    total_repos      = len(paths)
    if total_repos == current_progress:
        PrintProgressBar(current_progress, total_repos, prefix = 'Running:', suffix = 'Ran on ('+str(current_progress)+') folders')
    else:
        PrintProgressBar(current_progress, total_repos, prefix = 'Running:', suffix = "Done on " + str(current_progress) + "/" + str(total_repos) + " folders")

"""
Run run_callback in a separate thread for each argument in run_args (which is also passed to that thread)
"""
def RunInThreads(run_callback, run_args):
    threads = []
    for run_arg in run_args:
        thread = Thread(target=run_callback, args=run_arg)
        threads.append(thread)
        thread.start()
    return threads

"""
Run run_callback with each argument in run_args, in separate threads or
sequentially if "single thread" mode is on
If print_callback is present, it will be called to register the operation progress
"""
def RunInThreadsWithProgress(run_callback, run_args, print_callback=None, print_args=None):
    PrintProgressBar(0, len(run_args), prefix = 'Starting...', suffix = '0/' + str(len(run_args)))
    if Settings["single thread"]:
        for run_arg_ind in run_args:
            run_arg = run_args[run_arg_ind]
            try:
                run_callback(*run_arg)
                if print_callback != None:
                    if print_args != None:
                        print_callback(print_args)
                    else:
                        print_callback()
                else:
                    PrintProgressBar(run_arg_ind, len(run_args), prefix = 'Running:', suffix = 'Work finished ' + str(run_arg_ind) + '/' + str(len(run_args)))
            except KeyboardInterrupt:
                print("Keyboard Interrupt, stopping")
                return
    else:
        try:
            threads = RunInThreads(run_callback, run_args)
            PrintProgressWhileWaitOnThreads(threads, print_callback, print_args)
        except KeyboardInterrupt:
            print("Keyboard Interrupt, stopping threads")
            for thread in threads:
                if thread.is_alive():
                    thread._stop()

def __RunOnFoldersThreadWrapper(callback, path, arguments={}):
    global operation_lock
    global operation_status

    arguments["path"] = path
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
    current_dir = os.getcwd()
    run_args = []

    for path in paths:
        if not os.path.isdir(path):
            raise Exception(path+" is not a valid directory, cannot perform "+str(callback)+"("+str(arguments)+")")
        run_args.append((callback, path, arguments,))

    RunInThreadsWithProgress(__RunOnFoldersThreadWrapper, run_args, __PrintRunOnFoldersProgress, {"paths":paths})
    os.chdir(current_dir)

    return operation_status

def RunExecutable(CommandString):
    return subprocess.run(CommandString, shell=True)

class ProcessError(Exception):
    def __init__(self, Message, Returned):
        # Call the base class constructor with the parameters it needs
        super().__init__(Message)
        self.Returned = Returned

def LaunchProcess(Command, to_print=False):
    """
    Launch new process

    to_print: whether to print the output (process thinks it is in a TY)

    Returns:
        _type_: {"stdout":"<stdout>", "code": return code}
    """

    Returned = {"stdout": "", "stderr": "", "code": ""}

    if Command == "":
        return {"stdout": "", "stderr": "", "code": ""}

    if to_print == True:
        print(ColorFormat(Colors.Blue, Command))
        OutputBytes = []
        def read(fd):
            Data = os.read(fd, 1024)
            OutputBytes.append(Data)
            return Data

        # Remove all types of whitespace repetitions `echo  \t  a` -> `echo a`
        Command = " ".join(Command.split())

        Returned["code"] = int(pty.spawn(['bash', '-c', Command], read))

        if to_print == True:
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
        Message  = "\n\t========================= Process failed (start) =========================\n"
        Message += "\t\tProcess returned failure (" + ColorFormat(Colors.Yellow, str(Returned["code"])) + "):\n"
        Message += ColorFormat(Colors.Cyan, Command+"\n")
        Message += ColorFormat(Colors.Blue, "stdout: " + Returned["stdout"]+"\n")
        Message += ColorFormat(Colors.Red,  "stderr: " + Returned["stderr"]+"\n")
        Message += "Stack Trace:\n"
        for Line in traceback.format_stack():
            Pieces = Line.strip().split("\n")
            if len(Pieces) == 2:
                file, callback = Pieces
                function  = file.split(" in ")[-1]
                # Line NUMBER, .. # Get NUMBER, .. # Remove .. # Remove ,
                file_Line = file.split(" Line ")[-1].split(" ")[0][:-1]
                Message += function + "() Line " + str(file_Line) + "\n" +ColorFormat(Colors.Green, callback) + "\n"
            else:
                Message += Line
        Message += "\n\t========================= Process failed (end) =========================\n"
        raise ProcessError(Message, Returned)

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
def LaunchProcessAt(Command, Path="", to_print=False):
    if Path != "":
        # CurrentDirectory = os.getcwd()
        # os.chdir(Path)
        ReturnValue = LaunchProcess("set -e; cd " + Path + "; " +Command, to_print)
        # os.chdir(CurrentDirectory)
    else:
        ReturnValue = LaunchProcess(Command, to_print)

    return ReturnValue

"""
Changes to the given directory, launches the Command in a forked process and
returns the parsed stdout.
While the "stdout" Returned is empty, tries again
"""
def MultipleCDLaunch(Command, Path, to_print, Attempts=3):
    i = 0
    Output = None
    ThrownException = None
    while (Output == None or Output == "") and i < Attempts:
        try:
            Output = ParseProcessResponse(LaunchProcessAt(Command, Path, to_print))
        except Exception as ex:
            Output = None
            ThrownException = ex
        i += 1

    if Output == None:
        if ThrownException != None:
            # logging.error("MultipleCDLaunch(" + Command + ") exception with: " + str(ThrownException))
            # logging.error(traceback.format_exc())
            raise ThrownException

    return Output

def PrepareExecEnvironment():
    AppendToEnvVariable("PYTHONPATH",       Settings["paths"]["scripts"])
    AppendToEnvVariable("PB_ROOT_NAME",     Settings["name"])
    AppendToEnvVariable("PB_ROOT_URL",      Settings["url"])
