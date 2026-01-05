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

def AddPrintToExecBreaking(src_path, at_line=0):
    # The BigLine string starts at line 6
    start_line = 0
    at_line = start_line + at_line
    lines = ReadFile(f"{src_path}/{src_file}").split('\n')

    unique_data = "This will do a syntax error and break build" + NewRandomName()
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

# The function needs to return repos
# Imports might import the variables before they are initialized and copy by value
def CreateBaseRepos():
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

    return repo_a, repo_b, repo_c, repo_d

def RunTests(tests):
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
            test = tests[test_ind]
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
