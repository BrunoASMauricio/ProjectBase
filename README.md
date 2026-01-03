# ProjectBase

```text

 ______              __              __   ______
|   __ \.----.-----.|__|.-----.----.|  |_|   __ \.---.-.-----.-----.
|    __/|   _|  _  ||  ||  -__|  __||   _|   __ <|  _  |__ --|  -__|
|___|   |__| |_____||  ||_____|____||____|______/|___._|_____|_____|
                   |___|
Debug build 
(`Your/Repo/Url`)
(ssh access - Safe)
(`/Path/To/Loaded/Project`)
(01/03/2026 12:52:33)(`local_user`)
1 ) Load project (X loaded repositories)
2 ) Build project (launches the build environment for this purpose)
3>) Run
4>) Analyze
5>) Versioning
6>) Clean
7>) CI
8 ) Configure Project
9>) ProjectBase settings
Ctrl + D to exit
[<] 

```

ProjectBase enables the composition and management of projects that are made up
 of "micro libraries", with an "optional by default" approach.

Instead of copy pasting useful pieces of code from one project to another,
 or setting up a library and having to deal with "how do I install, how do I
 setup the headers, how do I link, how do I test, etc", simply create a git
 repository for that code and set its' URL as a dependency for your projects!

ProjectBase takes care of downloading and setting everything up!

Some neat features are:

1. Configure only what you want to use;
2. Easily integrate read-only repositories;
3. Single command, multi repository git management tooling;
4. Increased test coverage;
5. Decentralized programming

And more!

<!-- See more on how to set up your project with Project Base [here](https://gitlab.com/brunoasmauricio/ProjectBase/-/wikis/Setup-and-Run#setting-up-a-project) -->

#### "Micro Libraries"

A micro library is defined in PB as an independent git repository, with a "optional by default" `configs/configs.json`
 which configures how PB sets that repository up.

This contrasts with the classic "library" setup where for each library, it is necessary to provide
 compilation/linking scripts.
This extra work usually leads to libraries to be more "complete" and therefore complex, recreating functionality such
 as error handling, logging, file handling, etc.
The objective of PB is for each micro library to be focused on a single task, and delegate as much as possible to other
 micro libraries.

Since each repository can have independent tests, this also means that even for big projects, it is possible to achieve
 100% test coverage, because there is effectively a way to reach into each corner of the final binary.

#### "Optional by default"
Optional by default means that even if there is no configuration file, or if that configuration file does not have some
 or all of the possible configuration directives, PB will provide simple, unintrusive defaults.

It is also possible for a repository to "impose" configurations on one of their dependencies, which allows the use and full
 configuration of any existing repository without having to create forks to add configuration files.


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
