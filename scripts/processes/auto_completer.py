import readline
import glob
import sys
import os

class ActiveCompleter():
    def __init__(self):
        self.active_completer = None
        # Only 1 instance of this object exists, we can setup one-off readline stuff here
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind("tab: complete")

    def set(self, active_completer):
        self.active_completer = active_completer

    def get(self):
        return self.active_completer

active_completer = ActiveCompleter()

class CustomCompleter(object):  # Custom completer

    def __init__(self, histfile, options):
        self.options  = sorted(options)
        self.histfile = histfile
        try:
            readline.read_history_file(histfile)
            self.old_len = readline.get_current_history_length()
        except FileNotFoundError:
            open(histfile, 'wb').close()
            self.old_len = 0

    def update(self, input):
        readline.append_history_file(input, self.histfile)
        self.old_len = readline.get_current_history_length()

    def complete(self, text, state):
        # Only complete based on the last word of the current input, not the full line.
        # This prevents "3 3 " + TAB from trying to complete "3.3" style paths.
        line_buffer = readline.get_line_buffer()
        last_word = line_buffer.split(' ')[-1]

        # Add paths as options
        current_opts = self.options + list(glob.glob(os.path.expanduser(last_word)+'*')+[None])

        if state == 0:  # on first trigger, build possible matches
            if not last_word:
                self.matches = self.options[:]
            else:
                self.matches = [s for s in current_opts if s and s.startswith(last_word)]
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
    
    def setup(self):
        # Only change if self isn't currently active
        if active_completer.get() == self:
            return

        readline.set_completer(self.complete)
        readline.set_completion_display_matches_hook(self.display_matches)
        active_completer.set(self)
