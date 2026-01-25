# Internals

## Developing in ProjectBase

A good way to develop in PB is using it to test itself.

Use the following command to generate the base repositories in /tmp/PBTests (using the `testSuite_create_test_repos.py` script)
`./run.sh --url=git@gitlab.com:brunoasmauricio/ProjectBase.git 1 2 3 2 0 -e`
It will print the default test repositories which can be used for development.
To reset the repositories, simply re run the command anpve

Use the test repos for developing PB
`./ru

```shell
./run.sh -e --url=git@gitlab.com:brunoasmauricio/ProjectBase.git --branch=<branch to test>
# Then in the menus:
# Load the project
1
# Build (so the tests are placed appropriately)
2
# Commit and push

# Run the tests in the appropriate a
3 2 1 --args=BranchTests


Changes to PB need to be committed to be tested
Changes to tests dont, as long as they are done inside of the actual project being launched by PB and not the root PB

Add sys.exit(0) to the end of a test so the state isnt lost, and you can do `cd /tmp/PBTests/ProjectBase`
and then `. setup.sh; ./run.sh  --url=/tmp/PBTests/RemoteRepos/RepoA.git`

```

### Structure

- `templates/`: Store templates for build system, scripts, etc
- `menus/`: Generic code for creating menus and creating them with internal code
- `data/`: Code that deals with data handling
- `processes/`: Code that performs operations

### Processes

There are many ways to "run" code, depending on the requirements.

#### RunOnAllRepos / RunOnAllManagedRepos
Run a callback, on either all repositories that can be identified, or only PB managed repositories
uses `RunOnFolders`

#### RunOnFolders
Run a callback on the specified list of paths()
Uses `RunInThreadsWithProgress`, using `__RunOnFoldersThreadWrapper` as the callback, to setup the "path argument" (To revise)

#### RunInThreadsWithProgress
Run a callback with each of the specified parameters and print progress via a ProgressBar.
Decides and sets up multi-threading based on command line argument `-s/--single_thread`
Uses `RunInThreads` for multi-threading

#### RunInThreads
Run the provided callback, for each argument in the list, in a separate thread
Uses `ThreadWrapper`, which handles callback exceptions and sets up thread specific data

#### RunExecutable
TODO: Revise

#### LaunchProcess
Run a string based command, in the same Environment and setup a proper error message if the process fails

#### _LaunchCommand
Launch a command based on string, on a specific directory
Depending on `to_print` argument, uses fast, non-interactive `pty.spawn`, or `subprocess.run`.
Sets up and returns information about the process (stdout, stderr, code, etc)
TODO: Revise argument name

## Versioning

In git_operations there are the basic git operations
This is also where the translation between the branches the user sees and the unique local nomenclature happens

data/git is merely internal git data (no git commands required)

git_operations: Perform the git operations and translate the result into internals

versioning: Use git operations to perform versioning operations
