"""Removes secrets (bot tokens, API keys) from anything written to logs or shown on the dashboard."""

import re

_PATTERNS = [
    (re.compile(r"bot\d{6,}:[A-Za-z0-9_-]{20,}"), "bot<redacted>"),          # Telegram bot token in URLs
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), "<redacted-token>"),     # bare Telegram token
    (re.compile(r"AIza[0-9A-Za-z_-]{30,}"), "<redacted-key>"),                # Google API keys
    (re.compile(r"((?:key|token|password|access_token)=)[^&\s'\"]+", re.I), r"\1<redacted>"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._-]{16,}"), r"\1<redacted>"),
]


def redact(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingStream:
    """Wraps a text stream (the engine log) so every write is scrubbed."""

    def __init__(self, stream):
        self._stream = stream
        self.encoding = getattr(stream, "encoding", "utf-8")

    def write(self, text):
        return self._stream.write(redact(text))

    def flush(self):
        return self._stream.flush()

    def isatty(self):
        return False

    def fileno(self):
        return self._stream.fileno()

    def __getattr__(self, name):
        return getattr(self._stream, name)
