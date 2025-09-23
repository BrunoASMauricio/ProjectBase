from processes.load_fast import get_project_config_from_git_api
from processes.load_fast import get_all_project_dependencies
if __name__ == "__main__":
     #get_all_project_dependencies("https://gitlab.com/p4nth30n/Runtime/Data/treesitter")
     get_all_project_dependencies("https://gitlab.com/p4nth30n/Applications/TestApp")
