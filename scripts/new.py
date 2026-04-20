"""
new.py – Interactive repository creation for ProjectBase.

Call CreateNewRepository() from a menu entry or directly.
"""

import os
import sys
import logging

from data.settings import Settings
from data.common import SetupTemplate
from data.git import GetRepoNameFromURL
from processes.filesystem import CreateDirectory
from data.json import dump_json_file
from data.print import PrintInfo, PrintError, PrintWarning
from data.settings import UserPromptConfirm
from processes.git_operations import ParseGitResult


def CreateNewRepository():
    """
    Interactive flow to create a new repository skeleton and push it.
    Asks for repo name, initial directory, whether to add a README, and
    whether to add example source files.
    """
    print("=== Create New Repository ===\n")

    # Ask for repo name
    try:
        repo_name = input("Repository name: ").strip()
    except EOFError:
        PrintWarning("Cancelled.")
        return
    if not repo_name:
        PrintError("Repository name cannot be empty.")
        return

    # Ask for initial/target directory
    default_dir = os.path.join(Settings["paths"]["project code"], repo_name)
    try:
        repo_dir = input(f"Directory to create repository in [{default_dir}]: ").strip()
    except EOFError:
        PrintWarning("Cancelled.")
        return
    if not repo_dir:
        repo_dir = default_dir

    # Ask whether to add README
    add_readme = UserPromptConfirm("Add a default README?")

    # Ask whether to add example source files
    add_example = UserPromptConfirm("Add example source/header/test files?")

    # Create directory structure
    subdirs = [
        "",
        "configs",
        "code/source",
        "code/headers",
        "executables",
        "executables/tests",
    ]
    for sub in subdirs:
        target = os.path.join(repo_dir, sub)
        CreateDirectory(target)
        logging.debug(f"Created directory: {target}")

    # Write empty configs.json
    configs_json_path = os.path.join(repo_dir, "configs", "configs.json")
    dump_json_file({}, configs_json_path)

    # Write .gitignore from template if available
    try:
        SetupTemplate("repository/gitIgnore", os.path.join(repo_dir, ".gitignore"), {})
    except FileNotFoundError:
        pass

    # Optionally add README
    if add_readme:
        try:
            SetupTemplate(
                "repository/README.md",
                os.path.join(repo_dir, "README.md"),
                {"PROJECTNAME": repo_name},
            )
        except FileNotFoundError:
            # Fallback: write minimal README
            with open(os.path.join(repo_dir, "README.md"), "w") as f:
                f.write(f"# {repo_name}\n")

    # Optionally add example files
    if add_example:
        vars_ = {"REPOSITORYNAME": repo_name}
        example_map = {
            "examples/exampleCustomCMakeLists.txt": "configs/CMakeLists.txt",
            "examples/exampleTest.cpp":             "executables/tests/test.cpp",
            "examples/exampleSource.cpp":           "code/source/exampleSource.cpp",
            "examples/exampleHeader.hpp":           "code/headers/exampleHeader.hpp",
        }
        for tmpl, dest in example_map.items():
            try:
                SetupTemplate(tmpl, os.path.join(repo_dir, dest), vars_)
            except FileNotFoundError:
                logging.warning(f"Template {tmpl} not found, skipping.")

    PrintInfo(f"\nRepository skeleton created at: {repo_dir}")

    # Git init + initial commit + push
    if UserPromptConfirm("Initialise a git repository and commit the files?"):
        ParseGitResult("git init", repo_dir)
        ParseGitResult("git add -A", repo_dir)
        try:
            commit_msg = input("[commit message]: ").strip()
        except EOFError:
            commit_msg = f"Initial commit for {repo_name}"
        if not commit_msg:
            commit_msg = f"Initial commit for {repo_name}"
        ParseGitResult(f'git commit -m "{commit_msg}"', repo_dir)

        if UserPromptConfirm("Push to remote?", default_no=True):
            ParseGitResult("git push", repo_dir)

    PrintInfo("Done.")
