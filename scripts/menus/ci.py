from menus.menu import Menu
import subprocess
import tempfile
from pathlib import Path

CIMenu = Menu("Ci Menu")

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

    try:
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
        print(f"[CI] Placeholder for generating worktree JSON at {worktree_json_path}")
        # TODO: your code to generate worktreeFile.json
        worktree_json_path.write_text("{}")  # empty JSON for now

        # 5. Run CI commands
        # Adjust the paths according to your local setup
        system_textformatter_path = projectbase_root / "projects/textformatter.ProjectBase/code/Systems/textformatter"

        # Command 1: clean load + pull
        cmd1 = [
            "./run.sh",
            "--commitJsonPath", str(worktree_json_path),
            "--url", str(system_textformatter_path),
            "5", "3", "1","-e"
        ]
        print(f"[CI] Running load/pull command: {' '.join(cmd1)}")
        subprocess.run(cmd1, check=True, cwd=clone_path)

        # Command 2: build and run all tests
        cmd2 = [
            "./run.sh",
            "--commitJsonPath", str(worktree_json_path),
            "--url", str(system_textformatter_path),
            "2", "3", "3", "-e"
        ]

        print(f"[CI] Running build/test command: {' '.join(cmd2)}")
        subprocess.run(cmd2, check=True, cwd=clone_path)

        print("[CI] Scratch CI run completed successfully!")

    except subprocess.CalledProcessError as e:
        print(f"[CI] Command failed: {e}")
    finally:
        # Optionally clean up temporary folder
        # shutil.rmtree(tmp_dir)
        print(f"[CI] Temporary folder kept at {tmp_dir} for inspection (remove manually if desired)")




CIMenu.AddCallbackEntry("Run CI From blank state", RunCIScratch)
