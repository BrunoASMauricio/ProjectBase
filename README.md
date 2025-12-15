# ProjectBase

```text
 ______              __              __   ______
|   __ \.----.-----.|__|.-----.----.|  |_|   __ \.---.-.-----.-----.
|    __/|   _|  _  ||  ||  -__|  __||   _|   __ <|  _  |__ --|  -__|
|___|   |__| |_____||  ||_____|____||____|______/|___._|_____|_____|
                   |___|
Debug build
(<Projects' URL>)
(<Projects' Path>)
First argument must be the URL of the target project
1) Generate project (build/pull from templates and configs)
2) Build project (launches the build environment for this purpose)
3) Run project executable
4) Run all tests
5) Run single test
8) Run gitall.sh script
9) Clean binaries (remove all object and executable files, as well as the CMakeLists cache)
0) Project settings
Ctrl + D to exit
[<] 
```

ProjecBase helps managing a codebase composed of several code snippets or
libraries.

Instead of copy pasting bits and pieces of code from one project to another,
or setting up a library and having to deal with "how do I install, how do I
setup the headers, how do I link", simply create a git repository for that code
and set its' URL as a dependency for your projects!

ProjectBase takes care of downloading and setting everything up!

Some neat features are:

1. Configure only what you want to use;
2. Use existing projects, imposing custom configurations on them (i.e. where are
the headers? do we need to run some commands after downloading?);
3. Specify a commit so updates to a library don't break older projects;
4. Deal with diamond dependency! (*as long as configuration matches*).

And more

See more on how to set up your project with Project Base [here](https://gitlab.com/brunoasmauricio/ProjectBase/-/wikis/Setup-and-Run#setting-up-a-project)

## Concept

ProjectBase helps setup and manage large projects, providing the necessary tooling for
working with each of the components.

Each component of the project can be viewed, executed and tested as a project
itself. They are git repositories, and depending on the presence of certain
files, instruct ProjectBase on how to set it and its dependencies up.

It uses git for version management, CMakeLists as the main build system and
Python to orchestrate all of this.

An example project structure can be found below. Each module can be built and ran, only requiring the repositories they depend on, whether this is for development or testing.

Such a scheme encourages:

1. Modularity: Each repository holds smaller logical functions
2. Efficiency: Only download/build/test what truly is required
3. Unit Testing: Easily focus on single components

All without sacrificing:

1. System testing: The tests from higher level repositories end up being the system tests!
2. Simplicity: ProjectBase is just a few scripts written in a beginner friendly language (python), with no big complex framework behind it
3. Adaptability: The build system (CMake) can easily integrate other build systems, and the provided CMakeList templates can act as a backbone for complex build procedures, or even be simply used to toggle your particular build procedure

Example Project Diagram:

![Example Project Diagram](./images/ProjectBase_ProjectDiagram.jpg)

Interested in how to start using ProjectBase? Checkout some [workflows](https://gitlab.com/brunoasmauricio/ProjectBase/-/wikis/workflows)!

See all available information in the [wiki](https://gitlab.com/brunoasmauricio/ProjectBase/-/wikis/home)!

ProjectBase is licensed under GNU General Public License Version 3

## TODO

Ordered by priority

### General

- [X] Dependency visualizer
- [ ] ProjectBase documentation
- [ ] Add ProjectBase configs
  - [ ] For project wide flags
  - [ ] For build system setup
  - [ ] For config system setup
- [X] Print information about the running thread, if it takes too long
- [ ] Add auto-test option that pulls each repository independently, loads and builds the project, runs all tests and checks if everything went ok
- [ ] Consecutive failures should only make ProjectBase quit if they happen in quick succession
- [ ] Add option to disable dense logging
- [ ] Provide "code only" view into a project
  - [ ] Just like build folder is separate, use links to generate a view that only contains headers and source code
- [X] Add abstraction similar to menu, but for multiple choice stuff (i.e. executable/test/project/single repo to manage operations)
- [X] Add "There have been errors, please check the logs at PATH" message for logged exceptions
- [ ] Find a way to identify repositories without using URLs (different URLs can point to the same repo)
      Use the X commit of the default branch?
  - [ ] Overhaul handling of repositories by name/url/path. Use unique internal ID that can link to those three attributes
- [ ] Create abstraction to allow different build systems
  - [ ] Put CMake commands into separate specialization of said abstraction
- [ ] Divide test results into their respective modules
- [ ] Give warning if the same link (repository) has been checked out in different places
- [ ] Add support for some documentation system (i.e. doxygen)
- [ ] Add some statistics (i.e. baregit vs direct clone sizes and time delta between first and second project setups)
- [ ] Revamp old "new repository" creation script
  - [ ] Automatically set as dependent of existing repos, and auto commit that change in them
  - [ ] Allow config customization when creating a new project with new.py
    - [ ] Initial directory
    - [ ] Initial dependencies
    - [ ] Default README?
    - [ ] Default example?
    - [ ] Use options (y/n/a yes/no/all)
- [ ] Project metadata visualization (dependency tree, test amount and percentage of failures, ...)
- [X] Add time (with seconds) to banner. Helps in knowing when we ran the last commands
- [ ] Detect when ProjectBase was copy pasted into a different repository (messed up worktrees) and fix it
- [ ] Inserting commands during other commands does not work, but it should be possible to chain commands using a separator like ';'. (unclear now on what todo here)
- [X] Reset terminal after recovering control from external programs
- [ ] ?Organize the binaries by either date or name (maybe hash and say last time changed?)?
- [ ] Mass run valgrind
  - [ ] Collect how many bytes are lost and how many different errors, per each test
- [ ] Fix completion
  - [ ] Current input counts for completion. i.e. '3 3 ' and then TAB would show the possible completions of menu 3.3 and not current menu
- [ ] Deal with projects that have no code (simple message stating nothing to do)
- [X] Modify how processes are called. Multiple attempts should not be necessary and are very error prone
- [ ] Check config file on all config checks, dont cache
  - [ ] Special care with inherited configs
- [ ] abstract stack printer from processes
  - [ ] In logging
  - [ ] In general stack printing (non process stack)
- [ ] Sometimes input is blocked. A Ctrl+C fixes this, but it should still be fixed
- [ ] Only refresh project configurations for changes to configs.json
- [ ] Ponder idea of "virtual" dependencies that are just configuration layers for a project (i.e. they do not need an actual repository?)
- [ ] Allow extra preprocessing stage (i.e. custom preprocessor before GCC?). Maybe generalize how compilation runs. Needs to be done via CMakeLists but supported by ProjectBase
- [ ] Allow patches to be applied to dependencies on initial setup
  - [I] Purpose: Dependent on open source repos, but require some changes
- [ ] Only print a full menu if there isn't an automated input for the next one. If there is, print just the name of the operation that ran and from what menu it is

### CMake
- [ ] Build commands are now becoming too big and some error are appearing like so: 
  cc: fatal error: cannot execute ‘/usr/libexec/gcc/x86_64-redhat-linux/15/cc1’: posix_spawn: Argument list too long
  compilation terminated.
  gmake[2]: [CMakeFiles/AppTest.dir/build.make:79: CMakeFiles/AppTest.dir/home/ricostynha/Desktop/myth/ProjectBase/projects/textformatter.ProjectBase/code/Application/TestApp/app.c.o] Error 1
  Command has to be shrinked:
     - Remove duplicates from the command itself: maybe following something on this github:
      https://github.com/rock-core/base-cmake/issues/49
     - Stop putting link flags in compile flags
      Remove -lX11 -lXext -lncurses -lm -pg from CMAKE\_C\_FLAGS and CMAKE\_CXX\_FLAGS; keep them only in CMAKE\_EXE\_LINKER\_FLAGS / CMAKE\_SHARED\_LINKER\_FLAGS or target\_link\_libraries()
     - Command is passing global path to everything what is too verbose (relative to base project rooth is more sensible in majoriy of cases)
     - Use top level include dir instead of all subvarints:
        For a tree like /code/Runtime/Data/Array/{headers,inc,include,code,execs,tests,...},
        pick a single root (for example /code/Runtime/Data/Array) and adjust that module’s CMake to add only that as an include directory, letting the compiler find headers relative to it


- [X] Only add headers that exist
- [ ] Allow all build configs via configs.json
- [ ] Prevent executables from having the same name as a generated object/executable/library (aka a target)
- [ ] Only link directly against actual dependencies
- [ ] Alphabetically organize executables, and present them organized by the module they were defined in

### Build

- [ ] Make requested bash commands "before build" and "after build" run parallel to other such command lists

### Setup

- [X] Fix long loading times
- [X] Allow to clean Project Base cache
- [X] Separate loading from setup (loading loads the repos internally, setup forces a load and runs setup commands)
- [ ] Review imposed configs
- [X] Improve detection of configuration change
  - [ ] Improve detection of configuration change for imposed configs
- [?] Improve ability to change configs on the fly (without committing, pushing, deleting and recreating the project)

### Tests

- [ ] Allow defining different testing groups (i.e. tests that are heavy and should therefore not run everytime)
- [ ] Once a configuration system is present, allow running tests for multiple different configurations
  - [ ] Compile and run tests for each configuration independently (requires multiple CMAKE build and binary directories)
  - [ ] Depending on the load, adapt amount of threads spawned for tests
- [ ] On failure, provide better summary
  - [ ] After printing messages, print summary
  - [ ] In the summary, also print the index of the tests that failed, next to their name

### Configurability

- [ ] Collapse configs into single configs.json (dont use folder)
  - [ ] Allow users to specify source files and executables/tests to build
- [ ] Allow extra cflags per
  - [ ] object
  - [ ] module
  - [ ] globally
- [ ] Add support for a configuration system (i.e. Kconfig)
- [ ] Add support for a hardware description language (i.e. devicetree)
- [ ] Investigate necessity/feasibility of sending strings into code
- [ ] Allow the use of strings and lists (i.e. check type)
- [ ] Add option for custom command to run on all repos
- [ ] Allow public, private and test headers to be defined by each project. Or simply allow public and private, and tests have access to both?

### Versioning

- [X] In status, warn if there are dirty repos that will not be commited (have the no commit flag set)
- [X] Add information on sync status in getting repo status
- [ ] Toggle between project wide and specific repository operations
- [X] Allow two types of commits
  - [X] "fixed" commits (other word isencouraged) are normal commits
  - [X] "save" commits are temporary, and will be squashed into the next "fixed" commit
- [X] Before moving a worktree, make sure there are no RepoSaveChanges
  - [X] Done by using worktree move and not add + remove
- [ ] Allow the review of code when add/commiting ?
      On push, allow per repo fix on conflict
- [X] Warn exactly which repos are being comitted
- [ ] Try and setup git so normal pushes via single repo manipulation work as expected
- [ ] Failed clones should automatically be cleaned up
        Current bug, failed pulls somehow obtain the projectbase URL and subsequent `setup` clones projectbase instead of the respective repository
- [ ] Periodically fetch new data from repos. No automatic merge
- [ ] Periodically remove non-existing worktrees
- [X] Add single repo manipulation by providing a semi-independent already in the relevant directory
- [X] Improve detection of desync between baregit and upstream so push doesn't need to work on clean repos
- [ ] Deal with repositories pulled into other repositories
  - [ ] An example is when moving worktree, inner worktrees will be broken
- [ ] Do not perform `cd` for every git operation (why?)
- [ ] Allow swapping all repositories to a new branch
  - [ ] Allow seing all branches
  - [ ] Allow merging of that branch into another branch
    - [ ] Branches with no changes suffer nothing
- [ ] From time to time automatically sync (temporary commit)

Configs that CAN NOT have variables
  local path
  url

same dependencies with different imposed configs shoudld errorr out
ssame dependenceis with different branches/commits in the same path (in different paths it should work)
