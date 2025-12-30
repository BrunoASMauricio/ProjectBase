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



def RunCIScratch():
    """
    Run a CI scratch environment:
    - Create a temporary folder
    - Clone the ProjectBase repo into it
    - Generate worktreeFile.json (placeholder)
    - Run load/build/test commands
    """
    # 1. Create a temporary directory
    tmp_dir = tempfile.mkdtemp(prefix="ci_scratch_")
    print(f"[CI] Temporary CI folder created at {tmp_dir}")

    if(repo.repositories is None):
        raise ValueError("Repositores are empty, this should only be called after a load")
    
    project_base_path = Path(Settings["paths"]["project base"])
    project_name = Settings["ProjectName"]
    project_top_uid = str(project_base_path.parent / project_name)
    project_top_info = repo.repositories[project_top_uid]
    project_worktree_source =  project_top_info['repo source']
        
    # 2. Determine the path of ProjectBase repo (relative to this script)
    current_script_path = Path(__file__).resolve()
    projectbase_root = current_script_path.parents[2]  # ProjectBase/scripts/menus/ci.py -> ../../.. = ProjectBase
    projectbase_repo = projectbase_root

    print(f"[CI] ProjectBase repo detected at {projectbase_repo}")

    # 3. Clone ProjectBase into the temporary folder
    clone_path = Path(tmp_dir) / "ProjectBase"
    subprocess.run(["git", "clone", str(projectbase_repo), str(clone_path)], check=True)
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
    print(f"[CI] Running load/pull command: {' '.join(cmd1)}")
    subprocess.run(cmd1, check=True, cwd=clone_path)

    # Command 2: build and run all tests
    cmd2 = [
            "./run.sh",
            "--commitJsonPath", str(worktree_json_path),
            "--url", str(system_textformatter_path),
            "1","2", "3", "3", "-e"
        ]

    print(f"[CI] Running build/test command: {' '.join(cmd2)}")
    subprocess.run(cmd2, check=True, cwd=clone_path)

    print("[CI] Scratch CI run completed successfully!")
    print(f"[CI] Temporary folder kept at {tmp_dir} for inspection (remove manually if desired)")




CIMenu.AddCallbackEntry("Run CI From blank state", RunCIScratch)
