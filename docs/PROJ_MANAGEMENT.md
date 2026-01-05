# Opinionated management

## 
Here is an opinionated way for managing a multi-person project with ProjectBase

For developing a new feature, a developer creates/moves to a new branch:

```shell
# Create a local branch with a unique pseudo random name, connected to a remote branch with the exact name
./run.sh --url=git@gitlab.com:brunoasmauricio/ProjectBase.git 5 4 2 some/branch/name -e
```

Important note.
The actual local branch will be a unique branch, that follows the actual branch remotely.
This is done so multiple projects can use the same remote branch for the same repository.
The consequence of this is that manually managing git branches is discouraged, and PB should
 always be used for this, unless this detail is taken into consideration.

