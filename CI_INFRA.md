# Projectbase CI Infrastructure
This document describes the design and implementation of the Projectbase CI
(Continuous Integration) infrastructure

The goal of this infrastructure is to ensure that **all commits intended to be
pushed are validated in a clean and reproducible environment**, and that the
exact versions of all involved repositories are recorded.

---
## Objective
The CI infrastructure exists to guarantee that:

1. All commits intended to be pushed are validated.
2. No change breaks the build or tests of:
   - the modified repository itself
   - the full project integration
3. The **exact commit hash of every repository involved in a successful build**
   is known and recorded.
4. Builds are reproducible and debuggable.

In short: *every change must prove that it does not break anything*.
---

## Context: ProjectBase and Multi-Repository Projects

ProjectBase manages projects composed of **multiple Git repositories**, possibly
spread across different remotes.

It provides commands to:
- load repositories and their dependencies
- build them
- run their tests

These commands can operate on multiple repositories at once, treating the
project as a coherent whole.

However, Git commits and pushes are fundamentally **per-repository operations**.
When multiple repositories are modified together, it is possible to push changes
that are inconsistent or incomplete from the perspective of the full project.
This makes reliable testing difficult without additional coordination.

---

## Why a CI Infrastructure Is Necessary

Without CI support:

- A repository may be pushed before its dependencies are updated.
- Tests may rely on local, unpushed changes.
- It becomes unclear which dependency versions were used for a given build.
- Failures can only be reproduced on the original developer’s machine.

The CI infrastructure addresses these problems by:
- creating a controlled testing state
- enforcing consistent repository versions
- validating changes before they are considered stable

---

## Core CI Strategy

The CI pipeline is implemented **on top of ProjectBase**, not alongside it.

Instead of re-implementing dependency resolution or build logic, the CI process
**reuses ProjectBase itself as the execution engine**.

The strategy is based on the following principles:

### 1. Temporary CI Branches

For each repository that has unpushed or modified commits, a temporary branch is
created (e.g. `ci/tmp/<repo>/<id>`).

These branches:
- point to the exact commits being tested
- are pushed to the location from which ProjectBase fetches repositories
- are deleted after the CI run finishes (success or failure)

This allows ProjectBase to load repositories using standard Git operations,
without special-case handling for detached states.

---

### 2. CI-Aware Load Logic

ProjectBase load logic is extended with CI awareness:

- If no temporary branch is defined for a repository, it is loaded normally.
- If a temporary CI branch exists, that branch is used instead.
- Repositories with pinned commits continue to be checked out exactly.
- Dependency resolution remains unchanged.

workflows.

---

### 3. Incremental Validation

CI validation is performed in two stages:

#### a) Per-repository validation

For each modified repository:
1. Load the repository and all its dependencies (respecting CI branches).
2. Run:
   - `load`
   - `build`
   - `test`
3. Fail fast if any step fails.

This ensures that each repository is independently valid within the project
context. (At the minimum forces each repo to have its necessary dependencies correctly)

#### b) Full project validation

After all modified repositories pass:
1. Load the main/root project repository.
2. Run:
   - `load`
   - `build`
   - `test`

This validates the full integration state.

---
### 4. Build Manifest Generation

On successful CI completion, a **build manifest** is generated.

The manifest records, for every repository involved:
- repository identifier (URL or name)
- branch used (normal or temporary)
- exact commit hash checked out
- whether the repository was modified as part of CI

This information is obtained by querying Git **after checkout**, ensuring that
the manifest reflects the actual build state.

The manifest acts as:
- a reproducibility lockfile
- an audit record
- a debugging aid

---

### 5. Manifest Ownership

The build manifest is stored in the **root project being tested**, not in
individual dependency repositories.

This follows industry practice:
- the manifest describes an *integration state*
- dependencies remain unaware of how they are consumed
- one manifest corresponds to one validated project state

Optionally, manifests may later be mirrored to a separate repository for CI
history or analytics, but the authoritative version lives with the project.

---
## Execution Environment

CI runs are intended to execute:
- locally on the developer’s machine
- or in an isolated environment (e.g. Docker) (Still to think exacly where docker file must reside unclear)

---

Detect changes
    ↓
Create temp branches
    ↓
CI-aware load
    ↓
Test modified repos
    ↓
Test full project
    ↓
Generate manifest
    ↓
Cleanup temp branches

