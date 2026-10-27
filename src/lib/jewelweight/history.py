"""Output history, oldest first like a chat (pure Python)."""

KIND_RESULT = "result"
KIND_INFO = "info"
KIND_WARNING = "warning"
KIND_ERROR = "error"

KINDS = (KIND_RESULT, KIND_INFO, KIND_WARNING, KIND_ERROR)

MAX_ENTRIES = 50


class History(object):
    def __init__(self, limit=MAX_ENTRIES):
        self.limit = limit
        self._entries = []  # dicts {"kind", "text"}, oldest first

    @classmethod
    def from_list(cls, items, limit=MAX_ENTRIES):
        """Restore from stored data, skipping malformed entries."""
        result = cls(limit)
        result._append([
            (item.get("kind"), item.get("text"))
            for item in items
            if isinstance(item, dict) and item.get("kind") in KINDS
            and isinstance(item.get("text"), str)
        ])
        return result

    @property
    def entries(self):
        return [dict(entry) for entry in self._entries]

    def to_list(self):
        return self.entries

    def add_block(self, block):
        """Append (kind, text) pairs; the newest block ends up at the bottom."""
        self._append(block)

    def _append(self, block):
        self._entries.extend({"kind": kind, "text": text} for kind, text in block if text)
        if self.limit and len(self._entries) > self.limit:
            del self._entries[:len(self._entries) - self.limit]

    def clear(self):
        self._entries = []

    def last_result(self):
        """Text of the newest weight result, or None."""
        for entry in reversed(self._entries):
            if entry["kind"] == KIND_RESULT:
                return entry["text"]
        return None
