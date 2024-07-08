import re
import sys
from data.colors import ColorFormat, Colors

def RemoveNonAlfanumeric(String):
    return re.sub(r'[^A-Za-z0-9]+', '', String)


"""
Abort running program
"""
def Abort(Message):
    print(ColorFormat(Colors.Red, Message))
    sys.stdout.flush()
    sys.exit(-1)

"""
Abort if a condition is false
"""
def Assert(Condition, Message=None):
    if not Condition:
        if Message == None:
            Abort("Failed condition")
        else:
            Abort(Message)

"""
Remove 'None' elements from a list
"""
def RemoveNone(List):
    return [ListEl for ListEl in List if ListEl != None]

"""
True if Value is None or 0
"""
def IsEmptyOrNone(Value):
    return (Value == None or len(Value) == 0)

def StringIsNumber(Str):
    number_regex = '^[0-9]+$'
    if(re.search(number_regex, Str)):
        return True
    return False


def UserYesNoChoice(Message):
    try:
        print(Message)
        Answer = input("("+ColorFormat(Colors.Green,"Yy")+"/"+ColorFormat(Colors.Red,"Nn")+"): ")
        if Answer in ["y", "Y"]:
            Answer = True
        else:
            Answer = False

    except Exception as Ex:
        Answer = False

    return Answer
