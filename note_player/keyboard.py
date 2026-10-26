"""Unbuffered key reading from the terminal (POSIX, no root or X needed)."""

from __future__ import annotations

import os
import select
import sys
import termios
import tty

# How long to wait after a lone ESC byte before deciding it was the Esc key
# rather than the start of an escape sequence such as an arrow key.
ESC_TIMEOUT = 0.03

_SEQUENCES = {
    "[A": "up",
    "[B": "down",
    "[C": "right",
    "[D": "left",
    "OA": "up",
    "OB": "down",
    "OC": "right",
    "OD": "left",
}
_SPECIAL = {"\r": "enter", "\n": "enter", "\x7f": "backspace", "\t": "tab"}


class RawKeyboard:
    """Context manager that puts the terminal in cbreak mode and yields key names.

    Printable keys come back as themselves; others as names such as
    ``"esc"``, ``"enter"``, ``"up"``.
    """

    def __init__(self, stream=None) -> None:
        self._fd = (stream or sys.stdin).fileno()
        self._saved = None

    def __enter__(self) -> RawKeyboard:
        self._saved = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        sys.stdout.write("\x1b[?25l")  # hide cursor
        sys.stdout.flush()
        return self

    def __exit__(self, *exc) -> None:
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()

    def _byte(self, timeout: float | None) -> str | None:
        ready, _, _ = select.select([self._fd], [], [], timeout)
        if not ready:
            return None
        return os.read(self._fd, 1).decode(errors="ignore")

    def read_key(self, timeout: float | None = None) -> str | None:
        """Block until a key arrives (or ``timeout`` seconds pass -> None)."""
        char = self._byte(timeout)
        if char != "\x1b":
            return _SPECIAL.get(char, char) if char else None
        sequence = ""
        while (nxt := self._byte(ESC_TIMEOUT)) is not None:
            sequence += nxt
            if nxt.isalpha() or nxt == "~":
                break
        if not sequence:
            return "esc"
        return _SEQUENCES.get(sequence, "unknown")
