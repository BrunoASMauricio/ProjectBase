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
        self.menu = None
        try:
            readline.read_history_file(histfile)
            self.old_len = readline.get_current_history_length()
        except FileNotFoundError:
            open(histfile, 'wb').close()
            self.old_len = 0

    def set_menu(self, menu):
        self.menu = menu

    def set_options(self, options):
        self.options = sorted(options)

    def update(self, input):
        readline.append_history_file(input, self.histfile)
        self.old_len = readline.get_current_history_length()

    def _resolve_options(self, preceding_words):
        """
        Walk through submenus using preceding input words to find the
        target menu's completion options. Falls back to self.options
        if no menu is set or the path doesn't lead to submenus.
        If a callback has a completions function, use that.
        """
        if self.menu is None:
            return self.options

        # Import here to avoid circular imports
        from menus.menu import EntryType

        current_menu = self.menu
        for word in preceding_words:
            if not word.isdigit():
                break
            entry_type, entry_obj, completions_fn = current_menu.GetEntryAtIndex(int(word))
            if entry_type == EntryType.MENU:
                current_menu = entry_obj
            elif entry_type == EntryType.CALLBACK and completions_fn is not None:
                # Callback provides its own completions
                return completions_fn()
            else:
                break

        if current_menu is not self.menu:
            return current_menu.GetCompletionOptions()
        return self.options

    def _ranked_matches(self, query, options):
        """
        Return options that match the query, sorted by relevance (best first).
        Includes file glob matches as lowest priority.
        """
        scored = []
        for opt in options:
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
        line_buffer = readline.get_line_buffer()
        words = line_buffer.split()
        last_word = words[-1] if words else ""

        # If the line ends with a space, we're starting a new word
        if line_buffer.endswith(' '):
            preceding = words
            last_word = ""
        else:
            preceding = words[:-1]

        if state == 0:
            options = self._resolve_options(preceding)
            # All ranked matches for display
            self.matches = self._ranked_matches(last_word, options)
            # Single-word prefix matches for readline substitution
            self.substitution_matches = [
                m for m in self.matches
                if ' ' not in m and m.lower().startswith(last_word.lower())
            ] if last_word else [m for m in self.matches if ' ' not in m]

            # If exactly one match, let readline auto-complete it.
            # If multiple, return two fake matches whose common prefix equals
            # the typed text, so readline triggers the display hook without
            # modifying the buffer.
            if len(self.substitution_matches) != 1 and self.matches:
                dummy = last_word if last_word else ""
                self.substitution_matches = [dummy + "\x01", dummy + "\x02"]

        try:
            return self.substitution_matches[state]
        except IndexError:
            return None

    def display_matches(self, substitution, matches, longest_match_length):
        # line_buffer = readline.get_line_buffer()

        # Use our ranked matches (readline sorts alphabetically, losing our order)
        display = self.matches if self.matches else matches

        if not display:
            return

        sys.stdout.write("\n[>] Completions:\n")
        PrintInColumns(display)
        sys.stdout.write("[<] " + readline.get_line_buffer())
        sys.stdout.flush()

    def setup(self):
        # Only change if self isn't currently active
        if active_completer.get() == self:
            return

        readline.set_completer(self.complete)
        readline.set_completion_display_matches_hook(self.display_matches)
        active_completer.set(self)
