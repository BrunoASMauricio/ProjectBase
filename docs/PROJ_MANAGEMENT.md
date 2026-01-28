# Opinionated management

## 
Here is an opinionated way for managing a multi-person project with ProjectBase

For developing a new feature, a developer creates/moves to a new branch:

```shell
# Create a local branch with a unique pseudo random name, connected to a remote branch with the exact name
# If the 
./run.sh --url=git@gitlab.com:brunoasmauricio/ProjectBase.git 5 4 2 some/branch/name -e
```

Important note.
The actual local branch will be a unique branch, that follows the actual branch remotely.
This is done so multiple projects can use the same remote branch for the same repository.
The consequence of this is that manually managing git branches is discouraged, and PB should
 always be used for this, unless this detail is taken into consideration.

Repositories that have their branch changed:
1. Managed repositories
2. 
Only clean repositories change branch. If a repository that was 
If there is a failure to change branch, it will most likely be because of unstashed changes.
In this case
