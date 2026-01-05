# Internals

## Developing in ProjectBase

A good way to develop in PB is using it to test itself.

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

From high to low complexity: