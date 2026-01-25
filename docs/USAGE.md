# Running

## Invocation

```shell
usage: ./run.sh [-h] [-u URL] [-o OUT_FILE] [-l LOG_FILE] [-c COMMIT] [-b BRANCH] [-s | --single_thread | --no-single_thread] [-e] [-d] [-f] [-ci COMMITJSONPATH]

Extra command line arguments are treated as commands for ProjectBase

options:
  -h, --help            show this help message and exit
  -u, --url URL         Root repository's URL
  -o, --out_file OUT_FILE
                        Output to file
  -l, --log_file LOG_FILE
                        Pipe internal logs to file
  -c, --commit COMMIT   Root repository's commit
  -b, --branch BRANCH   Root repository's branch
  -s, --single_thread, --no-single_thread
                        Do not run PB in multiple threads
  -e, --exit            Exit after running command line arguments. Performs early exit in case one of the operations ends in error
  -d, --debug           Increase log verbosity to debug ProjectBase
  -f, --fast            Cache Repositories in pickle and do not consider config changes, deactivate to consider if needed
  -ci, --commitJsonPath COMMITJSONPATH
                        JSON Information with all the repos that have commit changes, that have to be commit copied instead of usual by remote copy
```

## Help

On any menu, inputting '?' or 'help' prints the help for the entries in that menu

## Navigation

PB has a standardized menu navigation scheme where each entry can be selected by inputting the index printed next to it.

```shell
1 ) Load project (1 loaded repositories)
2 ) Build project (launches the build environment for this purpose)
3>) Run
4>) Analyze
5>) Versioning
6>) Clean
7>) CI
8 ) Configure Project
9>) ProjectBase settings
Ctrl + D to exit
Previous command: 7
[<] 
```

### Menu return

Menu entries that perform an operation, will return to the parent menu after the operation is concluded.
The default behavior is for a menu that is returned this way to return to their parent as well, going up to either a parent that "holds" or to the main menu.

### Going back

The user can always press enter with an empty input, to go back, or Ctrl + D to exit PB on most menus.

Some menus can "hold" execution until a certain key is pressed (these menus inform the user which key this is)

### Automated return

In most ocasions (i.e. command line invoction) it isn't useful or even possible to pass an empty argument. As such, 'out' can always be used to go to the previous menu, both during an interactive run and an automated run

## Automated runs

Any parameters passed onto the run script is treated as menu input.
Example for loading (1), building (2) and running the first test (3 2)
```shell
./run.sh --url='your repo url' 1 2 3 2
```

After the inputs are parsed, control is returned, on the appropriate menu.
The `-e/--exit` argument stops execution after all arguments have been parsed

If there is an exception running one of the arguments, PB will exit immediately even if there are more arguments

## Executable Arguments

### Automated arguments

To pass arguments to an executable during automated runs, use the --args option.
For one of the arguments to contain spaces, use '' and surround that argument in particular with ""

Example for executing the first test with 3 arguments:
```shell
./run.sh -e --url='your repo url' 3 2 0 --args='arg1 arg2 "space separated arg"'
```

### Interactive arguments

Interactive arguments are simply a space separated list
```shell
Executables available in /..../binaries/objects/tests:
	<RepoA>
[0]RepoA_Test

!V for valgrind. !G for GDB. !S for GDB server @ 127.0.0.1:6175
Upper case (V,G,S) uses default parameters, lower case doesn't.
[![G|V|S]]<INDEX [0-9]+> [Space separated argument list]
exit or Ctr+D to exit
[<] 0 arg1 arg2 "space separated arg"
Running: "/..../binaries/objects/tests/RepoA/RepoA_RepoA_Test asdas asd "asda asda"
```

### Argument prefixes

There are a few prefixes defined for the executables.
These are selected by adding a `!` character followed by the respective command character.
The characters/prefixes/operations available are:
`!G`: gdb and pass arguments
`!S`: gdbserver on port 6175
`!V`: valgrind with a lot of options
`!C`: callgrind
`!g`: gdb with no options
`!s`: gdbserver with no options
`!v`: valgrind with no options



# Scripts

Python scripts launched from within PB contain access to the internal PB functions, as well as sharing the python venv and pip installation
