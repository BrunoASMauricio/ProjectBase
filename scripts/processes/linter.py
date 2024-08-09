


def __CleanLinterFiles(Project):
  if(check_project_json(Project)):
      # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment(Project)
    runClangTidy = "cd " +Project.Paths["project main"]+ "  &&  python ../../scripts/run-clang-tidy.py -use-color -format -style Microsoft -mythmode=clean"
    LaunchVerboseProcess( runClangTidy )
