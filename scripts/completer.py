import readline
import glob
import sys
import os

class CustomCompleter(object):  # Custom completer

    def __init__(self, options):
        self.options = sorted(options)

    def complete(self, text, state):
        # Add paths as options
        current_opts = self.options + list(glob.glob(os.path.expanduser(text)+'*')+[None])

        if state == 0:  # on first trigger, build possible matches
            if not text:
                self.matches = self.options[:] + current_opts
            else:
                self.matches = [s for s in current_opts if s and s.startswith(text)]
        try:
            return self.matches[state]
        except IndexError:
            return None

    def display_matches(self, substitution, matches, longest_match_length):
        line_buffer = readline.get_line_buffer()
        columns = os.environ.get("COLUMNS", 80)
        print("\n[>] Available completions:")
        tpl = "{:<" + str(int(max(map(len, matches)) * 1.2)) + "}"
        buffer = ""
        for match in matches:
            match = tpl.format(match[len(substitution):])
            if len(buffer + match) > columns:
                print(buffer)
                buffer = ""
            buffer += match
        if buffer:
            print(buffer)
        print("[<]\n"+line_buffer, end="")
        sys.stdout.flush()

def setup_completer(histfile):
    try:
        readline.read_history_file(histfile)
        old_len = readline.get_current_history_length()
    except FileNotFoundError:
        open(histfile, 'wb').close()
        old_len = 0


    completer = CustomCompleter([])
    readline.set_completer_delims(' \t\n;')
    readline.set_completer(completer.complete)
    readline.set_completion_display_matches_hook(completer.display_matches)

    readline.parse_and_bind("tab: complete")
    return old_len