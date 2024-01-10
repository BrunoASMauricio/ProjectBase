import logging
import traceback
import sys
import re

from common import *
from project import *


def runProjectExecutable(remote_repo_url, project_branch, project_commit, path):
    #global completer
    project = Project(remote_repo_url, project_branch, project_commit)
    
    executables_available = []

    os.chdir(project.paths["project_main"])

    index = 0
    print("Available executables to run, found in "+path+" (Ctrl-C to exit):")
    for entry in os.scandir(path):

        print("\t["+str(index)+"] "+ColorFormat(Colors.Blue, entry.name))
        executables_available.append(entry.name)
        index += 1
    
    if index == 0:
        print("No executables found")
        return
    
    print("Use G or V as a prefix (G0/V0) to run with GDB or Valgrind respectively")
    print("Every space separated word in front of the first one will be passed as a parameter")

    try:
        user_input = input("[<] ")

        # No input (Enter pressed)
        if len(user_input) == 0:
            return

        prefix = ""
        if user_input[0].upper() == "G":
            prefix = "gdb --args "
            user_input = user_input[1:]
        elif user_input[0].upper() == "S":
            prefix = "gdbserver 127.0.0.1:6175 "
            user_input = user_input[1:]
        elif user_input[0].upper() == "V":
            prefix = "valgrind -s --leak-check=full --track-origins=yes"
            user_input = user_input[1:]

        number_regex = '^[0-9]+$'

        base_input = user_input.split(' ')[0]

        # Obtain target executable
        if(re.search(number_regex, base_input)):
            # By index
            executable = path+"/"+executables_available[int(base_input)]
        else:
            # By name
            if os.path.isfile(path+"/"+base_input):
                executable = path+"/"+base_input
            # By relative project name
            elif os.path.isfile(project.paths["project_main"]+"/"+base_input):
                executable = project.paths["project_main"]+"/"+base_input
            # By absolute project name
            elif os.path.isfile(base_input):
                executable = base_input
            else:
                print("Unkown executable: "+base_input)
                return
        
        # Setup base commands and its arguments
        base_arguments = ' '.join([x for x in user_input.split(' ')[1:] if x != ""])
        
        logging.debug("Executable: "+executable)
        logging.debug("Base arguments: "+base_arguments)
        
        # Theres a prefix, base command and arguments are a single argument
        command_fragments = prefix+ " " + executable+" "+base_arguments
        
        try:
            result = subprocess.run(command_fragments, shell=True)
            if result.returncode != 0:
                print(ColorFormat(Colors.Red, command_fragments+" returned code = "+str(result.returncode)))
            else:
                print(ColorFormat(Colors.Green, command_fragments+" returned code = "+str(result.returncode)))
        except KeyboardInterrupt:
            print("Keyboard Interrupt")

    except Exception as ex:
        print("Error in running the executable\nException caught: "+str(ex))
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(stream = sys.stdout, level = logging.WARNING)
    # Get project repository
    remote_repo_url = getRepoURL()
    
    runProjectExecutable(remote_repo_url)