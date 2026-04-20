"""
Build system abstraction for ProjectBase.

A BuildSystem knows how to:
  1. Generate a per-repo build spec file from the JSON "build" section in configs.json
  2. Generate the project-level build entry point (including project-wide flags)
  3. Provide the shell command that drives the build

CMake, Make, and Cons (GNU Cons) are implemented.  To add a new back-end,
subclass BuildSystem and override the abstract methods.

JSON schema for the "build" key in configs.json (per-repository):
{
  "build": {
    "sources":        ["code/source/file.c", ...],
    "executables":    [{"name": "exec_name", "source": "executables/main.c",
                        "cflags": ["-DEXE_ONLY", ...]}, ...],
    "tests":          [{"name": "test_name", "source": "executables/tests/test.c",
                        "cflags": ["-DTEST_ONLY", ...]}, ...],
    "data":           [
      {"type": "test_data|test_exec|executable_data|executable_exec",
       "path": "relative/path/from/repo/root"}
    ],
    "cflags":          ["-DFOO", ...],      <- all targets in this repo
    "debug_cflags":    ["-g3", ...],
    "release_cflags":  ["-O2", ...],
    "lib_cflags":      ["-fPIC", ...],      <- shared library only
    "exe_cflags":      ["-DEXE", ...],      <- executables only
    "test_cflags":     ["-DTEST", ...]      <- tests only
  }
}

JSON schema for the "project" key in configs.json (root repository only):
{
  "project": {
    "cflags":         ["-DGLOBAL", ...],    <- applied to every target in the project
    "debug_cflags":   ["-g3", ...],         <- Debug builds only
    "release_cflags": ["-O2", ...]          <- Release builds only
  }
}

Repositories that still ship their own configs/CMakeLists.txt continue to
work exactly as before (backward compatibility).  The "build" JSON section is
only used when no hand-written CMakeLists.txt is present.
"""

from abc import ABC, abstractmethod

# ---------------------------------------------------------------------------
# BuildSpec — typed wrapper around the "build" JSON section
# ---------------------------------------------------------------------------

class BuildSpec:
    """Compilation descriptor parsed from a repo's configs.json "build" key."""

    def __init__(self, raw: dict):
        self.sources        = raw.get("sources",        [])
        self.executables    = raw.get("executables",    [])   # [{"name": str, "source": str}]
        self.tests          = raw.get("tests",          [])   # [{"name": str, "source": str}]
        self.data           = raw.get("data",           [])   # [{"type": str, "path": str}]
        # Flags applied to ALL targets (library + executables + tests)
        self.cflags         = raw.get("cflags",         [])
        self.debug_cflags   = raw.get("debug_cflags",   [])
        self.release_cflags = raw.get("release_cflags", [])
        # Target-specific additional flags
        self.lib_cflags     = raw.get("lib_cflags",     [])
        self.exe_cflags     = raw.get("exe_cflags",     [])
        self.test_cflags    = raw.get("test_cflags",    [])

    def is_empty(self) -> bool:
        return not any([
            self.sources, self.executables, self.tests, self.data,
            self.cflags, self.debug_cflags, self.release_cflags,
            self.lib_cflags, self.exe_cflags, self.test_cflags,
        ])

    @staticmethod
    def from_repo(repository) -> "BuildSpec | None":
        """Return a BuildSpec from a repo dict, or None if no 'build' key."""
        raw = repository.get("build")
        if raw is None:
            return None
        return BuildSpec(raw)


# ---------------------------------------------------------------------------
# ProjectBuildSpec — project-wide flags from the root repo's "project" key
# ---------------------------------------------------------------------------

class ProjectBuildSpec:
    """
    Project-wide compiler flags read from the root repository's
    configs.json "project" section.  Only honoured when the owning
    repository is the root of the loaded project.
    """

    def __init__(self, raw: dict):
        self.cflags         = raw.get("cflags",         [])
        self.debug_cflags   = raw.get("debug_cflags",   [])
        self.release_cflags = raw.get("release_cflags", [])

    def is_empty(self) -> bool:
        return not any([self.cflags, self.debug_cflags, self.release_cflags])

    @staticmethod
    def from_repo(repository) -> "ProjectBuildSpec | None":
        """Return a ProjectBuildSpec from a repo dict, or None if no 'project' key."""
        raw = repository.get("project")
        if raw is None:
            return None
        return ProjectBuildSpec(raw)



# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class BuildSystem(ABC):
    NAME = ""

    @abstractmethod
    def generate_repo_spec(self, repository) -> str:
        """
        Return the content of the per-repo build spec file generated from
        the configs.json "build" section.  Returns "" for repos with no spec.
        The file is written to the repo's build path by __SetupBuild.
        """

    @abstractmethod
    def generate_project_flags(self, project_spec: "ProjectBuildSpec | None") -> str:
        """
        Return build-system-specific content that applies project-wide compiler
        flags (from the root repository's "project" section).  Returns "" when
        project_spec is None or empty.
        """

    @abstractmethod
    def setup_project(self, repos_include_entries: list, project_vars: dict,
                      project_spec: "ProjectBuildSpec | None" = None):
        """Generate (or refresh) the project-level build file."""

    @abstractmethod
    def get_build_command(self) -> str:
        """Return the complete shell command that drives the build."""

    # @abstractmethod
    # def get_test_groups(self, repository) -> dict:
    #     """
    #     Return a mapping of {binary_name: group} for tests that declare a group.
    #     binary_name follows the build system's naming convention.
    #     Returns {} when no tests declare a group.
    #     """

    @abstractmethod
    def get_repo_build_filename(self) -> str:
        """Return the filename for the per-repo build file (e.g. 'CMakeLists.txt')."""

    @abstractmethod
    def get_repo_template(self) -> str:
        """Return the template path for the per-repo build file (relative to templates/)."""

    @abstractmethod
    def get_spec_filename(self) -> "str | None":
        """
        Return the filename for the auto-generated per-repo build spec, or None
        if the spec is embedded directly in the repo build file.
        """

    @abstractmethod
    def make_repo_include_entry(self, repo_source: str, build_path: str,
                                is_independent: bool) -> str:
        """Return the project-level include/invocation entry for one repository."""


