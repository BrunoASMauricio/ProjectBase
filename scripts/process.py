import os
import re
import pty
import logging
import traceback
import subprocess
import unicodedata

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
        print(Command)
        OutputBytes = []
        def read(fd):
            Data = os.read(fd, 1024)
            OutputBytes.append(Data)
            return Data

        # Remove all types of whitespace repetitions `echo  \t  a` -> `echo a`
        Command = " ".join(Command.split())

        Returned["code"] = int(pty.spawn(['bash', '-c', Command], read))

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
    return LaunchProcess(Command)

def LaunchVerboseProcess(Command):
    Returned =  LaunchProcess(Command, True)
    return Returned

"""
Changes to the given directory, launches the Command in a forked process and
returns the { "stdout": "..." , "code": "..."  } dictionary
"""
def CDLaunchReturn(Command, Path=""):
    if Path != "":
        CurrentDirectory = os.getcwd()
        os.chdir(Path)
        ReturnValue = LaunchProcess(Command)
        os.chdir(CurrentDirectory)
    else:
        ReturnValue = LaunchProcess(Command)

    return ReturnValue

"""
Changes to the given directory, launches the Command in a forked process and
returns the parsed stdout.
While the "output" Returned is empty, tries again
"""
def MultipleCDLaunch(Command, Path, Attempts=3):
    i = 0
    Output = None
    ThrownException = None
    while (Output == None or Output == "") and i < Attempts:
        try:
            Output = ParseProcessResponse(CDLaunchReturn(Command, Path))
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
