"""Keyboard-to-pitch mapping.

The layout follows the common DAW convention: the home row is the white
keys and the row above it is the black keys, starting from middle C.

    w e   t y u   o p
   a s d f g h j k l ; '
"""

from __future__ import annotations

import math

NOTE_KEY_MAP: dict[str, float] = {
    "a": 261.63,  # C4
    "w": 277.18,  # C#4
    "s": 293.66,  # D4
    "e": 311.13,  # D#4
    "d": 329.63,  # E4
    "f": 349.23,  # F4
    "t": 369.99,  # F#4
    "g": 392.00,  # G4
    "y": 415.30,  # G#4
    "h": 440.00,  # A4
    "u": 466.16,  # A#4
    "j": 493.88,  # B4
    "k": 523.25,  # C5
    "o": 554.37,  # C#5
    "l": 587.33,  # D5
    "p": 622.25,  # D#5
    ";": 659.26,  # E5
    "'": 698.46,  # F5
}

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def frequency_for(key: str, octave_shift: int = 0) -> float | None:
    base = NOTE_KEY_MAP.get(key.lower())
    if base is None:
        return None
    return base * 2.0**octave_shift


def note_name(frequency: float) -> str:
    midi = round(69 + 12 * math.log2(frequency / 440.0))
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"
