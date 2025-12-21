import os
import sys
from common import Abort, SetupTemplateScript, GetProjectPaths


"""
This script provides any necessary operation for the build process, so the exact build
 system in used can be abstracted, and no build system dependency is required.
"""


"""

"""
def WrongUsage(MainMessage = ""):
    ErrorMessage  = MainMessage+"\n"
    ErrorMessage += "\nUsage:\n"
    ErrorMessage += "Arguments: "+sys.argv[0]+" <PathType> <FileType> <FilePath>\n"
    ErrorMessage += '\tPathType: ["tests" | "executables"] - Target path\n'
    ErrorMessage += '\tFileType: ["data" | "exec"] - Whether to make file executable\n'
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

FileTypePermissions = {
    # R/W
    "data": 0o666,
    # R/W/X
    "exec": 0o777
}

EverythingIsOk =                      PathType in ["tests", "executables"]
EverythingIsOk = EverythingIsOk and ( FileType in FileTypePermissions.keys() )
EverythingIsOk = EverythingIsOk and ( os.path.isfile(FilePath) )
if EverythingIsOk != True:
    WrongUsage("Arguments are not sane")

# Correct project path
ProjectPaths = GetProjectPaths(ProjectName)
if not os.path.isdir(ProjectPaths["project main"]):
    WrongUsage('Project "'+ProjectPaths["project main"]+'" does not exist')

FileName = FilePath.split("/")[-1]
TargetPath = ProjectPaths[PathType]+"/"+FileName
SetupTemplateScript(FilePath, TargetPath)

Permissions = FileTypePermissions[FileType]
os.chmod(TargetPath, Permissions)
# message("Setting up ${FILE_PATH} as a ${FILE_TYPE} file in the ${PATH_TYPE} folder")
