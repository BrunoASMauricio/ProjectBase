#!/bin/python3

"""
Test basic process calling and retrieving output
"""

import sys

from PB_test_support import *
from processes.filesystem import GetTemporaryPath

repo_a = None
repo_b = None
repo_c = None
repo_d = None

src_file = "source/code.c"

def SetupCode(instance):
    f_name = instance.repo.name

    header = """
#ifndef """ + f_name + """
#define """ + f_name + """

int func_""" + f_name + """(int argc);

#endif
"""

    src = """#include <stdio.h>

int func_""" + f_name + """(int argc)
{
    const char* BigLine = "\\
    PRINTING """ + f_name + """ \\
    \\n";
    printf(BigLine);
    return argc - 1;
}"""

    test = """
#include """ + '"' + f_name + '.h"' + """
int main(int argc, char** argv)
{
    (void)argv;
    return func_""" + f_name + """(argc);
}
    """

    build = """
SET(repository_source_files
    ${REPO_SRC_PATH}/""" + src_file +  """
)

COMPILE_TEST(""" + f_name + """_Test ${REPO_SRC_PATH}/tests/test.c)
"""
    commit = GIT_COMMIT("Added source code")
    commit.AddFile(f"headers/{f_name}.h", header)
    commit.AddFile(src_file, src)
    commit.AddFile("tests/test.c", test)
    commit.AddFile("configs/CMakeLists.txt", build)
    instance.ComplexCommit(commit)
    instance.Push()

"""
This function adds a unique line to the print code of a repo
It returns that unique line
Use it, and check the output to know if the commit is present
"""
def AddPrintToExec(src_path, at_line=0):
    # The BigLine string starts at line 6
    start_line = 6
    at_line = start_line + at_line
    lines = ReadFile(f"{src_path}/{src_file}").split('\n')
    Assert("const char* BigLine" in lines[start_line - 2], f"Big line not present where expected: {lines}")

    unique_data = NewRandomName()
    new_printed_line = f"\\n{unique_data}\\"
    lines.insert(at_line, new_printed_line)
    WriteFile(f"{src_path}/{src_file}", '\n'.join(lines))

    return unique_data

def LazyAccepBothChanges(src_path):
    markers = [
        "<<<<<<<",
        "=======",
        ">>>>>>>",
    ]
    path = f"{src_path}/{src_file}"
    data = ReadFile(path)
    new_data = []
    for line in data.split("\n"):
        # Skip merge markers
        skip = False
        for marker in markers:
            if line.startswith(marker):
                skip = True
                break
        if skip == True:
            continue
        new_data.append(line)
        # print(line)
    WriteFile(path, '\n'.join(new_data))

def CreateBaseRepos():
    global repo_a
    global repo_b
    global repo_c
    global repo_d

    # Repo A depends on B and C
    # Repo B depends on C and D
    # Repo C and D don't have dependenciesot 
    repo_a = GIT_REPO("RepoA")
    repo_b = GIT_REPO("RepoB")
    repo_c = GIT_REPO("RepoC")
    repo_d = GIT_REPO("RepoD")

    inst_a = repo_a.AddInstance(f"{test_path}/repo_a")
    inst_b = repo_b.AddInstance(f"{test_path}/repo_b")

    inst_a.SetDependency(repo_b.url)
    inst_a.SetDependency(repo_c.url)
    inst_a.SetLocalPath("some/local/path/1")
    inst_a.Add(inst_a.conf_file).Commit("Set configs").Push()

    inst_b.SetDependency(repo_c.url)
    inst_b.SetDependency(repo_d.url)
    inst_b.SetLocalPath("some/another/path/2")
    inst_b.Add(inst_b.conf_file).Commit("Set configs").Push()

    SetupCode(inst_a)
    SetupCode(inst_b)

    repo_a.DelInstance(inst_a)
    repo_b.DelInstance(inst_b)

"""
Simple test
Test default repos work as expected
Test local paths
Run basic tests
TODO: Pass branch by parameter to the exec
"""
def Test1(branch):
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

if len(sys.argv) == 1:
    branch = "main"
else:
    if len(sys.argv) > 2:
        print("Only parameter acceptable is PB branch to test")
        sys.exit(1)
    branch = sys.argv[1]

print(f"Setting up tests for branch `{branch}` of PB")

# Only clone if PB doesnt exist
if not os.path.isdir("/tmp/PB"):
    LaunchCommand(f"[ -d \"\" ] || git clone {PB_url} /tmp/PB")
else:
    # If it exists, make sure it is up to date
    LaunchCommand(f"git -C /tmp/PB pull")

try:
    Reset()

    for test_ind in range(len(tests)):
        print(f"Running test {test_ind}")
        test = tests[test_ind]
        CreateBaseRepos()
        test(branch)
        Reset()
    print(f"Successfully ran {len(tests)} tests")
except Exception as ex:
    log = GetTemporaryPath(tmp_path)
    WriteFile(log, ReadFile(PB_log))

    out = GetTemporaryPath(tmp_path)
    WriteFile(out, ReadFile(PB_out))

    print(f"Test {test_ind} failed!: {ex}")
    sys.exit(1)
