#!/bin/python3

"""
Test basic process calling and retrieving output
"""

from PB_test_support import *
from PB_test_base_repos import *

"""
Simple test
Test default repos work as expected
Test local paths
Run basic tests
TODO: Pass branch by parameter to the exec
"""
def Test1(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    RunPB(repo_a.url, "1 2 3 3", branch)
    TestInFile("Built target RepoA_RepoA_Test", PB_out)
    TestInFile("Built target RepoB_RepoB_Test", PB_out)

    TestFolder(f"{PB_path}/projects/RepoA.ProjectBase/code/RepoC")
    TestFolder(f"{PB_path}/projects/RepoA.ProjectBase/code/some/local/path/1/RepoA")
    TestFolder(f"{PB_path}/projects/RepoA.ProjectBase/code/some/another/path/2/RepoB")
    TestInFile("All 2 tests successful!", PB_out)

    # Run single test
    RunPB(repo_a.url, "1 3 2 0", branch)
    TestInFile("PRINTING RepoA", PB_out)
    TestNotInFile("PRINTING RepoB", PB_out)

    # Run another test
    RunPB(repo_a.url, "1 3 2 1", branch)
    TestNotInFile("PRINTING RepoA", PB_out)
    TestInFile("PRINTING RepoB", PB_out)


"""
Test changes and update
"""
def Test2(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    RunPB(repo_a.url, "1 2", branch)
    TestInFile("Built target RepoA_RepoA_Test", PB_out)
    TestInFile("Built target RepoB_RepoB_Test", PB_out)

    inst_1 = repo_a.AddInstance(f"{test_path}/repo_a_1")
    commits_before = inst_1.GetAllCommits()
    inst_1.ComplexCommit(GIT_COMMIT("Add random file").AddFile("some_file", "some_content")).Push()
    commits_after = inst_1.GetAllCommits()
    Assert(len(commits_before) + 1 == len(commits_after), f"Incorrect amount of commits {len(commits_before)} and {len(commits_after)}")
    # Update repo
    RunPB(repo_a.url, "1 5 3 1 1", branch)
    # Changes were compatiable, so it should have updated and still be synced/clean
    TestInFile("Project is clean", PB_out)
    TestInFile("Project is synced", PB_out)

"""
Add a print (in a commit that isnt problematic)
Non updated repo does not have this print
Updated repo has this print
"""
def Test3(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    # Setup new data to be printed
    inst_1 = repo_a.AddInstance(f"{test_path}/repo_a_1")
    data_to_print = AddPrintToExec(inst_1.path, 0)

    # Data doesnt exist originally
    RunPB(repo_a.url, "1 2 3 2 0", branch)
    TestNotInFile(data_to_print, PB_out)
    # Update repo
    inst_1.Add(f"{inst_1.path}/{src_file}").Commit("Add print").Push()
    RunPB(repo_a.url, "1 5 3 1", branch)
    # Now print exists!
    RunPB(repo_a.url, "1 2 3 2 0", branch)
    TestInFile(data_to_print, PB_out)

"""
Test incompatible changes
"""
def Test4(branch):
    repo_a, _, _, _ = CreateBaseRepos()

    # Setup BP and "remote" instance
    inst_1 = repo_a.AddInstance(f"{test_path}/repo_a_1")
    RunPB(repo_a.url, "1 2 3 2 0", branch)

    # Setup data to print
    data_to_print_1 = AddPrintToExec(inst_1.path, 0)
    pb_source_path = f"{PB_path}/projects/RepoA.ProjectBase/code/{inst_1.GetConfs()["local_path"]}/RepoA/"
    data_to_print_2 = AddPrintToExec(pb_source_path, 0)

    # Sanity check that data doesnt exist originally
    TestNotInFile(data_to_print_1, PB_out)
    TestNotInFile(data_to_print_2, PB_out)

    # Check status
    RunPB(repo_a.url, "1 2 5 1", branch)
    TestInFile([
                    "Project is dirty",
                    "There is 1 dirty managed repo: RepoA (at /some/local/path/1/RepoA)",
                    "There are no dirty unknown repos",
                    "Project is synced"
                ],
               PB_out)

    # Update repo with first change
    inst_1.Add(f"{inst_1.path}/{src_file}").Commit("Add print 1").Push()

    # Attempt to update PB
    RunPB(repo_a.url, "1 2 5 3 1", branch)
    # Validate message
    TestInFile(["source/code.c: needs merge", "WARNING: Code needs merge"], PB_out)

    # Fix merge conflict and update
    LazyAccepBothChanges(pb_source_path)
    RunPB(repo_a.url, '1 2 5 2 1 "Fixed merge conflict"', branch)

    # Check status again
    RunPB(repo_a.url, "1 2 5 1", branch)
    TestInFile([
                    "RepoC (at /RepoC) is synced and clean",
                    "RepoB (at /some/another/path/2/RepoB) is synced and clean",
                    "RepoA (at /some/local/path/1/RepoA) is ahead (fix with sync push) and clean",
                    "RepoD (at /RepoD) is synced and clean",
                    "Project is clean",
                    "Project is desynced",
                    "There is 1 desynced managed repo: RepoA (at /some/local/path/1/RepoA)",
                    "There are no desynced unknown repos"
                ],
               PB_out)

    # Check both prints
    RunPB(repo_a.url, "1 3 2 0", branch)
    TestInFile(["PRINTING RepoA", data_to_print_1, data_to_print_2], PB_out)

tests = [
    Test1,
    Test2,
    Test3,
    Test4
]

RunTests(tests)
