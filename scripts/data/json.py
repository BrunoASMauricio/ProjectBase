from data.common import PrintWarning
import traceback
import json
import os

def load_json_file(path, error_value=None, variable_substitutions={}):
    """
    Returns the json from the given file, or error_value in cas of an error
    Parameters
    ----------
    file : string
        The target file path
    error_value : Object
        The object returned in case there is an error loading the json file
        If Object is None, the exception is thrown
    """

    if not os.path.isfile(path):
        return error_value

    try:
        with open(path, 'r') as File:
            json_data = json.load(File)

        for variable_name in variable_substitutions:
            json_data = json_data.replace("$$" + variable_name + "$$", variable_substitutions[variable_name])

        if json_data == None:
            raise Exception("Null json data")

        return json_data

    except Exception as Ex:
        if error_value == None:
            raise Exception(f"Could not load json from file {path} {traceback.format_exc()}")
        PrintWarning(f"Failed to parse json in {path}, using default: {str(Ex)}")

    return error_value

def dump_json_file(json_data, path):
    with open(path, 'w') as file:
        json.dump(json_data, file, indent=4)
