# Faster load strategy different 

# First go get on all files the configs.json directly from gitlab API
# (proably after expand)

# Call on all repo paths the clone as it was 


import os
import re
import json 

from data.print import *
from processes.process import LaunchProcess


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

from urllib.parse import quote



def _get_api_url_and_auth(project_path: str, branch: str = "main") -> Tuple[str, str]:
    """Determines the API URL and curl header based on the host."""
    
    project_path_normalized = normalize_project_path(project_path) 

    project_enc = quote(project_path_normalized, safe="")
    file_path_enc = quote("configs/configs.json", safe="")
    branch_enc = quote(branch, safe="")


    # Configuration file path within the repository
    config_file_path = "configs/configs.json"

    if "gitlab" in project_path:
        # Construct API raw URL
        gitlab_token = os.environ.get("GITLAB_TOKEN")
        if not gitlab_token:
            raise RuntimeError(
                "GitLab token not defined. Please set the environment variable GITLAB_TOKEN."
            )
    
        url = (
            f"https://gitlab.com/api/v4/projects/{project_enc}"
            f"/repository/files/{file_path_enc}/raw?ref={branch_enc}"
        )
        auth_header = f'--header "PRIVATE-TOKEN: $GITLAB_TOKEN"'
        return url, auth_header
        
    elif "github" in project_path:
        # GitHub API uses owner/repo structure and file content API
        # We assume the normalized path is 'owner/repo'
        url = f"https://api.github.com/repos/{repo_path}/contents/{config_file_path}?ref={branch}"
        # GitHub uses Authorization header from $GITHUB_TOKEN
        auth_header = f'--header "Authorization: token $GITHUB_TOKEN"'
        return url, auth_header

    raise ValueError(f"Unsupported Git host in path: {project_path_normalized}")

def get_project_config_from_git_api(project_path, branch="main"):
    """
    Fetch configs/configs.json for `project_path` via Git API (GitLab/GitHub).
    """
    tmp = tempfile.NamedTemporaryFile(prefix="cfg_", suffix=".json", delete=False)
    output_file = tmp.name
    tmp.close()

    try:
        url, auth_header = _get_api_url_and_auth(project_path, branch)

        # Build and run curl
        command = f'curl -sS -L {auth_header} "{url}" --output "{output_file}"'
        LaunchProcess(command)

        # Load JSON (GitHub API returns file content base64 encoded, GitLab returns raw)
        data = {}
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                raw_content = f.read()
            
            if "github" in url.lower() and '"content"' in raw_content:
                # GitHub JSON response needs decoding
                github_api_data = json.loads(raw_content)
                base64_content = github_api_data.get("content", "")
                decoded_content = base64.b64decode(base64_content).decode("utf-8")
                data = json.loads(decoded_content)
            else:
                # GitLab (or raw content direct from GitHub's redirect)
                data = json.loads(raw_content)

        except Exception as e:
            # helpful debug output
            PrintError(f"Failed to process API response for {project_path!r}: {e} {url}\n{command}")
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
    while queue:
        proj = queue.pop(0)  # FIFO; change to pop() for DFS
        if proj in checked_dependencies:
            continue
        try:
            data = get_project_config_from_git_api(proj)
        except Exception as e:
            # Print and skip this project on failure
            PrintError(f"Error fetching config for '{proj}': {e}")
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
    PrintInfo(f"Checked dependencies {len(checked_dependencies)} \n{checked_dependencies}")
    return checked_dependencies, queue


import concurrent.futures
import threading
from typing import List, Tuple, Set
import queue


def get_all_project_dependencies(project_path, checked_dependencies=None, to_check_dependencies=None, max_workers=15):
    """
    Parallel version that uses API calls to discover and gather configurations 
    for the entire dependency graph.

    Returns:
        List[Tuple[str, dict]]: List of (project_path, config_data) for all discovered projects.
    """
    if checked_dependencies is None:
        checked_dependencies = []
    if to_check_dependencies is None:
        to_check_dependencies = []

    queue = [project_path] + list(to_check_dependencies)
    visited = set(queue)
    
    # Store results: {project_path: config_data}
    repo_configs = {}
    
    while queue:
        current_batch = queue
        queue = []
        
        # Ensure thread safety for shared data if necessary, 
        # but for this logic, each thread only returns its results.
        
        def process_project(proj):
            # The result will be (project_path, config_data, new_dependency_configs)
            if proj in repo_configs or proj in checked_dependencies: # Use repo_configs as main check
                return None, None, [] 
            
            data = get_project_config_from_git_api(proj)
                
                # Extract all dependency config dicts from the found data
            new_dependency_configs = extract_dependencies_from_json(data)

                # Append to checked list (note: this list is no longer strictly necessary 
                # if we use repo_configs and visited)
            checked_dependencies.append(proj) 
                
            return proj, data, new_dependency_configs
                
        
        # Process batch in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # We map the function to the current batch of project paths
            results = list(executor.map(process_project, current_batch))
            
            # Collect results and new dependencies
            for proj, config_data, new_dependency_configs in results:
                if proj and config_data is not None:
                    # 1. Store the found configuration data
                    repo_configs[proj] = config_data
                
                # 2. Collect paths of *new* dependencies to queue for the next batch
                for dep_config in new_dependency_configs:
                    # We assume 'url' is the path we need to normalize and check against 'visited'
                    dep_path = dep_config.get("url")
                    if dep_path and dep_path not in visited:
                        visited.add(dep_path)
                        queue.append(dep_path) # Queue the path for the next API call
    
    # Convert the results dictionary back into the required list format
    final_results = [
        (path, config) for path, config in repo_configs.items()
    ]

    print("Checked dependencies")
    print(len(final_results))
    return final_results # Returns List of (path, config_data)