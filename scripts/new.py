import os
import sys
import json
import logging
from time import time
from colorama import Fore, Style

from common import *
from git import *

logging.basicConfig(stream = sys.stdout, level = logging.DEBUG)

   
# Get remote repository
if len(sys.argv) > 1:
    remote_repo_url = sys.argv[1]
else:
    remote_repo_url = input("Remote repository must already exist, please introduce url: ")

main_repo_name = getRepoName(remote_repo_url)
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
    "scripts"#,
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

print(Fore.GREEN+"""
Repository set up in """+repo_dir+""", verify and commit the changes

Keep in mind that if even 1 source file is listed, a library and a test are automatically generated.
This is imposed behaviour because, if a repository has code that can be included/linked against, it must both belong to some library file, and have tests to validate its' behaviour and exemplify its' usage.
For now, validation isn't automatic.

These are the changes to commit, please insert a commit message (or Ctrl+C to cancel)
( You can always cancel, go to """+repo_dir+""" and adapt these changes to your will )
"""+Style.RESET_ALL)
print(status)
print("Dont use \" in your commit message")
commit_message = input("[commit message >]")

launchVerboseProcess('git commit -m "'+commit_message+'"')
launchVerboseProcess("git push")
