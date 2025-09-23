# Faster load strategy different 

# First go get on all files the configs.json directly from gitlab API
# (proably after expand)

# Call on all repo paths the clone as it was 


import os
import glob
import json 

from processes.process        import LaunchProcess

import re
import urllib.parse

def normalize_project_path(project_input: str) -> str:
    """
    Normalize an input (URL, SSH, or plain path) to a plain project path string:
      "namespace/subgroup/.../project"

    Examples accepted:
      - "https://gitlab.com/p4nth30n/Runtime/Standard/Standard"
      - "https://gitlab.com/p4nth30n/Applications/AdminConsole/-/blob/main/configs/config.json"
      - "git@gitlab.com:p4nth30n/Runtime/Standard/Standard.git"
      - "p4nth30n/Runtime/Standard/Standard"
    """
    s = project_input.strip()

    # remove trailing .git
    if s.endswith(".git"):
        s = s[:-4]

    # SSH form: git@host:group/project or ssh://git@host/group/project
    m = re.match(r'^(?:git@|ssh://git@)([^:/]+)[:/](.+)$', s)
    if m:
        path = m.group(2).lstrip('/')
        plain = path.rstrip('/')
        return plain

    # HTTP(S) form
    m = re.match(r'^(?:https?://)([^/]+)(?:/|$)(.+)$', s)
    if m:
        path = m.group(2)
        # Remove UI fragments like "/-/" and UI paths like /blob/... /raw/... /tree/...
        path = path.split('/-/')[0]
        path = re.sub(r'/(?:blob|raw|tree)/.*$', '', path)
        plain = path.strip('/')
        return plain

    # Otherwise assume it's already a plain path like "namespace/project"
    return s.strip('/')


def extract_dependencies_from_json(data_json):
    dependencies_paths = []
    api_paths = []
    if("dependencies" in data_json):
        dependencies_paths = list(data_json["dependencies"].keys())
    if("API" in data_json):
        api_paths = list(data_json["API"].keys())
    return dependencies_paths + api_paths

import tempfile
def get_project_config_from_git_api(project_path, branch="main"):
    """
    Fetch configs/configs.json for `project_path` via GitLab API into a unique temp file,
    load the JSON and remove the temp file before returning the parsed data (or {} on failure).
    """
    # create a unique temporary filename (file closed so curl can write to it)
    tmp = tempfile.NamedTemporaryFile(prefix="cfg_", suffix=".json", delete=False)
    output_file = tmp.name
    tmp.close()

    try:
        # normalize and build API URL
        project_path_normalized = normalize_project_path(project_path)
        project_path_2f = "%2F".join(project_path_normalized.split("/"))
        url = f"https://gitlab.com/api/v4/projects/{project_path_2f}/repository/files/configs%2Fconfigs.json/raw?ref={branch}"

        # build and run curl (uses $GITLAB_TOKEN from env)
        command = f'curl -sS -L --header "PRIVATE-TOKEN: $GITLAB_TOKEN" "{url}" --output "{output_file}"'
        LaunchProcess(command)

        # load JSON
        data = {}
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            # helpful debug output
            print(url)
            print(command)
            print(f"Failed to load configs.json for {project_path!r}: {e}")
            data = {}

        return data

    finally:
        # always try to remove the temporary file
        if os.path.exists(output_file):
                os.remove(output_file)


def get_all_project_dependencies_single_threaded(project_path, checked_dependencies=None, to_check_dependencies=None):
    if checked_dependencies is None:
        checked_dependencies = []
    if to_check_dependencies is None:
        to_check_dependencies = []

    # initialize queue with the requested project and any extra to_check entries
    queue = [project_path] + list(to_check_dependencies)
    print(queue)
    while queue:
        proj = queue.pop(0)  # FIFO; change to pop() for DFS
        if proj in checked_dependencies:
            continue
        try:
            data = get_project_config_from_git_api(proj)
        except Exception as e:
            # Print and skip this project on failure
            print(f"Error fetching config for '{proj}': {e}")
            checked_dependencies.append(proj)
            continue

        # extract dependency paths from the project's config
        deps = extract_dependencies_from_json(data)

        # mark this project as checked
        checked_dependencies.append(proj)

        # enqueue new dependencies (avoid duplicates and already-checked)
        for d in deps:
            if d not in checked_dependencies and d not in queue:
                queue.append(d)

    # queue here is the remaining to-check (should normally be empty)
    print("Checked dependencies")
    print(checked_dependencies)
    print(len(checked_dependencies))
    return checked_dependencies, queue


import concurrent.futures
import threading
from typing import List, Tuple, Set
import queue


def get_all_project_dependencies(project_path, checked_dependencies=None, to_check_dependencies=None, max_workers=15):
    """
    Simpler parallel version that only parallelizes the API calls
    """
    if checked_dependencies is None:
        checked_dependencies = []
    if to_check_dependencies is None:
        to_check_dependencies = []

    queue = [project_path] + list(to_check_dependencies)
    visited = set(queue)
    
    while queue:
        # Process current batch of projects in parallel
        current_batch = queue
        queue = []
        
        def process_project(proj):
            if proj in checked_dependencies:
                return []
            try:
                data = get_project_config_from_git_api(proj)
                deps = extract_dependencies_from_json(data)
                checked_dependencies.append(proj)
                return deps
            except Exception as e:
                print(f"Error fetching config for '{proj}': {e}")
                checked_dependencies.append(proj)
                return []
        
        # Process batch in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_project, current_batch))
            
            # Collect new dependencies
            for deps in results:
                for d in deps:
                    if d not in visited:
                        visited.add(d)
                        queue.append(d)
    
    print("Checked dependencies")
    print(checked_dependencies)
    print(len(checked_dependencies))
    return checked_dependencies