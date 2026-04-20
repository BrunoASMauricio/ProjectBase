from processes.build.cmake_build import CMakeBuildSystem
from processes.build.abstract_build_system import BuildSystem

# Apply build system selection before any build-related code runs
from processes.build.cmake_build import CMakeBuildSystem
from processes.build.make_build import MakeBuildSystem

# Default to Cmake
_active: BuildSystem = CMakeBuildSystem()

from data.error import Abort
# ConsBuildSystem as _ConsBuildSystem
_BUILD_SYSTEM_MAP = {
    "cmake": CMakeBuildSystem,
    "make":  MakeBuildSystem,
    # "cons":  _ConsBuildSystem,
}

def GetActiveBuildSystem() -> BuildSystem:
    return _active

def SetActiveBuildSystem(build_system: BuildSystem):
    global _active
    _active = build_system

def SetActiveBuildSystemSetting(build_system: str):
    if build_system not in _BUILD_SYSTEM_MAP:
        Abort(f"Invalid build system {build_system}")
    SetActiveBuildSystem(_BUILD_SYSTEM_MAP[build_system]())
