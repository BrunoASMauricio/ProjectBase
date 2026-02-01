import os
from data.print import *
from processes.filesystem import CreateParentDirectory, CreateDirectory, JoinPaths, RemoveDirectory
from data.paths import GetBasePaths
from processes.process import *
from data.paths import GetNewTemporaryPath
from data.common import GetTimeForPath

from processes.http import StartHTTPServer, GetHTTPRoot

def GetFlameGraphLocation():
    fg_path = JoinPaths(GetBasePaths()["scripts"], "FlameGraph")
    if not os.path.isdir(fg_path):
        return None

    # Check for the presence of one of the expected scripts
    if not os.path.isfile(JoinPaths(fg_path, "stackcollapse-bpftrace.pl")):
        return None

    return fg_path

def SetupFlamegraph():
    path = GetFlameGraphLocation()
    if path == None:
        try:
            CreateParentDirectory(path)
            PrintNotice("Cloning flame graph")
            LaunchProcess(f"git clone https://github.com/brendangregg/FlameGraph.git {path}", interactive=False)
            PrintNotice("Flame graph setup")
        except Exception as Ex:
            PrintError("Failed to setup flamegraph")
            raise Ex

    return GetFlameGraphLocation()


def RunFlamegraph(executable, args):
    fg_path = SetupFlamegraph()
    if fg_path == None:
        raise Exception("Can not run with flamegraph, could not setup")

    # Start default server in case it isnt already started
    StartHTTPServer()

    base_path = GetNewTemporaryPath()
    CreateDirectory(base_path)
    out_folded_path = JoinPaths(base_path, "out.folded")
    LaunchProcess(f"perf record -F 99 --call-graph dwarf,1024  -g -- {executable} {args} &> /dev/null", base_path, True)
    LaunchProcess(f"perf script | {fg_path}/stackcollapse-perf.pl > {out_folded_path} 2> /dev/null", base_path)
    
    exec_name = f"{ executable.split("/")[-1] }.{ GetTimeForPath() }.svg"
    graph_path = JoinPaths(GetHTTPRoot(), exec_name)
    LaunchProcess(f"{fg_path}/flamegraph.pl {out_folded_path} > {graph_path} 2> /dev/null", base_path)
    RemoveDirectory(base_path)

    # Return None (no command to run) and a message to print after the exec list
    return None, f"Check the flamegraph results in your browser at http://127.0.0.1:8000/{exec_name} or locally at {graph_path}"
