import os
import logging

from git import *
from common import *
from time import time

def RepoIdentifier(Url, branch, commit, configs):
    return str(Url) + " " + str(branch) + " " + str(commit)+" "+str(configs)
    # Use hash of configs??

"""
Performs operations on a single repository
Is represented by a simple dictionary
"""
class REPOSITORY(dict):
    def Reset(self, Project, NewRepoId, Url, branch, commit):
        key_list = list(self.keys())

        for key in key_list:
            del self[key]

        self.Project = Project
        self.Paths = self.Project.Paths

        self["url"] = Url
        self["id"] = NewRepoId
        self["name"] = GetRepoNameFromURL(Url)
        self["bare_tree_path"] = GetRepoBareTreePath(Url)
        self["branch"] = branch
        self["commit"] = commit

        # Where this repos source can be found
        self["source"] = None

        # Where a .git can be found for this repo
        self["bare path"] = None


    def __init__(self, Project, NewRepoId, Url, Branch=None, Commit=None):
        self.Reset(Project, NewRepoId, Url, Branch, Commit)

    """
    Checks if a given name and value pair exist in the configuration of this repository
    If value is None, just checks if it exists
    """
    def CheckConfig(self, Name, Value = None):
        if Value == None:
            return Name in self.keys()
        return ((Name in self.keys()) and (self[Name] == Value))

    """
    Load and parse a repositories configurations
    """
    def LoadRepo(self, DependentConfigs=None):
        logging.info("Loading repository "+self["name"])

        # Set/Get bare data
        Git.SetupBareData(self.Paths[".gits"], self)

        # Check if repo is present in project structure
        SourcePath = Git.FindGitRepo(self.Paths["project code"], self["url"], self["commit"])

        if SourcePath == None:
            # No source exists, create temporary worktree to extract configs
            TempRepoClone, TempProject_clone = CreateTemporaryRepository(self, DependentConfigs)

            # Relocate repository according to configs in temporary source
            self["source"] = TempRepoClone["source"]
            self.LoadConfigs(DependentConfigs)

            os.makedirs(self["full_local_path"], exist_ok=True)

            Git.addWorktree(self, self["full_local_path"])

            deleteTemporaryRepository(TempRepoClone, TempProject_clone)

            SourcePath = self["full_local_path"]

        # Reload metadata (only keep source)
        self.Reset(self.Project, self["id"], self["url"], self["branch"], self["commit"])
        self["source"] = SourcePath

        self.LoadConfigs(DependentConfigs)

        self.__ParseConfigs(self)

    def Setup(self,):
        print("Setting up repository: "+self["url"])

        self.__SetupCommandList()
        self.__SetupCMakeLists()

    def HasFlag(self, flag):
        if flag in self["flags"]:
            return True
        return False

    def __RunCommandList(self, command_list):
        for command_set_name in command_list:
            command_set = command_list[command_set_name]
            print("Command check: "+str(command_set["condition to proceed"]))

            if ParseProcessResponse(LaunchVerboseProcess(command_set["condition to proceed"])) == "":
                print("Running commands "+str(command_set["command list"]))
                LaunchVerboseProcess("set -xe && "+' && '.join(command_set["command list"]))

    def __SetupCMakeLists(self):
        if self.HasFlag("no auto build"):
           return

        if type(self["headers"]) == type([]):
            DirectoryIncludes = [self["full_local_path"]+'/'+repo for repo in self["headers"]]
        else:
            DirectoryIncludes = [self["full_local_path"]+'/'+self["headers"]]

        LinkLibraries = []

        for RepoId in self.Project.LoadedRepos:
            Url = RepoId.split(" ")[0]
            # Do not self-import
            if Url == self["url"]:
                continue

            Repository = self.Project.LoadedRepos[RepoId]
            if type(Repository["headers"]) == type([]):
                IncludeEntry = ['\t'+Repository["full_local_path"].replace(" ","\ ")+"/"+repo for repo in Repository["headers"]]
                # Do not import twice
                if IncludeEntry in DirectoryIncludes:
                    continue

                if Repository["headers"] != "":
                    DirectoryIncludes += IncludeEntry
            else:
                IncludeEntry = '\t'+Repository["full_local_path"].replace(" ","\ ")+"/"+ Repository["headers"]
                # Do not import twice
                if IncludeEntry in DirectoryIncludes:
                    continue

                if Repository["headers"] != "":
                    DirectoryIncludes.append(IncludeEntry)


            if not Repository.HasFlag("independent project") and not Repository.HasFlag("no auto build"):
                LinkLibraries.append(Repository["name"]+'_lib')

        if self["test_headers"] != "":
            TestHeaders = self["test_headers"].split(",")
            TestHeaders = [self["full_local_path"] + "/" + Header for Header in TestHeaders]
        else:
            TestHeaders = ""


        # Only add repo-wide CMakeLists.txt if one isn't already present
        # The function readlines() reads the file.
        CanDelete = False
        RepoCmakeLists = self["full_local_path"]+"/CMakeLists.txt"
        if os.path.isfile(RepoCmakeLists):
            with open(RepoCmakeLists) as f:
                Content = f.readlines()

            if len(Content) > 0 and "# PROJECTBASE" in Content[0]:
                CanDelete = True

            if CanDelete:
                os.unlink(RepoCmakeLists)

        if not os.path.isfile(RepoCmakeLists):
            SetupTemplateScript("repository/CMakeLists.txt", RepoCmakeLists, {
                    "ADDLIBRARYTYPE": "",
                    "TARGETINCLUDETYPE": "PUBLIC",
                    "INCLUDEREPOSITORYDIRECTORIES": '\n'.join(DirectoryIncludes),
                    "LINKDEPENDENCIES": '\n'.join(LinkLibraries),
                    "TEST_HEADER_INCLUDES": '\n'.join(TestHeaders)
                })

class FAKE_PROJECT(dict):
    def __init__(self, Url, Branch, Commit):

        Name = GetRepoNameFromURL(Url)

        self.Paths = GetProjectPaths(Name)
        self.Paths["project code"] = self.Paths["temporary"] + "/" + Name + ".ProjectBase"

        self.update({
            "ProjectRepoName":    Name,
            "ProjectRepoUrl":     Url,
            "ProjectRepoBranch":  Branch,
            "ProjectRepoCommit":  Commit,
        })
        self.LoadedRepos = {}

# def CreateTemporaryRepository(Repo, DependentConfigs):
#     # Setup temp project
#     Url = Repo["url"]
#     Branch= Repo["branch"]
#     Commit = Repo["commit"]

#     TempProject = FAKE_PROJECT(Url, Branch, Commit)
#     TempRepo = REPOSITORY(TempProject, "dont care", Url, Branch, Commit, )
#     TempRepo.Paths["project code"]
#     #TempRepo.copy(Repo)
#     TempRepo["bare path"] = Repo["bare path"]

#     Git.addWorktree(TempRepo, Repo.Paths["temporary"]+"/"+Repo["name"]+"_"+str(time()))

#     # Load metadata
#     TempRepo.LoadConfigs(DependentConfigs)
#     return TempRepo, TempProject

import shutil

def deleteTemporaryRepository(TempRepo, TempProject):
    # Relocate repository according to metadata
    Git.DelWorktree(TempRepo)
    try:
        shutil.rmtree(TempProject.Paths["project code"])
    except:
        pass

    del TempProject
    del TempRepo
