#!/bin/python3

"""
Create test repos for PB development
"""

from PB_test_support import *
from PB_test_base_repos import *

def CreateTestRepos(branch):
    repos = CreateBaseRepos()
    for repo in repos:
        print(f"Created repository: {repo.name} in {repo.bare_path} with a url of {repo.url}")

RunTests([CreateTestRepos])
