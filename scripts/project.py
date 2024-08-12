# from repository import *
# from settings import get_active_settings
# from common import *

# """
# Performs operations on a project
# Each project is built from a single repository
# Is represented by a simple dictionary
# """
# class PROJECT(dict):
#     # Load project data
#     def Load(self):
#         # Clean project cache
#         del self.LoadedRepos
#         self.LoadedRepos = {}

#         # Recursive repository generation starting with main
#         self.__LoadRepo(self["ProjectRepoUrl"], self["ProjectRepoBranch"], self["ProjectRepoCommit"])

#     def __LoadRepo(self, Url, Branch, Commit, configs=None):
#         NewRepoId = RepoIdentifier(Url, Branch, Commit, configs)

#         # Already loaded, skip
#         if NewRepoId in self.LoadedRepos.keys():
#             return

#         Repo = REPOSITORY(self, NewRepoId, Url, Branch, Commit)

#         Repo.LoadRepo(configs)

#         self.LoadedRepos[NewRepoId] = Repo

#         for DependencyUrl in Repo["dependencies"]:
#             Dependency = Repo["dependencies"][DependencyUrl]

#             self.__LoadRepo(Dependency["url"], Dependency["branch"], Dependency["commit"], Dependency["configs"])

#     # Create compile_commpands.json file used tor IDES and linting tools
#     def MakeCompileJson(self):
#        compileCommandsStr = "cd " +self.Paths["project main"]+ "  &&  cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 CMakeLists.txt"
#        LaunchVerboseProcess(compileCommandsStr)


#     # Delete project binaries and cached build artifacts

#     def __SetupCMakeLists(self):
#         # Install project wide CMakeLists
#         PresentRepos = {}
#         for RepoId in self.LoadedRepos:
#             Repo = self.LoadedRepos[RepoId]
#             if  Repo.HasFlag("no auto build"):
#                 continue

#             if Repo.HasFlag("independent project"):
#                 # TODO Throw error if CMakeLists.txt does not exist in sub_dire
#                 IncludeEntry = 'add_subdirectory("'+Repo["full_local_path"]+'")'
#             else:
#                 IncludeEntry = 'include("'+Repo["full_local_path"]+'/CMakeLists.txt")'

#             # Do not include duplicates (due to multiple imported)
#             if Repo["full_local_path"] in PresentRepos:
#                 # TODO
#                 # If the duplicate has a different import definition, throw error
#                 #if repo["full_local_path"] != IncludeEntry:
#                 #    logging.fatal("Same repository included with diferring \"independent project\" flag status")
#                 #    logging.fatal(repo["full_local_path"])
#                 #    logging.fatal(IncludeEntry)
#                 #    sys.exit(0)

#                 continue

#             PresentRepos[Repo["full_local_path"]] = IncludeEntry

#         SetupTemplateScript("project/CMakeLists.txt", self.Paths["project main"]+"/CMakeLists.txt", {
#             "INCLUDE_REPOSITORY_CMAKELISTS":'\n'.join(PresentRepos.values())
#         })



