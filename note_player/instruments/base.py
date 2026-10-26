"""Instrument plugin contract.

An instrument never produces audio itself. It takes a raw frequency and
describes *how* it should sound as a :class:`Voice`: a set of partials
(tweaked frequencies + gains + waveforms) and an envelope. Audio backends
turn that description into sound, so instruments stay backend-agnostic.

Adding an instrument = dropping a module in this package that subclasses
:class:`Instrument` and sets ``name``. It is registered automatically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

WAVEFORMS = frozenset({"sine", "square", "triangle", "sawtooth", "trapezium", "pluck"})

_REGISTRY: dict[str, type[Instrument]] = {}


@dataclass(frozen=True)
class Partial:
    """One component tone of a voice."""

    frequency: float
    gain: float = 1.0
    waveform: str = "sine"

    def __post_init__(self) -> None:
        if self.waveform not in WAVEFORMS:
            raise ValueError(f"unknown waveform {self.waveform!r}")
        if self.frequency <= 0:
            raise ValueError("frequency must be positive")


@dataclass(frozen=True)
class Voice:
    """Backend-agnostic description of a single sounding note."""

    partials: tuple[Partial, ...]
    duration: float
    attack: float = 0.005
    release: float = 0.2
    reverb: int = 0  # 0-100
    tail: float = 0.0  # extra silence appended so reverb can ring out

    def __post_init__(self) -> None:
        if not self.partials:
            raise ValueError("a voice needs at least one partial")
        if self.duration <= 0:
            raise ValueError("duration must be positive")


class Instrument(ABC):
    name: ClassVar[str]
    description: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "name", None)
        if name:
            _REGISTRY[name] = cls

    @abstractmethod
    def voice(self, frequency: float, duration: float) -> Voice:
        """Shape a raw frequency into this instrument's sound."""


def registry() -> dict[str, type[Instrument]]:
    return dict(_REGISTRY)
