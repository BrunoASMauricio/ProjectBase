import traceback
import json

def load_json_file(Path, ErrorValue=None, VariableSubstitutions={}):
    """
    Returns the json from the given file, or ErrorValue in cas of an error
    Parameters
    ----------
    file : string
        The target file path
    ErrorValue : Object
        The object returned in case there is an error loading the json file
        If Object is None, the exception is thrown
    """
    try:
        with open(Path, 'r') as File:
            JsonData = json.load(File)

        for VariableName in VariableSubstitutions:
            JsonData = JsonData.replace("$$" + VariableName + "$$", VariableSubstitutions[VariableName])

        if JsonData == None:
            raise Exception("Null json data")

        return JsonData

    except Exception as Ex:
        if ErrorValue == None:
            raise Exception("Could not load json from file " + Path + " " + traceback.format_exc())
    return ErrorValue

def dump_json_file(JsonData, Path):
    with open(Path, 'w') as file:
        json.dump(JsonData, file)