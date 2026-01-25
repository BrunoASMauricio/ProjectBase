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
    " | RepoA | master | master",
    " | RepoB | master | master",
    " | RepoD | master | master",
    " | RepoC | master | master"
    ], PB_out)

    # Create new branch and check it out
    RunPB(repo_a.url, "1 5 4 4 Test 4 1", branch)
    TestInFile([
    " | RepoA | Test  | Test",
    " | RepoB | Test  | Test",
    " | RepoD | Test  | Test",
    " | RepoC | Test  | Test"
    ], PB_out)

    # Go back to maser
    RunPB(repo_a.url, "1 5 4 4 master 4 1", branch)
    TestInFile([
    " | RepoA | master | master",
    " | RepoB | master | master",
    " | RepoD | master | master",
    " | RepoC | master | master"
    ], PB_out)

"""
Empty merge test
"""
def Test2(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    # Setup repos and run test for sanity
    RunPB(repo_a.url, "1 2 3 3", branch)
    TestInFile("Built target RepoA_RepoA_Test", PB_out)

    # Create new branch and validate it exists
    RunPB(repo_a.url, "1 5 4 4 Test 4 1", branch)
    TestInFile([
    " | RepoA | Test  | Test",
    " | RepoB | Test  | Test",
    " | RepoD | Test  | Test",
    " | RepoC | Test  | Test"
    ], PB_out)
    # Merge branch
    RunPB(repo_a.url, "1 2 5 4 5 2", branch)
    TestInFile("merge with branch master completed with success", PB_out)
    TestNotInFile("There was an issue", PB_out)


"""
Create and switch to branch A
Create and switch to branch B
Go back to A.
Validate A isnt created again
"""
def Test3(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    # Setup repos and run test for sanity
    RunPB(repo_a.url, "1 2 3 3", branch)
    TestInFile("Built target RepoA_RepoA_Test", PB_out)

    # Create new branch and validate it exists
    RunPB(repo_a.url, "1 5 4 4 Test 4 1", branch)
    TestInFile([
    " | RepoA | Test  | Test",
    " | RepoB | Test  | Test",
    " | RepoD | Test  | Test",
    " | RepoC | Test  | Test",
    "Creating local branch Test"
    ], PB_out)

    # Create another branch and validate it exists
    RunPB(repo_a.url, "1 5 4 4 Test2 4 1", branch)
    TestInFile([
    " | RepoA | Test2 | Test2",
    " | RepoB | Test2 | Test2",
    " | RepoD | Test2 | Test2",
    " | RepoC | Test2 | Test2",
    "Creating local branch Test2"
    ], PB_out)

    # Switch branch
    RunPB(repo_a.url, "1 5 4 4 Test 4 1", branch)
    TestInFile([
    " | RepoA | Test  | Test",
    " | RepoB | Test  | Test",
    " | RepoD | Test  | Test",
    " | RepoC | Test  | Test"
    ], PB_out)
    # Nothing is created
    TestNotInFile("Creating local branch Test", PB_out)

"""
Create and switch to branch A
Try to delete branch A (expect failure)
Change to master
Successfully delete branch A
"""
def Test4(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    # Setup repos and run test for sanity
    # Create new branch and validate it exists
    RunPB(repo_a.url, "1 2 3 3 5 4 4 Test", branch)
    TestInFile([
    "Built target RepoA_RepoA_Test",
    "Creating local branch Test"
    ], PB_out)

    # Attempt to delete currently checked out branch (expect failure)
    RunPB(repo_a.url, "1 2 5 4 7 1", branch)
    TestInFile("Cannot delete. Please check out a different branch and then retry", PB_out)

    # Change to master
    RunPB(repo_a.url, "1 2 5 4 3 2", branch)

    # Attempt to delete again
    RunPB(repo_a.url, "1 2 5 4 7 1", branch)
    TestInFile("Deleted local branch (PB generated branch): Test", PB_out)

"""
Check a remote branch does not exist
Create a local branch and push it
Check it now exists remotely
Delete branch locally
Check it still exists remotely
Delete branch remotely
Check it does not exist remotely
"""
def _Test5(branch, push):
    repo_a, _, _, _ = CreateBaseRepos()

    # Create branch, print branches, check it wasnt pushed
    RunPB(repo_a.url, "1 2 3 3 5 4 4 Test 4 2", branch)
    TestInFile([
    "Built target RepoA_RepoA_Test",
    "Creating local branch Test",

    "==== Checkedout branches ====",
    "Test: RepoA, RepoB, RepoC, RepoD",
    "==== Local branches ====",
    "Test: RepoA, RepoB, RepoC, RepoD",
    "master: RepoA, RepoB, RepoC, RepoD",
    "==== Remote/Tracked branches ====",
    "origin/Test: RepoA, RepoB, RepoC, RepoD",
    "origin/master: RepoA, RepoB, RepoC, RepoD",
    "==== Non pushed branches ====",
    "These branches require a push to be properly set remotely",
    "Test: RepoA, RepoB, RepoC, RepoD",
    ], PB_out)
    # Test with pushing the branches to the remote and without
    # Result should be the same
    if push == True:
        # Push branch and check the warning no longer appears
        RunPB(repo_a.url, "1 2 5 3 2 4 2", branch)
        TestInFile([
            "Pushing all managed repositories",
            "==== Checkedout branches ====",
            "Test: RepoA, RepoB, RepoC, RepoD",
            "==== Local branches ====",
            "Test: RepoA, RepoB, RepoC, RepoD",
            "master: RepoA, RepoB, RepoC, RepoD",
            "==== Remote/Tracked branches ====",
            "origin/Test: RepoA, RepoB, RepoC, RepoD",
            "origin/master: RepoA, RepoB, RepoC, RepoD"
        ], PB_out)

    # Delete the branch remotely (first check out to different branch)
    RunPB(repo_a.url, "1 2 5 4 3 2 4 8 1 4 2", branch)
    TestInFile([
        "==== Checkedout branches ====",
        "master: RepoA, RepoB, RepoC, RepoD",
        "==== Local branches ====",
        "Test: RepoA, RepoB, RepoC, RepoD",
        "master: RepoA, RepoB, RepoC, RepoD",
        "==== Remote/Tracked branches ====",
        "origin/master: RepoA, RepoB, RepoC, RepoD",
        "Deleted remote branch: Test"
    ], PB_out)
    TestNotInFile("origin/Test: RepoA, RepoB, RepoC, RepoD", PB_out)

    # Delete the branch locally
    RunPB(repo_a.url, "1 2 5 4 7 1 4 2", branch)
    TestInFile([
        "==== Checkedout branches ====",
        "master: RepoA, RepoB, RepoC, RepoD",
        "==== Local branches ====",
        "master: RepoA, RepoB, RepoC, RepoD",
        "==== Remote/Tracked branches ====",
        "origin/master: RepoA, RepoB, RepoC, RepoD",
        "Deleted local branch (PB generated branch): Test"
    ], PB_out)
    TestNotInFile([
        "Test: RepoA, RepoB, RepoC, RepoD",
        "origin/Test: RepoA, RepoB, RepoC, RepoD",
    ], PB_out)

def Test5(branch):
    _Test5(branch, True)

def Test6(branch):
    _Test5(branch, False)

"""
Test empty rebase on multiple repos
"""
def Test7(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    # Create new branch and validate it exists
    RunPB(repo_a.url, "1 2 3 3 5 4 4 Test", branch)
    TestInFile([
    "Built target RepoA_RepoA_Test",
    "Creating local branch Test"
    ], PB_out)

    # Rebase against the master
    RunPB(repo_a.url, "1 2 5 4 6 2", branch)
    TestInFile("Rebased branches into master", PB_out)
    TestNotInFile("There was an issue", PB_out)

"""
Test smooth rebase (there are changes to the current beanch but they are ok)
"""
def Test8(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    # Checkout master
    RunPB(repo_a.url, "1 2 3 3", branch)
    TestInFile("Built target RepoA_RepoA_Test", PB_out)

    # Prepare another clone of the repo
    inst_1 = repo_a.AddInstance(f"{test_path}/repo_a_1")
    # Get the expected PB path for this repo
    
    # Obtain the commit number from the PB path
    commits_before = GetAllCommitsFromPath(inst_1.GetPBPath(repo_a))

    # Do some changes to master in repo_a
    inst_1.ComplexCommit(GIT_COMMIT("Add random file").AddFile("some_file", "some_content")).Push()

    # Update
    RunPB(repo_a.url, "1 2 5 3 1", branch)
    commits_after = GetAllCommitsFromPath(inst_1.GetPBPath(repo_a))

    Assert(len(commits_before) + 1 == len(commits_after), f"Incorrect amount of commits {len(commits_before)} and {len(commits_after)}")

"""
Test
"""
def _Test9(branch, undo):
    repo_a, _, _, _ = CreateBaseRepos()

    # Create new branch and validate it exists
    RunPB(repo_a.url, "1 2 3 3 5 4 4 Test", branch)
    TestInFile([
    "Built target RepoA_RepoA_Test",
    "Creating local branch Test"
    ], PB_out)

    # Do some changes to master in repo_a
    inst_1 = repo_a.AddInstance(f"{test_path}/repo_a_1")
    inst_1.ComplexCommit(GIT_COMMIT("Add random file").AddFile("some_file", "some_content")).Push()

    # Update
    RunPB(repo_a.url, "1 2 5 3 1", branch)

    # Rebase against the master
    RunPB(repo_a.url, "1 2 5 4 6 2", branch)
    TestInFile("Rebased branches into master", PB_out)
    TestNotInFile("There was an issue", PB_out)

def Test9(branch):
    _Test9(branch, True)

def Test10(branch):
    _Test9(branch, False)

"""
Tests to do
TODO: branches checked out on 2 PB instances (different url)

        Test rebase

Test rebase failure on single repo:
    test both "undo rebase" and "keep conflict"

"""

# Test delete branch that was already deleted 9remote and local
tests = [
    Test1,
    Test2,
    Test3,
    Test4,
    Test5,
    Test6,
    Test7,
    Test8,
    Test9,
    Test10
]

RunTests(tests)
