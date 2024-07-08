from process import LaunchProcess

def CreateDirectory(Path):
    LaunchProcess('mkdir -p "'+Path+'"')

def CreateParentDirectory(PathToChild):
    PathToParent = '/'.join(PathToChild.split("/")[:-1])
    CreateDirectory(PathToParent)
