from data.print import *

def PBTerminal():
    # Shared namespace for variables to persist between executions
    namespace = {}
    
    print("Interactive Debug REPL\nType 'exit' or 'quit' to end the session." + "-" * 40)
    
    while True:
        try:
            # Read user input
            user_input = input(">>> ")
            
            # Check for exit commands
            if user_input.strip().lower() in ('exit', 'quit'):
                print("Goodbye!")
                break
            
            # Handle empty input
            if not user_input.strip():
                continue
            
            # Handle multi-line input (e.g., for functions, loops)
            if user_input.rstrip().endswith(':'):
                lines = [user_input]
                while True:
                    continuation = input("... ")
                    if continuation == "":
                        break
                    lines.append(continuation)
                user_input = "\n".join(lines)
            # Shove some imports into console
            imports = [ "from data.settings     import *",
                        "from data.colors       import *",
                        "from data.common       import *",
                        "from data.git          import *",
                        "from processes.project import *",
                        "from processes.process import *",
                        "from processes.git_operations import *",
                        "from processes.git     import *",
                        "from processes.repository import *"]
            for _import in imports:
                eval(_import, namespace)

            # Try to evaluate as an expression first (to print results)
            try:
                result = eval(user_input, namespace)
                if result is not None:
                    print(result)
            except SyntaxError:
                # If it's not an expression, execute as a statement
                exec(user_input, namespace)
                
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt")
            continue
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            PrintError(f"{type(e).__name__}: {e}")
