#!/bin/python3

from PB_test_support import *
from PB_test_base_repos import *

"""
New branch test
"""
def Test1(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    RunPB(repo_a.url, "1 2 3 3", branch)
    TestInFile("Built target RepoA_RepoA_Test", PB_out)

    RunPB(repo_a.url, "1 5 4 1", branch)
    TestInFile([
    " | RepoA | master | origin/master",
    " | RepoB | master | origin/master",
    " | RepoD | master | origin/master",
    " | RepoC | master | origin/master"
    ], PB_out)

    # Create new branch and check it out
    RunPB(repo_a.url, "1 5 4 2 Test 4 1", branch)
    TestInFile([
    " | RepoA | Test | origin/Test",
    " | RepoB | Test | origin/Test",
    " | RepoD | Test | origin/Test",
    " | RepoC | Test | origin/Test"
    ], PB_out)

    # Go back to maser
    RunPB(repo_a.url, "1 5 4 2 master 4 1", branch)
    TestInFile([
    " | RepoA | master | origin/master",
    " | RepoB | master | origin/master",
    " | RepoD | master | origin/master",
    " | RepoC | master | origin/master"
    ], PB_out)

"""
Empty merge test
"""
def Test2(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    RunPB(repo_a.url, "1 2 3 3", branch)
    TestInFile("Built target RepoA_RepoA_Test", PB_out)

    RunPB(repo_a.url, "1 5 4 1", branch)
    TestInFile([
    " | RepoA | master | origin/master",
    " | RepoB | master | origin/master",
    " | RepoD | master | origin/master",
    " | RepoC | master | origin/master"
    ], PB_out)

    RunPB(repo_a.url, "1 5 4 2 Test 4 1", branch)
    RunPB(repo_a.url, "1 5 4 1", branch)
    TestInFile([
    " | RepoA | Test | origin/Test",
    " | RepoB | Test | origin/Test",
    " | RepoD | Test | origin/Test",
    " | RepoC | Test | origin/Test"
    ], PB_out)

    RunPB(repo_a.url, "1 5 4 4 ", branch)

"""
Base single change merge
"""
def Test3(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    RunPB(repo_a.url, "1 5 4 2 Test 4 1", branch)
    TestInFile([
    " | RepoA | Test | origin/Test",
    " | RepoB | Test | origin/Test",
    " | RepoD | Test | origin/Test",
    " | RepoC | Test | origin/Test"
    ], PB_out)

    data_to_print = AddPrintToExec(inst_1.GetPBPath(repo_a), 0)

    TestInFile([
    "DIRTY  | RepoA | Test | origin/Test",
    "       | RepoB | Test | origin/Test",
    "       | RepoD | Test | origin/Test",
    "       | RepoC | Test | origin/Test"
    ], PB_out)
    sys.exit(0)


# Test delete branch that was already deleted 9remote and local
tests = [
    Test1,
    Test2,
]

RunTests(tests)
