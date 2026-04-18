import sys
import inspect
from data.print import *

# Exception for stopping current operation without printing stack/operation information
# Used when we know the error has been output (i.e. inside a thread) and we don't store it
class SlimError(Exception):
    def __init__(self, Message):
        # Call the base class constructor with the parameters it needs
        super().__init__(f"Message:{Message}")

def get_full_traceback(exc):
    tb = exc.__traceback__
    msg = "Traceback (most recent call last):"
    while tb:
        frame = tb.tb_frame
        lineno = tb.tb_lineno
        code = frame.f_code
        func_name = code.co_name
        filename = code.co_filename

        # Basic location
        msg += f'  File "{filename}", line {lineno}, in {func_name}\n'

        # Get argument values
        arg_info = inspect.getargvalues(frame)
        args = arg_info.args
        locals_ = arg_info.locals

        # Print args with their values
        # if args:
        #     arg_strs = []
        #     for arg in args:
        #         # repr to avoid huge dumps
        #         val = locals_.get(arg, '<no value>')
        #         arg_strs.append(f"{arg}={val!r}")
        #     msg += f"    Arguments: {', '.join(arg_strs)}"

        tb = tb.tb_next

    # Finally show exception type and message
    msg += f"{type(exc).__name__}: {exc!r}"
    return msg

"""
Abort running program
"""
def Abort(message, err_ret=-1):
    message = ColorFormat(Colors.Red, message)

    print(message)
    logging.error(message)

    FlushthreadLog()
    sys.stdout.flush()
    sys.exit(err_ret)

"""
Abort if a condition is false
"""
def Assert(condition, message=None):
    if not condition:
        if message == None:
            Abort("Failed condition")
        else:
            Abort(message)

