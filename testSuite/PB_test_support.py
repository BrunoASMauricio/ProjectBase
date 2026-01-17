import os
import subprocess
from pathlib import Path

from processes.repository import GetRepoIdFromURL
from data.git import GetRepoNameFromURL
from data.common import Assert, RemoveAnsiEscapeCharacters
from processes.process import _LaunchCommand
from processes.filesystem import RemoveDirectory, CreateDirectory, WriteFile, ReadFile, CreateParentDirectory, NewRandomName
from data.json import dump_json_file, load_json_file

base_path = "/tmp/PBTests"
tmp_path = f"{base_path}/tmp"
repos_path = f"{base_path}/RemoteRepos"
PB_path = f"{base_path}/ProjectBase"
PB_out = f"{base_path}/PBOut"
PB_log = f"{base_path}/PBLog"
test_path = f"{base_path}/Tests"
PB_url = "https://gitlab.com/brunoasmauricio/ProjectBase"

def TestNotFile(path):
    if True == os.path.isfile(path):
        raise Exception(f"Not expected file {path} exists")

def TestFile(path, content=None):
    if False == os.path.isfile(path):
        raise Exception(f"Expected file {path} does not exist")
    if content != None:
        actual_content = ReadFile(path)
        if content != actual_content:
            raise Exception(f"File content differs:\nExpected: f{content}\nActual: {actual_content}")

def TestNotFolder(path):
    if True == os.path.isdir(path):
        raise Exception(f"Not expected folder {path} exists")

def TestFolder(path):
    if False == os.path.isdir(path):
        raise Exception(f"Expected folder {path} does not exist")

def TestInFile(content, file):
    file_content = RemoveAnsiEscapeCharacters(ReadFile(file))
    if type(content) == type([]):
        for el in content:
            if el not in file_content:
                raise Exception(f"content '{el}' not present in file '{file}' (from multiple: '{content}'):\n{file_content}")
        return

    if content not in file_content:
        raise Exception(f"content '{content}' not present in file '{file}'\n{file_content}")

def TestNotInFile(content, file):
    file_content = RemoveAnsiEscapeCharacters(ReadFile(file))
    if type(content) == type([]):
        for el in content:
            if el in file_content:
                raise Exception(f"unwanted content '{el}' present in file '{file}' (from multiple: '{content}'):\n{file_content}")
        return

    if content in file_content:
        raise Exception(f"unwanted content '{content}' present in file '{file}'\n{file_content}")

class GIT_COMMIT():
    def __init__(self, message):
        self.changes = []
        self.message = message

    # Change the file in a commit
    def ChangeFile(self, file, line, new_line):
        change = {
            "type": "change file",
            "file": file,
            "line": line,
            "new_line": new_line
        }
        self.changes.append(change)
        return self

    # Add a file to the commit
    def AddFile(self, file, content):
        change = {
            "type": "new file",
            "file": file,
            "content": content
        }
        self.changes.append(change)
        return self

# def AppendLine(path, content):
#     with open(path, 'a') as file:
#         file.write(content)

class CommandExecutionError(Exception):
    def __init__(self, message, return_code):
        super().__init__(message)
        self.message = message
        self.return_code = return_code

def LaunchCommand(command, path=None, to_print=False):
    result = _LaunchCommand(command, path, to_print)
    if result["code"] != 0:
        raise CommandExecutionError(
            message=f"Could not run '{command}' at {path}: {result}",
            return_code=result["code"]
        )
    return result

def RepoInit(repo):
    # Create repo instance
    instance = repo.AddInstance(f"{tmp_path}/{NewRandomName()}")

    # Add a "first commit"
    first_commit = GIT_COMMIT("first commit")
    first_commit.AddFile("first_file", "Hey!\nYou are finally awake\n")
    first_commit.AddFile("configs/configs.json", "{}")
    instance.ComplexCommit(first_commit)
    instance.Push()

    repo.DelInstance(instance)

def GetAllCommitsFromPath(path):
    """
    Return all commits from the git repository at `repo_path` as a list of dicts.
    Each dict includes:
    - sha
    - author_name
    - author_email
    - author_date
    - committer_name
    - committer_email
    - committer_date
    - message
    - diff (the patch/changes)
    """
    # Use record and field separators to delimit fields and commits
    # We stop the metadata section with a unique delimiter before the diff.
    sep_field = "\x1f"
    sep_commit = "\x1e"
    end_meta = "\x1d"  # sentinel between metadata and diff
    pretty_fmt = (
        sep_commit + "%H" + sep_field +
        "%an" + sep_field + "%ae" + sep_field + "%ad" + sep_field +
        "%cn" + sep_field + "%ce" + sep_field + "%cd" + sep_field +
        "%s\n%b" + end_meta
    )
    cmd = [
        "git", "-C", str(path),
        "log",
        f"--pretty=format:{pretty_fmt}",
        "--date=iso-strict",
        "--patch"  # include diffs
    ]
    a = 0
    def ParseDiff(diff):
        lines = diff.split('\n')

        if lines[0].startswith("diff") == False:
            return ""

        for ind in range(len(lines)):
            line = lines[ind]
            if line.startswith("--- "):
                break
        Assert(lines[ind].startswith("---"),     f"AA1 {ind} {lines}")
        Assert(lines[ind + 1].startswith("+++ b"), f"AA2 {ind} {lines}")

        if lines[ind].startswith("--- a"):
            from_file = lines[ind].replace("--- a", "")
        else:
            from_file = lines[ind].replace("--- ", "")

        new_format = {
            "from": from_file,
            "to":   lines[ind + 1].replace("+++ b", ""),
            "content": lines[ind + 2:]
        }
        return new_format
    try:
        raw = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to run git log: {e.output!r}") from e
    commits = []
    # Each record ends at sep_commit
    for raw_commit in raw.split(sep_commit):
        a += 1
        if not raw_commit.strip():
            continue
        # Split metadata from diff on our sentinel
        try:
            meta_part, diff_part = raw_commit.split(end_meta, 1)
        except ValueError:
            # If no sentinel found, skip
            continue
        fields = meta_part.strip().split(sep_field)
        (
            sha,
            author_name, author_email, author_date,
            committer_name, committer_email, committer_date,
            subject
        ) = fields
        commits.append({
            "sha": sha,
            "author_name": author_name,
            "author_email": author_email,
            "author_date": author_date,
            "committer_name": committer_name,
            "committer_email": committer_email,
            "committer_date": committer_date,
            "subject": subject,
            "diff": ParseDiff(diff_part.strip()),
        })
    return commits

class GIT_REPO_INSTANCE():
    def __init__(self, repo, path):
        self.repo = repo
        self.path = path
        self.confs = {}
        self.commits = []
        self.conf_file = f"{self.path}/configs/configs.json"
        LaunchCommand(f"git clone {repo.bare_path} {self.path}")
        self.__loadConfs()

    def GetPBPath(self, root_proj):
        return f"{PB_path}/projects/{root_proj.name}.ProjectBase/code/{self.GetConfs()["local_path"]}/{self.repo.name}"

    def __loadConfs(self):
        self.confs = load_json_file(self.conf_file, {})

    def __saveConfs(self):
        dump_json_file(self.confs, self.conf_file)

    def SetConfs(self, confs):
        self.confs = confs
        self.__saveConfs()

    def GetConfs(self):
        return self.confs

    # Some helpers for configs (instead of editing them directly)
    def SetLocalPath(self, path):
        self.confs["local_path"] = path
        self.__saveConfs()

    def SetDependency(self, url):
        if "dependencies" not in self.confs.keys():
            self.confs["dependencies"] = {}

        self.confs["dependencies"][url] = {}

        self.__saveConfs()

    def RunGitCommand(self, command):
        LaunchCommand(command, self.path)
        return self

    def Add(self, path):
        self.RunGitCommand(f"git add {path}")
        return self

    def Commit(self, commit_message):
        self.RunGitCommand(f"git commit -m '{commit_message}'")
        return self

    def Push(self):
        self.RunGitCommand(f"git push")
        return self

    def CommitAndPushAll(self, commit_message):
        self.RunGitCommand(f"git add -A")
        self.Commit(commit_message)
        self.Push()

    def ComplexCommit(self, commit):
        self.commits.append(commit)
        for change in commit.changes:
            # Always try to create parent folder(s)
            full_path = f"{self.path}/{change["file"]}"
            CreateParentDirectory(full_path)

            if change["type"] == "new file":
                TestNotFile(full_path)
                WriteFile(full_path, change["content"])
            # elif change["type"] == "change file":
            #     TestFile(full_path)
            #     ReplaceLine(full_path, change["line"], change["new_line"])

            self.Add(change["file"])

        self.Commit(commit.message)
        return self

    """
    Return all commits from the git repository at `repo_path` as a list of strings.
    Each element is formatted as:
    "<sha> <date> <author> - <subject>"
    """
    def GetAllCommits(self):
        return GetAllCommitsFromPath(self.path)


class GIT_REPO():
    def __init__(self, name):
        self.instances = []
        self.bare_path = f"{repos_path}/{name}.git"
        self.url  = self.bare_path
        self.id   = GetRepoIdFromURL(self.url)
        self.name = GetRepoNameFromURL(self.url)
        Assert(name == self.name)

        # Initialize remote repository
        LaunchCommand(f"mkdir {self.bare_path}; cd {self.bare_path}; git init --bare {self.bare_path}")

        # Setup first commit data 
        RepoInit(self)

    def AddInstance(self, path):
        instance = GIT_REPO_INSTANCE(self, path)
        self.instances.append(instance)
        return instance

    def DelInstance(self, instance):
        LaunchCommand(f"rm -rf {instance.path}")
        self.instances.remove(instance)



def Reset():
    # Full reset base path
    RemoveDirectory(base_path)
    CreateDirectory(base_path)
    os.chdir(base_path)

    # Setup repos path
    CreateDirectory(repos_path)

    # Setup PB
    LaunchCommand(f"cp -r /tmp/PB {PB_path}")

"""
Reset log and output file
Run ProjectBase with the appropriate commands, url and PB branch
"""
def RunPB(url, commands, branch):
    # Truncate files
    WriteFile(PB_log, "")
    WriteFile(PB_out, "")
    LaunchCommand(f"git checkout {branch}", path=PB_path)
    cmd = f"./run.sh --fast --log_file={PB_log} --out_file={PB_out} -e --url={url} {commands}"
    return_info = LaunchCommand(cmd, to_print=False, path=PB_path)
    return return_info
    # LaunchCommand(f". setup.sh; ./run.sh --fast --log_file={PB_log} --out_file={PB_out} -e --url={url} {commands}", to_print=False, path=PB_path)


"""
Create a list of commits that are incompatible with each other
They all create a different file with the same name
"""
def PrepareIncompatibleCommits(amount_of_commits):
    file_name = NewRandomName()
    commits = []
    content = "oh oooooh, spaghetiooos"
    for ind in amount_of_commits:
        commit = GIT_COMMIT()
        commit.AddFile(file_name, f"{content} commit# {ind}")
        commits.append(commit)

    return commits

