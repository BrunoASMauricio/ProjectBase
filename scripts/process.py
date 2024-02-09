import os
import re
import pty
import logging
import traceback
import subprocess
import unicodedata

from common import Abort, AppendToEnvVariable, GetTextDiff, ColorFormat, Colors

#                           PROCESS OPERATIONS

def RemoveControlCharacters(Str):
    """
    Removes control characters. Keeps \\n except if trailing
    """
    AllowedCCs = ['\n', '\t']
    NewStr = "".join(Ch for Ch in Str if (unicodedata.category(Ch)[0] != "C" or Ch in AllowedCCs))
    return NewStr.rstrip()

def RemoveAnsiEscapeCharacters(Str):
    AnsiEscape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return AnsiEscape.sub("", Str)

def LaunchProcess(Command, ToPrint=False):
    """
    Launch new process

    ToPrint: whether to print the output (process thinks it is in a TY)

    Returns:
        _type_: {"output":"<stdout>", "code": return code}
    """

    Returned = {"output": "", "code": ""}

    if Command == "":
        return {"output": "", "code": ""}

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

            Returned["output"] = CleanUTF8
        else:
            Returned["output"] = ""
    else:
        Result = subprocess.run(['bash', '-c', Command],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        Returned["output"] = Result.stdout.decode('utf-8')
        Returned["code"] = int(Result.returncode)

    return Returned

def ParseProcessResponse(Response):
    return RemoveControlCharacters(Response["output"].rstrip())

def OpenBashOnDirectoryAndWait(WorkingDirectory):
    print("Opening new slave terminal")
    print("Close when finished (hit Ctrl+D or type exit)")
    # Open a new Bash shell in the specified working directory
    Process = subprocess.Popen(['bash'], cwd=WorkingDirectory)


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

    if Result["output"] != ExpectedOutput:
        TextDiff = GetTextDiff(ExpectedOutput, Result["output"])
        Message  = "Wrong output for process"
        Message += ''.join(TextDiff)
        Message += "\t\nExpected (" + str(len(Result["output"])) + " characters)"
        Message += "="*30 + "\n>"+Result["output"]+"<"
        Message += "\t\nGot (" + str(len(ExpectedOutput)) + " characters)"
        Message += "="*30 + "\n>"+ExpectedOutput+"<"
        Abort(Message)

"""
Changes to the given directory, launches the Command in a forked process and
returns the { "stdout": "..." , "code": "..."  } dictionary
"""
def CDLaunchReturn(Command, Path="", ToPrint=False):
    if Path != "":
        CurrentDirectory = os.getcwd()
        os.chdir(Path)
        ReturnValue = LaunchProcess(Command, ToPrint)
        os.chdir(CurrentDirectory)
    else:
        ReturnValue = LaunchProcess(Command, ToPrint)

    return ReturnValue

"""
Changes to the given directory, launches the Command in a forked process and
returns the parsed stdout.
While the "output" Returned is empty, tries again
"""
def MultipleCDLaunch(Command, Path, ToPrint, Attempts=3):
    i = 0
    Output = None
    ThrownException = None
    while (Output == None or Output == "") and i < Attempts:
        try:
            Output = ParseProcessResponse(CDLaunchReturn(Command, Path, ToPrint))
        except Exception as ex:
            Output = None
            ThrownException = ex
        i += 1

    if Output == None:
        if ThrownException != None:
            logging.error(traceback.format_exc())
            logging.error("MultipleCDLaunch(" + Command + ") exception with: " + str(ThrownException))
            raise ThrownException

    return Output

def PrepareExecEnvironment(Project):
    AppendToEnvVariable("PYTHONPATH",       Project.Paths["scripts"])
    AppendToEnvVariable("PB_ROOT_NAME",     Project["ProjectRepoName"])
    AppendToEnvVariable("PB_ROOT_URL",      Project["ProjectRepoUrl"])
    AppendToEnvVariable("PB_ROOT_BRANCH",   Project["ProjectRepoBranch"])
    AppendToEnvVariable("PB_ROOT_COMMIT",   Project["ProjectRepoCommit"])
