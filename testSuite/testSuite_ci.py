#!/bin/python3

"""
Test basic process calling and retrieving output
"""

from PB_test_support import *
from PB_test_base_repos import *

"""
Simple test
Test CI no change
"""
def Test1(branch):
    try:
        RunPB(repo_a.url, "1 7 1", branch)
    except CommandExecutionError as e:
        message = e.message
        ret_code = e.return_code
        raise ValueError(f"CI Failed, as it returned a non 0 return value:\n val :{ret_code} message: {message}")

"""
Add a change on a commit that will break the build
"""
def Test2(branch):
    global repo_a
    inst_1 = repo_a.AddInstance(f"{test_path}/repo_a_1")
    data_to_print =  AddPrintToExecBreaking(inst_1.path, 0)

    inst_1.Add(f"{inst_1.path}/{src_file}").Commit("Add print").Push()
    RunPB(repo_a.url, "1 5 3 1", branch)
    try:
        return_info = RunPB(repo_a.url, "1 7 1", branch)
    except CommandExecutionError as e:
        message = e.message
        ret_code = e.return_code
        # It is suppose to fail with ret_code of 1 (CI always fails with 1 for now)
        if(ret_code != 1):
            raise ValueError("ret_code receive should be 1 in Test 2 of CI, as CI when failed returns 1")
    else:
        # If no exception occured! (it should occur so it is an error)
        raise ValueError("Running test 2 of CI should trigger an exception, but it did not, as return code is diferent from 0, it should be 1")
    

"""
Test incompatible changes
"""
def Test4(branch):
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
    Test2
]

RunTests(tests)
