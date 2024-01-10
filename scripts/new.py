from colorama import Fore, Style
from time import time
import argparse
import logging
import sys
import os

from common import *
from git import *

if __name__ != "__main__":
    print("This script is not meant to be imported, please run directly")
    sys.stdout.flush()
    sys.exit(-1)

logging.basicConfig(stream = sys.stdout, level = logging.DEBUG)

def parse_arguments():
    # Initialize parser
    parser = argparse.ArgumentParser()

    # Adding optional argument
    parser.add_argument("-u", "--url", help = "Repository to setup", default=None, required=False)

    parser.add_argument("-s", "--simple",
                        help = "Basic setup, only ",
                        default=None, required=False, nargs=1)

    parser.add_argument("-", "--branch",
                        help = "Root repository's branch",
                        default=None, required=False, type=str, nargs=1)

    # Read arguments from command line
    return parser.parse_known_args()

# Get remote repository
if len(sys.argv) > 1:
    remote_repo_url = sys.argv[1]


main_repo_name = getRepoNameFromURL(remote_repo_url)
repo_dir = "/tmp/"+main_repo_name+"_"+str(time())

ret = launchProcess("git clone \""+remote_repo_url+"\" \""+repo_dir+"\"")
if ret["stderr"] != "":
    print(ret["stderr"])

# Setup base structure
repository_structure = [
    "",
    "configs",
    "code/source",
    "code/headers",
    "executables",
    "executables/tests",
]
launchProcess("mkdir -p "+(' '+repo_dir+'/').join(repository_structure))

# Setup empty dependencies
launchProcess('echo "{}" > '+repo_dir+'/configs/configs.json')

# Setup template readme
setupScript("repository/README.md", repo_dir+"/README.md", {"PROJECTNAME":main_repo_name})

setupScript("repository/gitIgnore", repo_dir+"/.gitignore")



# Setup example CMakeLists.txt
setupScript("examples/exampleCustomCMakeLists.txt", repo_dir+"/configs/CMakeLists.txt")

# Setup example main test
setupScript("examples/exampleTest.cpp", repo_dir+"/executables/tests/test.cpp", {"REPOSITORYNAME":main_repo_name})

# Setup example source
setupScript("examples/exampleSource.cpp", repo_dir+"/code/source/exampleSource.cpp", {"REPOSITORYNAME":main_repo_name})

# Setup example header
setupScript("examples/exampleHeader.hpp", repo_dir+"/code/headers/exampleHeader.hpp", {"REPOSITORYNAME":main_repo_name})

os.chdir(repo_dir)

launchVerboseProcess("git add *")
launchVerboseProcess("git add -u")
launchVerboseProcess("git add .gitignore")

status = Git.getStatus(repo_dir)

print(ColorFormat(Colors.Green, """
Repository set up in """+repo_dir+""", verify and commit the changes

Keep in mind that if even 1 source file is listed, a library and a test are automatically generated.
This is imposed behaviour because, if a repository has code that can be included/linked against, it must both belong to some library file, and have tests to validate its' behaviour and exemplify its' usage.
For now, validation isn't automatic.

These are the changes to commit, please insert a commit message (or Ctrl+C to cancel)
( You can always cancel, go to """+repo_dir+""" and adapt these changes to your will )
"""))
print(status)
print("Dont use \" in your commit message")
commit_message = input("[commit message >]")

launchVerboseProcess('git commit -m "'+commit_message+'"')
launchVerboseProcess("git push")
