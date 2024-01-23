import os
import json
import pickle
import hashlib
import logging
import traceback
from git import *
from time import sleep

from colorama import Fore, Style
from process import *

def get_paths(project_name):
    """
    Builds and returns a dictionary with a projects' directory structure
    indexed by a string describing each paths' purpose
    """
    # Setup paths
    paths = {
        "project_base": os.getcwd()
    }
    # Where the .git files are located
    paths[".gits"] =        paths["project_base"]+"/bare_gits"
    paths["temporary"] =    paths["project_base"]+"/temporary"
    
    # Projects main directory
    paths["project_main"] = paths["project_base"]+"/projects/" + project_name + ".ProjectBase"
    
    # Projects cmake cache
    paths["cmake"] =        paths["project_main"]+"/cmake"
    
    # Project output binaries
    paths["binaries"] =     paths["project_main"]+"/binaries"
    
    # Project repository worktrees
    paths["project_code"] = paths["project_main"]+'/code'
    
    # Path for repositories that don't specify local_path
    paths["general_repository"] = 'general'
    
    # Path for output binaries
    paths["objects"]     = paths["binaries"]+"/objects"
    paths["executables"] = paths["objects"]+"/executables"
    paths["tests"]       = paths["objects"]+"/tests"
    paths["libraries"]   = paths["binaries"]+"/libs"

    # Path for whatever data might be used/needed
    paths["data"]        = paths["project_main"]+"/data"

    return paths

def GetRepositoryPaths(loaded_repos):
    all_repositories = []
    for repo_id in loaded_repos:
        repo = loaded_repos[repo_id]
        if not repo.hasFlag("no commit"):
            all_repositories.append(repo['full_local_path'])
    return all_repositories

"""
Remove 'None' elements from a list
"""
def RemoveNone(list):
    return [x for x in list if x != None]

def programIsInstalled(program):
    return parseProcessResponse(launchSilentProcess("command -v "+program)) != ""

def installProgram(program):
    if programIsInstalled(program):
        return

    if programIsInstalled("apt"):
        launchVerboseProcess("sudo apt-get install "+program)
    elif programIsInstalled("pacman"):
        launchVerboseProcess("sudo apt-get install "+program)
    else:
        raise Exception("No installer found to install program "+program)

"""
For each path, change directory to it, execute the provided function with the
provided arguments, concatenate result into list and return said list
"""
def runOnFolders(paths, function_to_run, list_arguments={}):
    operation_status = []
    cwd = os.getcwd()

    for path in paths:
        if not os.path.isdir(path):
            raise Exception(path+" is not a valid directory, cannot perform "+str(function_to_run))

        os.chdir(path)

        result = function_to_run(**list_arguments)
        operation_status.append(result)
        # Sleep to prevent what?
        sleep(0.05)

    os.chdir(cwd)

    # for inode in os.listdir(path_to_dir):
    #     if os.path.isdir(path_to_dir+"/"+inode) and inode != ".git":
    #         result_list = runOnFolders(path_to_dir+"/"+inode, function_to_run, list_arguments)
    #         if len(result_list) > 0:
    #             operation_status = operation_status + result_list

    return operation_status

def getRepoConfig(installed_repos, repository_url):
    for repo in installed_repos:
        if installed_repos[repo]["url"] == repository_url:
            return installed_repos[repo]
    return None

def getFileHash(file_to_hash):
    with open(file_to_hash, 'rb') as f:
        calculated_hash = hashlib.md5(f.read()).hexdigest()
    return calculated_hash

# Sets up a script according to its template and the target variable substitutions
def setupScript(script_name, target_file, variable_substitutions={}):
    whole_script = ""
    if script_name.endswith(".sh"):
        # Get bash header
        with open("templates/scriptHeader.sh", 'r') as f:
            whole_script = f.read()+"\n\n"

    # Get rest of script
    with open("templates/"+script_name, 'r') as f:
        whole_script += f.read()
    # Perform variable substitutions
    for variable_name in variable_substitutions:
        whole_script = whole_script.replace("$$"+variable_name+"$$", variable_substitutions[variable_name])

    # Write script back
    with open(target_file, 'w') as f:
        f.write(whole_script)

def loadJsonFile(path, error_value=None, variable_substitutions={}):
    """
    Returns the json from the given file, or error_value in cas of an error
    Parameters
    ----------
    file : string
        The target file path
    error_value : Object
        The object returned in case there is an error loading the json file
        If Object is None, the exception is thrown
    """
    try:
        with open(path, 'r') as file:
            json_data = json.load(file)

        for variable_name in variable_substitutions:
            json_data = json_data.replace("$$"+variable_name+"$$", variable_substitutions[variable_name])

        return json_data

    except Exception as ex:
        if error_value == None:
            raise Exception("Could not load json from file "+path+" "+traceback.format_exc())
    return error_value

from enum import Enum

class Colors(Enum):
    Red = 1
    Blue = 2
    Yellow = 3
    Green = 4
    Magenta = 5

globals().update({color.name: color for color in Colors})

ColorDict = {
    Colors.Red: Fore.RED,
    Colors.Blue: Fore.BLUE,
    Colors.Yellow: Fore.YELLOW,
    Colors.Green: Fore.GREEN,
    Colors.Magenta: Fore.MAGENTA
}

def ColorFormat(Color, Message):
    return ColorDict[Color] + Message + Style.RESET_ALL

def UserYesNoChoice(Message):
    try:
        print(Message)
        answer = input("("+ColorFormat(Colors.Green,"Yy")+"/"+ColorFormat(Colors.Red,"Nn")+"): ")
        if answer in ["y", "Y"]:
            answer = True
        else:
            answer = False

    except Exception as ex:
        answer = False

    return answer


def loadPickleFile(path, error_value=None):
    try:
        if os.path.isfile(path):
            with open(path, 'rb') as file:
                return pickle.load(file)
    except Exception as ex:
        if error_value == None:
            logging.error("Could not load json from file "+path+" "+traceback.format_exc())
            raise ex
    return error_value

def dumpPickleFile(path, object):
    with open(path, "wb") as f:
        pickle.dump(object, f)

