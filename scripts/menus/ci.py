from menus.menu import Menu
import subprocess
import tempfile
from pathlib import Path
from data.settings import Settings
import processes.repository as repo
from processes.versioning import getProjectStatusInfo
from processes.process import LaunchProcess
from processes.process import ProcessError
import json
import logging

CIMenu = Menu("Ci Menu")
def logging_and_print(message, isError = False):
    if(isError):
        logging.error(message)
    else:
        logging.info(message)
    print(message)


def create_content_for_worktree_json(work_tree_path : Path):
    # This function creates a json file with a dictionary mapping
    # uid of projects ahead to their wortree on the local path
    #map_uid_to_source_worktree_of_commited_repos = {}
    map_uid_source: dict[str,str] = {}
    knownProjStat, unknownProjStat = getProjectStatusInfo()
    # This are the uid that must be on the path
    for ahead in knownProjStat.ahead_id:
        ahead_info = repo.repositories[ahead]
        ahead_source =  ahead_info['repo source']
        map_uid_source[ahead] = ahead_source
    
    with open(work_tree_path, "w", encoding="utf-8") as f:
        json.dump(map_uid_source, f, indent=2, sort_keys=True)

    return map_uid_source

def run_cmd(cmd, cwd, label):
    message = f"[CI] Running {label}: {' '.join(cmd)}"
    logging_and_print(message)
    res = subprocess.run(cmd, cwd=cwd, shell=True)
    if res.returncode != 0:
        message = f"[CI] {label} failed with exit code {res.returncode}"
        logging_and_print(message,isError=True)
    return res.returncode


from dataclasses import dataclass
@dataclass
class ProjectCIInfo:
    pb_temp_path: Path
    worktree_file: Path
    top_project_worktree_local: str 
    top_project_uid : str
    ahead_repos_uid : dict[str,str]  # for ahead repos key: uid, value: global path of worktree

def SetupCI() -> ProjectCIInfo:
    """
    Run a CI scratch environment:
    - Create a temporary folder
    - Clone the ProjectBase repo into it
    - Generate worktreeFile.json 
    """
    tmp_dir = tempfile.mkdtemp(prefix="ci_scratch_")
    message = f"[CI] Temporary CI folder kept at {tmp_dir} for inspection (remove manually if desired)"
    logging_and_print(message)
    if(repo.repositories is None):
        raise ValueError("Repositores are empty, this should only be called after a load")
    
    project_base_repo= Path(Settings["paths"]["project base"])
    
    # 2. Get parameters to call CI
    project_name: str = Settings["ProjectName"]
    project_folder: str = "projects/" + project_name + ".ProjectBase"
    root_url = "root_url.txt"
    project_root = project_base_repo / project_folder / root_url
    with open(project_root) as f:
        project_top_uid = f.read()
    project_top_uid = repo.url_SSH_to_HTTPS(project_top_uid)
    project_top_info = repo.repositories[project_top_uid]
    project_worktree_source: str =  project_top_info['repo source']

        

    # 3. Clone ProjectBase into the temporary folder
    clone_path = Path(tmp_dir) / "ProjectBase"
    subprocess.run(["git", "clone", str(project_base_repo), str(clone_path)], check=True)

    worktree_json_path = Path(tmp_dir) / "worktreeFile.json"
    ahead_repos_uid = create_content_for_worktree_json(worktree_json_path)

    # if top project has changes do not use the url toot, but use locar worktree when running CI

    return ProjectCIInfo( pb_temp_path=clone_path, 
                          worktree_file= worktree_json_path, 
                          top_project_worktree_local=project_worktree_source,
                          top_project_uid = project_top_uid,
                          ahead_repos_uid =ahead_repos_uid)

from enum import Enum
class RunCIType(Enum):
    TOP = 1
    AheadRepos = 2
    AllRepos = 3

def resolve_path(repo_uid : str, pinfo : ProjectCIInfo ) -> str:
    # If top modified use local sourcetree else use uid from remote
    if repo_uid == pinfo.top_project_uid:
        return pinfo.top_project_worktree_local if pinfo.top_project_uid in pinfo.ahead_repos_uid else pinfo.top_project_uid
    else:
        if(repo_uid in pinfo.ahead_repos_uid):
            return pinfo.ahead_repos_uid[repo_uid]
        else:
            return repo_uid
    
from tqdm import tqdm
def RunCIScratch(runCiType : RunCIType):
    """
    Run a CI scratch environment:
    - Setup CI
    - Run load/pull/build/test commands using local project as root
    """
    # 1 - SetupCI
    p = SetupCI()
    worktree_json_path = p.worktree_file
    top_uid = p.top_project_uid
    clone_path = p.pb_temp_path

    paths_to_run: list[str] = []

    if(runCiType == RunCIType.TOP):
        paths_to_run.append(resolve_path(top_uid, p))
    
    if(runCiType == RunCIType.AheadRepos):
        for repo_uid in p.ahead_repos_uid:
            paths_to_run.append(resolve_path(repo_uid, p))

    if(runCiType == RunCIType.AllRepos):
        for repo_uid in repo.repositories:
            paths_to_run.append(resolve_path(repo_uid, p))

    all_passed = True
    for path in tqdm(paths_to_run, desc="Running CI", unit="repo"):
        # 5. Run CI commands

        # TODO DOing like this the repositories are used for the entire run the same 
        # Projectbase what probably is better less time cloning but for now is breaking 
        # for isntances: 
        #ricostynha@nobara-pc:/tmp/ci_scratch_qubc2ltb/ProjectBase$ ./run.sh 
        #Installed projects:
        #        [0] Scheduler : /home/ricostynha/Desktop/myth/ProjectBase/projects/textformatter.ProjectBase/code/Core/Scheduler
        #        [1] tree-sitter : /home/ricostynha/Desktop/myth/ProjectBase/projects/textformatter.ProjectBase/code/External/Libraries/tree-sitter
        #        [2] keyboard : /home/ricostynha/Desktop/myth/ProjectBase/projects/textformatter.ProjectBase/code/Application/keyboard
        # Tree sitter that was the first to be created works great the others the load fails like so
        #72 unloaded dependencies found
        #Finished dependency round
        #74 unloaded dependencies found
        #Starting... |---Process returned failure (128):----------------------------------------------------------------------------------------------| 0.0% 0/2
        #at /tmp/ci_scratch_qubc2ltb/ProjectBase/configs/bare_gits/gitlab.com/p4nth30n/Core/Scheduler.git
        #set -e; export PYTHONPATH='/tmp/ci_scratch_qubc2ltb/ProjectBase/scripts'; export PB_ROOT_NAME='keyboard'; git worktree move /tmp/ci_scratch_qubc2ltb/ProjectBase/configs/temporary/ZseJAnaVtYXI/Scheduler /tmp/ci_scratch_qubc2ltb/ProjectBase/projects/keyboard.ProjectBase/code/Core
        #stdout: 
        #stderr: fatal: '/tmp/ci_scratch_qubc2ltb/ProjectBase/projects/keyboard.ProjectBase/code/Core/Scheduler' already exists

        cmd = [
                "source",
                "./setup.sh",
                ";",
                "./run.sh",
                "--commitJsonPath", str(worktree_json_path),
                "--url", str(path),
                "--log_file", "/tmp/project_base_ci_error.log",
                "--out_file", "/tmp/project_base_ci_out.log",
                "1","5", "3", "1","out","1","2","3","3","-e"
            ]
        # Steps
        # 1 Load
        # 5 Versioning
        # 3 Sync
        # 1 Pull data from remote

        # - 1 go previous menu
        # 1 Load (some config could have changed)
        # 2 Build
        # 3 Run
        # 3 Run all tests
        run_cmd = ' '.join(cmd)
        message = f"[CI] Testing {path} Running: {run_cmd}"
        logging_and_print(message)
        try:
            ret = LaunchProcess(" ".join(cmd), clone_path,False)
            #retcode = int(ret["code"])
        except ProcessError as p:
            #simple_message, trace_message, returned = p.args
            #retcode = int(returned)
            all_passed = False
            message = f"[CI] Test Failed : {path}"
            logging_and_print(message, isError=True)

    if(all_passed):
        message = "[CI] Scratch CI run completed successfully!"
        logging_and_print(message)
    else:
        Settings.return_code = 1
        message = "[CI] Scratch CI run Failed!"
        logging_and_print(message, isError=True)



CIMenu.AddCallbackEntry("Run CI For Top Project", lambda: RunCIScratch(RunCIType.TOP))
CIMenu.AddCallbackEntry("Run CI For All ahead Repositories (inclusive top)",lambda: RunCIScratch(RunCIType.AheadRepos))
CIMenu.AddCallbackEntry("Run CI For All Repositories (inclusive ahead and top)", lambda: RunCIScratch(RunCIType.AllRepos))
