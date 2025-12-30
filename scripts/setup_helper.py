import os
import sys
from data.common import Abort, SetupScript
from data.paths import GetProjectPaths

"""
This script provides any necessary operation for the build process, so the exact build
 system in used can be abstracted, and no build system dependency is required.
"""

file_perms = {
    # R/W
    "data": 0o666,
    # R/W/X
    "exec": 0o777
}

path_types = ["tests", "executables"]
def WrongUsage(MainMessage = ""):
    ErrorMessage  = MainMessage+"\n"
    ErrorMessage += "\nUsage:\n"
    ErrorMessage += "Arguments: "+sys.argv[0]+" <PathType> <FileType> <FilePath>\n"
    ErrorMessage += f'\tPathType: {path_types} - Target path\n'
    ErrorMessage += '\tFileType: {file_perms.keys()} - Whether to make file executable\n'
    ErrorMessage += '\tFilePath: Path to the original resource\n'
    ErrorMessage += "Received data:\n\t"+'\n\t'.join(sys.argv[1:])+"\n"
    ErrorMessage += "Cannot proceed"
    Abort(ErrorMessage)

if __name__ != "__main__":
    Abort("This script is not meant to be imported, please run directly")

# Correct ammount of arguments
if len(sys.argv) != 5:
    WrongUsage("Incorrect amount of arguments")

# Sane arguments
_, ProjectName, PathType, FileType, FilePath = sys.argv

conditions = [
    [len(FilePath) > 0, f"A proper file path must be provided: {FilePath}"],
    [PathType in path_types, f"Only {path_types} are allowed as path type"],
    [FileType in file_perms.keys(), f"Only {file_perms.keys()} permissions are allowed"],
    [os.path.isfile(FilePath), f"File ({FilePath}) must exist"]
]

if any(not sublist[0] for sublist in conditions):
    WrongUsage(f"Arguments are not sane: {conditions}")

# Correct project path
ProjectPaths = GetProjectPaths(ProjectName)
if not os.path.isdir(ProjectPaths["project main"]):
    WrongUsage('Project "'+ProjectPaths["project main"]+'" does not exist')

FileName = FilePath.split("/")[-1]

print(f"Setting up {FileName} as a {FileType} file in the {PathType} folder")

TargetPath = ProjectPaths[PathType]+"/"+FileName
SetupScript(FilePath, TargetPath)


Permissions = file_perms[FileType]
os.chmod(TargetPath, Permissions)
