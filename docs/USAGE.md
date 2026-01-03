# Running

## Automated runs

Any parameters passed onto the run script is treated as menu input.
Example for loading (1), building (2) and running the first test (3 2)
```shell
./run.sh --url='your repo url' 1 2 3 2
```

After the inputs are parsed, control is returned, on the appropriate menu.
The `-e/--exit` argument stops execution after all arguments have been parsed

If there is an exception running one of the arguments, PB will exit immediately even if there are more arguments

## Arguments

### Automated arguments

To pass arguments to an executable during automated runs, use the --args option.
For one of the arguments to contain spaces, use '' and surround that argument in particular with ""

Example for executing the first test with 3 arguments:
```shell
./run.sh -e --url='your repo url 3 2 0 --args='arg1 arg2 "space separated arg"'
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
