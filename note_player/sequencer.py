"""Note files: parse them into steps and play them back in time.

One step per line: one or more notes (a chord) followed by how long to hold
them, in seconds. ``x`` is a rest. ``#`` starts a comment.

    a4 1.2
    x 0.5          # silence
    c4 e4 g4 1.0   # chord
    f#4 0.5
    bb3 0.5
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REST = "x"
_NOTE = re.compile(r"^([a-g])([#b]?)(-?\d)$")
_SEMITONES = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


class NoteFileError(ValueError):
    pass


@dataclass(frozen=True)
class Step:
    frequencies: tuple[float, ...]  # empty for a rest
    duration: float
    line: int


def note_frequency(token: str) -> float:
    """``a4`` -> 440.0. Accepts sharps (``c#4``) and flats (``bb3``)."""
    match = _NOTE.match(token.lower())
    if not match:
        raise ValueError(f"not a note: {token!r}")
    letter, accidental, octave = match.groups()
    semitone = _SEMITONES[letter] + {"#": 1, "b": -1, "": 0}[accidental]
    midi = (int(octave) + 1) * 12 + semitone
    return 440.0 * 2 ** ((midi - 69) / 12)


def parse(text: str) -> list[Step]:
    steps = []
    for number, raw in enumerate(text.splitlines(), 1):
        tokens = _strip_comment(raw)
        if not tokens:
            continue
        if len(tokens) < 2:
            raise NoteFileError(f"line {number}: expected '<note(s)> <seconds>', got {raw.strip()!r}")
        *notes, length = tokens
        try:
            duration = float(length)
        except ValueError:
            raise NoteFileError(f"line {number}: {length!r} is not a duration in seconds") from None
        if duration <= 0:
            raise NoteFileError(f"line {number}: duration must be positive")
        if notes == [REST]:
            steps.append(Step((), duration, number))
            continue
        try:
            frequencies = tuple(note_frequency(note) for note in notes)
        except ValueError as error:
            raise NoteFileError(f"line {number}: {error}") from None
        steps.append(Step(frequencies, duration, number))
    return steps


def _strip_comment(line: str) -> list[str]:
    # A comment is a token starting with '#'; the '#' inside "f#4" is a sharp.
    tokens = []
    for token in line.split():
        if token.startswith("#"):
            break
        tokens.append(token)
    return tokens


def load(path: str | Path) -> list[Step]:
    return parse(Path(path).read_text())


def play(
    steps: list[Step],
    play_note: Callable[[float, float], object],
    wait: Callable[[float], bool] = lambda seconds: time.sleep(seconds) is None,
    on_step: Callable[[int, Step], object] | None = None,
) -> bool:
    """Play ``steps`` in order. Returns False if ``wait`` asked to stop early.

    ``play_note(frequency, duration)`` starts a note without blocking.
    ``wait(seconds)`` sleeps and returns False to abort playback.
    Steps are scheduled against a fixed clock, so timing doesn't drift.
    """
    deadline = time.monotonic()
    for index, step in enumerate(steps):
        if on_step:
            on_step(index, step)
        for frequency in step.frequencies:
            play_note(frequency, step.duration)
        deadline += step.duration
        if not wait(max(0.0, deadline - time.monotonic())):
            return False
    return True
