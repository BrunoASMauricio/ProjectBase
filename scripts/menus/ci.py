from menus.menu import Menu
import subprocess
import tempfile
from pathlib import Path
from data.settings import Settings
import processes.repository as repo
from processes.versioning import getProjectStatusInfo
from processes.process import LaunchProcess
import json

CIMenu = Menu("Ci Menu")

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
    print(f"[CI] Running {label}: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, shell=True)
    if res.returncode != 0:
        print(f"[CI] {label} failed with exit code {res.returncode}")
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
    print(f"[CI] Temporary CI folder kept at {tmp_dir} for inspection (remove manually if desired)")
    if(repo.repositories is None):
        raise ValueError("Repositores are empty, this should only be called after a load")
    
    project_base_repo= Path(Settings["paths"]["project base"])
    print(f"[CI] ProjectBase repo detected at {project_base_repo}")

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
    print(f"[CI] ProjectBase cloned to {clone_path}")

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
        print(f"[CI] Testing {path} Running: {run_cmd}")
        ret = LaunchProcess(" ".join(cmd), clone_path,False)
        if(ret["code"] != 0):
            all_passed = False
            print(f"[CI] Testing Fail {path}")
        
    if(all_passed):
        print("[CI] Scratch CI run completed successfully!")
        return 0
    else:
        print("[CI] Scratch CI Failed!")
        return 1



CIMenu.AddCallbackEntry("Run CI For Top Project", lambda: RunCIScratch(RunCIType.TOP))
CIMenu.AddCallbackEntry("Run CI For All ahead Repositories (inclusive top)",lambda: RunCIScratch(RunCIType.AheadRepos))
CIMenu.AddCallbackEntry("Run CI For All Repositories (inclusive ahead and top)", lambda: RunCIScratch(RunCIType.AllRepos))
