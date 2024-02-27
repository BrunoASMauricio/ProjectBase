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

- [ ] Add some statistics (i.e. baregit vs direct clone sizes and time delta between first and second project setups)
- [ ] Find a way to identify repositories without using URLs (different URLs can point to the same repo)
- [ ] Add screenshot or text block of ProjectBase banner in README
- [ ] Update documentation
- [ ] Allow the review of code when add/commiting ?
- [ ] Try and setup git so normal pushes via single repo manipulation work as expected
- [ ] Allow config customization when creating a new project with new.py
  - [ ] Initial directory
  - [ ] Initial dependencies
  - [ ] Default README?
  - [ ] Default example?
  - [ ] Use options (y/n/a yes/no/all)
- [ ] Add support for a configuration system (i.e. Kconfig)
- [ ] Add support for some documentation system (i.e. doxygen)
- [ ] Investigate necessity/feasibility of sending strings into code
- [ ] gitall tasks
  - [ ] Do not perform `cd` for every git operation
  - [ ] Periodically fetch new data from repos
  - [ ] Periodically remove non-existing worktrees
  - [ ] Add option for custom command to run on all repos
  - [X] Add single repo manipulation by providing a semi-independent console,
already in the relevant directory
  - [ ] Improve detection of desync between baregit and upstream so push doesn't
need to work on clean repos
