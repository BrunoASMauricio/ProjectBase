import readline
import glob
import sys
import os
from difflib import SequenceMatcher
from data.common import PrintInColumns

class ActiveCompleter():
    def __init__(self):
        self.active_completer = None
        # Only 1 instance of this object exists, we can setup one-off readline stuff here
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind("tab: complete")
        # Ctrl+L: clear current input, insert "clear", and submit
        readline.parse_and_bind(r'"\C-l": "\C-a\C-kclear\C-m"')

    def set(self, active_completer):
        self.active_completer = active_completer

    def get(self):
        return self.active_completer

active_completer = ActiveCompleter()

MIN_MATCH_SCORE = 0.6

def _match_score(option, query):
    """
    Score how well the query matches the option.
    Prioritizes contiguous substring matches over scattered subsequences.
    Returns 0.0 - 1.5, where below MIN_MATCH_SCORE is filtered out.
    """
    if not query:
        return MIN_MATCH_SCORE

    query_lower = query.lower()
    option_lower = option.lower()

    # Best case: prefix match
    if option_lower.startswith(query_lower):
        return 1.0 + (len(query_lower) / len(option_lower)) * 0.5

    # Contiguous substring match
    if query_lower in option_lower:
        return 0.8 + (len(query_lower) / len(option_lower)) * 0.2

    # Longest common substring (contiguous, not subsequence)
    matcher = SequenceMatcher(None, query_lower, option_lower)
    longest_block = max((size for _, _, size in matcher.get_matching_blocks()), default=0)
    contiguity = longest_block / len(query_lower)

    return contiguity * 0.7

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

    def set_options(self, options):
        self.options = sorted(options)

    def update(self, input):
        readline.append_history_file(input, self.histfile)
        self.old_len = readline.get_current_history_length()

    def _ranked_matches(self, query):
        """
        Return options that match the query, sorted by relevance (best first).
        Includes file glob matches as lowest priority.
        """
        scored = []
        for opt in self.options:
            score = _match_score(opt, query)
            if score >= MIN_MATCH_SCORE:
                scored.append((score, opt))

        # Add file path matches
        if query:
            for path in glob.glob(os.path.expanduser(query) + '*'):
                scored.append((MIN_MATCH_SCORE, path))

        # Sort by score descending, then alphabetically
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [opt for _, opt in scored]

    def complete(self, text, state):
        # Only complete based on the last word of the current input, not the full line.
        # This prevents "3 3 " + TAB from trying to complete "3.3" style paths.
        line_buffer = readline.get_line_buffer()
        last_word = line_buffer.split(' ')[-1]

        if state == 0:
            self.matches = self._ranked_matches(last_word)
        try:
            return self.matches[state]
        except IndexError:
            return None

    def display_matches(self, substitution, matches, longest_match_length):
        line_buffer = readline.get_line_buffer()

        # Use our ranked matches (readline sorts alphabetically, losing our order)
        display = self.matches if self.matches else matches

        if not display:
            return

        print("\n[>] Completions:")
        PrintInColumns(display)
        print("[<] " + line_buffer, end="")
        sys.stdout.flush()

    def setup(self):
        # Only change if self isn't currently active
        if active_completer.get() == self:
            return

        readline.set_completer(self.complete)
        readline.set_completion_display_matches_hook(self.display_matches)
        active_completer.set(self)
