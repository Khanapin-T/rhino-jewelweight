"""Output history shown in the window, newest entries first (pure Python)."""

KIND_RESULT = "result"
KIND_INFO = "info"
KIND_WARNING = "warning"
KIND_ERROR = "error"

MAX_ENTRIES = 50


class History(object):
    def __init__(self, limit=MAX_ENTRIES):
        self.limit = limit
        self._entries = []  # dicts {"kind", "text"}, newest first

    @property
    def entries(self):
        return list(self._entries)

    def add_block(self, block):
        """Put a block of (kind, text) pairs on top, keeping its reading order."""
        new = [{"kind": kind, "text": text} for kind, text in block if text]
        self._entries[0:0] = new
        if self.limit:
            del self._entries[self.limit:]

    def clear(self):
        self._entries = []

    def last_result(self):
        """Text of the newest weight result, or None."""
        for entry in self._entries:
            if entry["kind"] == KIND_RESULT:
                return entry["text"]
        return None

    def render(self):
        return "\n".join(entry["text"] for entry in self._entries)
