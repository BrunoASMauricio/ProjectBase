

## Why use worktrees

Using worktrees has two main benefits:

### It improves full offline workflow

As long as the repository was already pulled by another project, it can be used in a different project, even if that projectwasn't loaded while the system was online.

### Repeated repositories

Old repositories tend to have a very dense `.git` which can be very big, and may cause problems in terms of available storage if multiple copies are required


## There is a weird branch name with the local time and a `_ProjectBase_` in the middle

In order to allow the same remote branch to be checkedout in different worktrees, the local names can't be the same.
Therefore branches are configured with the appropriate remote name, but a unique "local" name (different per worktree)

If you are seing these branches while inspecting the local repository, then everything is fine and you can ignore the nomenclature.

If you are seing them in the remote repository, it means the git configurations set by ProjectBase were changed externally.

Some changes that lead to this:

* If the git config `push.default` was set to `current` or `tracking` instead of the `upstream` set by PB, pushes will no longer setup the appropriate remote


