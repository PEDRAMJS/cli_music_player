from __future__ import annotations

from dataclasses import dataclass

OCTAVE_RANGE = (-2, 2)
DURATION_RANGE = (0.25, 4.0)
DURATION_STEP = 0.25
VOLUME_STEP = 10


@dataclass
class Settings:
    instrument: str = "piano"
    octave_shift: int = 0
    duration: float = 1.5  # seconds
    volume: int = 70  # percent

    def shift_octave(self, step: int) -> None:
        self.octave_shift = _clamp(self.octave_shift + step, *OCTAVE_RANGE)

    def change_duration(self, step: int) -> None:
        self.duration = _clamp(self.duration + step * DURATION_STEP, *DURATION_RANGE)

    def change_volume(self, step: int) -> None:
        self.volume = _clamp(self.volume + step * VOLUME_STEP, 0, 100)


def _clamp(value, low, high):
    return max(low, min(high, value))
