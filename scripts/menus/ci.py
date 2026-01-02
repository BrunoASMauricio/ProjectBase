from menus.menu import Menu
import subprocess
import tempfile
from pathlib import Path
from data.settings import Settings
import processes.repository as repo
from processes.versioning import getProjectStatusInfo
import json

CIMenu = Menu("Ci Menu")

def create_content_for_worktree_json(work_tree_path : Path):

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

def run_cmd(cmd, cwd, label):
    print(f"[CI] Running {label}: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd)
    if res.returncode != 0:
        print(f"[CI] {label} failed with exit code {res.returncode}")
    return res.returncode

def RunCIScratch():
    """
    Run a CI scratch environment:
    - Create a temporary folder
    - Clone the ProjectBase repo into it
    - Generate worktreeFile.json 
    - Run load/pull/build/test commands using local project as root
    """
    # 1. Create a temporary directory
    tmp_dir = tempfile.mkdtemp(prefix="ci_scratch_")
    print(f"[CI] Temporary CI folder kept at {tmp_dir} for inspection (remove manually if desired)")
    if(repo.repositories is None):
        raise ValueError("Repositores are empty, this should only be called after a load")
    
    project_base_repo= Path(Settings["paths"]["project base"])
    print(f"[CI] ProjectBase repo detected at {projectbase_repo}")

    project_name: str = Settings["ProjectName"]
    project_folder: str = "projects/" + project_name + ".ProjectBase"
    root_url = "root_url.txt"
    project_root = project_base_repo / project_folder / root_url
    with open(project_root) as f:
        project_top_uid = f.read()
    project_top_uid = repo.url_SSH_to_HTTPS(project_top_uid)
    project_top_info = repo.repositories[project_top_uid]
    project_worktree_source =  project_top_info['repo source']
        

    # 3. Clone ProjectBase into the temporary folder
    clone_path = Path(tmp_dir) / "ProjectBase"
    subprocess.run(["git", "clone", str(project_base_repo), str(clone_path)], check=True)
    print(f"[CI] ProjectBase cloned to {clone_path}")

    # 4. Generate worktreeFile.json (placeholder)
    worktree_json_path = Path(tmp_dir) / "worktreeFile.json"
    create_content_for_worktree_json(worktree_json_path)
    print(f"[CI] Mapper from url to projects with commit sources on file {worktree_json_path}")

    # 5. Run CI commands
    # Adjust the paths according to your local setup
    system_textformatter_path = project_worktree_source

    # Command 1: clean load + pull   
    cmd1 = [
            "./run.sh",
            "--commitJsonPath", str(worktree_json_path),
            "--url", str(system_textformatter_path),
            "1","5", "3", "1","-e"
        ]
    
    if run_cmd(cmd1, clone_path, "load/pull") != 0:
        return 1

    # Command 2: build and run all tests
    cmd2 = [
            "./run.sh",
            "--commitJsonPath", str(worktree_json_path),
            "--url", str(system_textformatter_path),
            "1","2", "3", "3", "-e"
        ]
    
    if run_cmd(cmd2, clone_path, "build/test") != 0:
        return 2
   
    print("[CI] Scratch CI run completed successfully!")
    return 0




CIMenu.AddCallbackEntry("Run CI From blank state", RunCIScratch)
