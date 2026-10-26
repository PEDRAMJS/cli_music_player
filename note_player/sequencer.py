"""Note files: parse them into steps, play them back in time, record new ones.

One step per line: one or more notes (a chord) followed by how long to hold
them, in seconds. ``x`` is a rest. ``#`` starts a comment.

    a4 1.2
    x 0.5          # silence
    c4 e4 g4 1.0   # chord
    f#4 0.5
    bb3 0.5
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REST = "x"
_NOTE = re.compile(r"^([a-g])([#b]?)(-?\d)$")
_SEMITONES = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
_NAMES = ("c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b")


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


# Notes pressed closer together than this are recorded as one chord.
CHORD_WINDOW = 0.05


class Recorder:
    """Collects timed key presses and turns them into steps.

    A step lasts until the next press, capped at ``hold`` (how long a note
    sounds); any longer gap becomes a rest. Silence before the first note
    is dropped.
    """

    def __init__(self, hold: float) -> None:
        self.hold = hold
        self._onsets: list[tuple[float, list[float]]] = []

    def __len__(self) -> int:
        return len(self._onsets)

    def press(self, frequency: float, at: float) -> None:
        if self._onsets and at - self._onsets[-1][0] < CHORD_WINDOW:
            self._onsets[-1][1].append(frequency)
        else:
            self._onsets.append((at, [frequency]))

    def steps(self) -> list[Step]:
        steps = []
        for index, (onset, frequencies) in enumerate(self._onsets):
            if index + 1 < len(self._onsets):
                gap = self._onsets[index + 1][0] - onset
            else:
                gap = self.hold
            sounding = round(min(gap, self.hold), 2)
            steps.append(Step(tuple(frequencies), sounding, len(steps) + 1))
            if (rest := round(gap - sounding, 2)) > 0:
                steps.append(Step((), rest, len(steps) + 1))
        return steps


def format_steps(steps: list[Step]) -> str:
    lines = []
    for step in steps:
        notes = " ".join(note_token(f) for f in step.frequencies) or REST
        lines.append(f"{notes} {step.duration:g}")
    return "\n".join(lines) + "\n"


def note_token(frequency: float) -> str:
    """440.0 -> ``a4``; the inverse of :func:`note_frequency`."""
    midi = round(69 + 12 * math.log2(frequency / 440.0))
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


def save(path: str | Path, steps: list[Step]) -> None:
    Path(path).write_text(format_steps(steps))
